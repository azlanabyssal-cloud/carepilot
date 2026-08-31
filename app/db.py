"""
Case persistence - the missing "a physician needs to pull this up later"
half of the intake pipeline.

Before this file existed, every /case-intake response was pure request/
response: a ClinicalHistorySummary was built, returned once over HTTP,
and then gone - nothing a physician could look back up minutes, hours,
or the next day later. SIH26047's own patient journey (Step 5:
"Physician reviews complete history... at consultation," see
docs/sih/SIH26047_Patient_Case_Taking_Software.md) assumes the summary
is still there by the time the patient reaches the consultation room,
which a stateless pipeline can never actually guarantee.

Plain stdlib sqlite3, not an ORM: this is one table with a fixed,
already-known shape (ClinicalHistorySummary's own fields), queried by
primary key or a simple ORDER BY - exactly the case an ORM's abstraction
buys nothing for, while a new dependency is a real cost this scope
doesn't need to pay. Same "right-sized tool, not the fanciest one"
reasoning app/agents/verify.py already gives for TF-IDF over a
transformer embedding model (docs/INTERVIEW_NOTES.md, Guideline-
Verification Q&A) - this would be revisited the moment real multi-table
relations (patients, visits, documents) or serious concurrent-write
throughput actually demanded it, neither of which is true yet.

Columns, not a JSON blob: the entire reason to reach for a real database
here instead of writing each ClinicalHistorySummary out as a JSON file
is so a physician-facing query tool can run
`SELECT chief_complaint, priority_level FROM cases` directly - a blob
column would give that property up while still calling itself
"a database."
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from app.schemas import ClinicalHistorySummary, TriageLevel

DEFAULT_DB_PATH = "data/cases.db"

# Every ClinicalHistorySummary field, plus three DB-only columns
# (case_id, created_at, source) that aren't part of that API schema at
# all - source in particular exists only so this table can answer "how
# did this case arrive" (text/voice/document), a question the pipeline
# itself never needs to answer back through the physician-facing schema.
# Kept as one ordered tuple, reused for CREATE/INSERT/SELECT below, so
# the table shape and the queries against it can't quietly drift apart.
_SUMMARY_COLUMNS = (
    "chief_complaint",
    "history_of_present_illness",
    "past_medical_surgical_history",
    "drug_allergy_history",
    "family_history",
    "personal_history",
    "review_of_systems",
    "prior_investigations_summary",
    "priority_level",
    "is_reviewed_by_physician",
)
_ALL_COLUMNS = ("case_id", "created_at", "source") + _SUMMARY_COLUMNS

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    chief_complaint TEXT NOT NULL,
    history_of_present_illness TEXT NOT NULL,
    past_medical_surgical_history TEXT,
    drug_allergy_history TEXT,
    family_history TEXT,
    personal_history TEXT,
    review_of_systems TEXT,
    prior_investigations_summary TEXT,
    priority_level TEXT NOT NULL,
    is_reviewed_by_physician INTEGER NOT NULL
)
"""


class CaseStore:
    """
    SQLite-backed store for persisted ClinicalHistorySummary records.

    Opens a fresh, short-lived sqlite3 connection per method call
    (see _connection() below) rather than holding one open for this
    object's whole lifetime - deliberately, not an oversight. FastAPI
    runs a sync route handler like /case-intake in a worker-thread pool
    (Starlette's run_in_threadpool), so a single CaseStore built once at
    import time (app/main.py's _CASE_STORE, same "build once, share for
    the process lifetime" pattern as _GUIDELINE_INDEX/_FACILITIES) can
    end up called from a different OS thread on every request. sqlite3
    connections refuse cross-thread reuse by default (check_same_thread
    =True) specifically because a single connection object isn't safe to
    share across threads without extra caller-managed locking - the same
    real gotcha Flask's own tutorial works around by opening one
    connection per request rather than one for the app's lifetime. This
    class does the same thing at the method-call level instead: no
    shared connection ever crosses a thread boundary, so there is no
    locking scheme to get right or to leave untested. The overhead of
    opening/closing a local SQLite file connection per call is
    negligible at this scope - the same "right-sized, not fanciest"
    tradeoff this module's own docstring already names for choosing
    sqlite3 over an ORM in the first place.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        # data/ already exists in this repo, but tests point this at an
        # arbitrary tmp_path file, and a fresh clone or deploy target
        # might not have created the parent directory yet - cheap to
        # guarantee here, expensive to debug later as a confusing
        # "unable to open database file" error the first time someone
        # runs this somewhere new.
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(_CREATE_TABLE_SQL)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """
        One connection, scoped to exactly one `with` block: commits (via
        sqlite3's own with-connection transaction semantics) on a clean
        exit, rolls back on an exception, and always closes the
        connection afterward either way. See the class docstring for why
        this opens fresh per call instead of holding one connection open
        for CaseStore's whole lifetime.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save(self, summary: ClinicalHistorySummary, source: str) -> str:
        """
        Always inserts a new row under a freshly generated case_id -
        never an upsert keyed on summary.case_id, even if the object
        passed in already has one set. Whatever case_id `summary` already
        carries (normally None - see app/schemas.py's own docstring) is
        ignored on purpose: this method's entire job is minting the
        real, persisted identity for this case, exactly once, and
        handing it back.
        """
        case_id = uuid.uuid4().hex
        # ISO 8601 with an explicit UTC offset - both genuinely human-
        # readable AND lexicographically sortable in that form, which is
        # exactly what list_recent()'s `ORDER BY created_at DESC` leans
        # on for correct chronological ordering without a second,
        # database-specific timestamp type.
        created_at = datetime.now(timezone.utc).isoformat()
        values = (
            case_id,
            created_at,
            source,
            summary.chief_complaint,
            summary.history_of_present_illness,
            summary.past_medical_surgical_history,
            summary.drug_allergy_history,
            summary.family_history,
            summary.personal_history,
            summary.review_of_systems,
            summary.prior_investigations_summary,
            summary.priority_level.value,
            int(summary.is_reviewed_by_physician),
        )
        placeholders = ", ".join("?" for _ in _ALL_COLUMNS)
        with self._connection() as conn:
            conn.execute(
                f"INSERT INTO cases ({', '.join(_ALL_COLUMNS)}) VALUES ({placeholders})",
                values,
            )
        return case_id

    def get(self, case_id: str) -> Optional[ClinicalHistorySummary]:
        """Returns None, not an error, for an unknown case_id - "no such
        case yet" is a normal, expected outcome for a physician-lookup
        tool, not a failure."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"SELECT {', '.join(_ALL_COLUMNS)} FROM cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return self._row_to_summary(row) if row is not None else None

    def list_recent(self, limit: int = 50) -> list[ClinicalHistorySummary]:
        """
        Most recent first by created_at - a physician (or, today, the
        GET /cases endpoint) wants the newest cases surfaced first, not
        buried after every case this store has ever recorded. limit=50
        is a real, named scope cap, not pagination - nothing here yet
        needs to browse deep case history, and this can grow a real
        offset/cursor parameter the day something does.
        """
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT {', '.join(_ALL_COLUMNS)} FROM cases ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    @staticmethod
    def _row_to_summary(row: sqlite3.Row) -> ClinicalHistorySummary:
        return ClinicalHistorySummary(
            case_id=row["case_id"],
            chief_complaint=row["chief_complaint"],
            history_of_present_illness=row["history_of_present_illness"],
            past_medical_surgical_history=row["past_medical_surgical_history"],
            drug_allergy_history=row["drug_allergy_history"],
            family_history=row["family_history"],
            personal_history=row["personal_history"],
            review_of_systems=row["review_of_systems"],
            prior_investigations_summary=row["prior_investigations_summary"],
            priority_level=TriageLevel(row["priority_level"]),
            is_reviewed_by_physician=bool(row["is_reviewed_by_physician"]),
        )
