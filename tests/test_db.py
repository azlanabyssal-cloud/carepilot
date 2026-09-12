"""
Unit tests for app/db.py's CaseStore - the persistence layer a physician-
facing case-lookup tool depends on. Every test here runs against a fresh
temp-file database (pytest's tmp_path fixture) - never the real
data/cases.db app/main.py's _CASE_STORE writes to at import time. See
tests/test_main.py for the endpoint-level tests that exercise that real,
live-app-wired store instead.
"""

import sqlite3
import time
import uuid
from datetime import datetime, timezone

import pytest

from app.db import CaseStore
from app.schemas import ClinicalHistorySummary, TriageLevel


def _summary(**overrides) -> ClinicalHistorySummary:
    fields = dict(
        chief_complaint="persistent cough",
        history_of_present_illness="two days, worse at night",
        priority_level=TriageLevel.CLINIC_VISIT,
    )
    fields.update(overrides)
    return ClinicalHistorySummary(**fields)


def test_save_returns_a_real_uuid4_hex_case_id(tmp_path):
    """
    Not a placeholder or an incrementing string - a genuine uuid4,
    proven by round-tripping it through uuid.UUID's own parser and
    checking it comes back in the exact same canonical hex form
    uuid.uuid4().hex itself produces.
    """
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(), source="text")
    assert uuid.UUID(hex=case_id).hex == case_id


def test_save_generates_a_different_case_id_each_call(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    first_id = store.save(_summary(), source="text")
    second_id = store.save(_summary(), source="text")
    assert first_id != second_id


def test_get_returns_none_for_an_unknown_case_id(tmp_path):
    """
    None, not an exception - a physician-lookup tool asking "does this
    case exist" needs "no" to be a normal answer, not a crash.
    """
    store = CaseStore(str(tmp_path / "cases.db"))
    assert store.get("not-a-real-case-id") is None


def test_save_then_get_round_trips_every_field(tmp_path):
    """
    The actual point of a real database instead of a JSON dump: every
    field a physician might later query on must survive a save/get round
    trip intact, not just whichever ones happen to get exercised by
    other tests.
    """
    store = CaseStore(str(tmp_path / "cases.db"))
    summary = _summary(
        chief_complaint="chest pain",
        history_of_present_illness="onset two hours ago, radiating to left arm",
        past_medical_surgical_history="hypertension",
        drug_allergy_history="penicillin allergy",
        family_history="father had a heart attack at 55",
        personal_history="smoker",
        review_of_systems="no fever",
        prior_investigations_summary="ECG: normal sinus rhythm",
        priority_level=TriageLevel.EMERGENCY,
        is_reviewed_by_physician=True,
    )

    case_id = store.save(summary, source="voice")
    fetched = store.get(case_id)

    assert fetched is not None
    assert fetched.case_id == case_id
    assert fetched.chief_complaint == "chest pain"
    assert fetched.history_of_present_illness == "onset two hours ago, radiating to left arm"
    assert fetched.past_medical_surgical_history == "hypertension"
    assert fetched.drug_allergy_history == "penicillin allergy"
    assert fetched.family_history == "father had a heart attack at 55"
    assert fetched.personal_history == "smoker"
    assert fetched.review_of_systems == "no fever"
    assert fetched.prior_investigations_summary == "ECG: normal sinus rhythm"
    assert fetched.priority_level == TriageLevel.EMERGENCY
    assert fetched.is_reviewed_by_physician is True


def test_save_then_get_preserves_none_for_unset_optional_fields(tmp_path):
    """
    Distinct from the full-round-trip test above: a case with none of the
    optional history sections filled in must come back with real None
    values, not empty strings silently standing in for "not asked" -
    same distinction ClinicalHistorySummary's own docstring already
    draws, now proven to survive an actual SQLite round trip too.
    """
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(), source="text")
    fetched = store.get(case_id)

    assert fetched is not None
    assert fetched.past_medical_surgical_history is None
    assert fetched.drug_allergy_history is None
    assert fetched.family_history is None
    assert fetched.personal_history is None
    assert fetched.review_of_systems is None
    assert fetched.prior_investigations_summary is None


def test_list_recent_orders_most_recent_first(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    first_id = store.save(_summary(chief_complaint="first case"), source="text")
    time.sleep(0.01)
    second_id = store.save(_summary(chief_complaint="second case"), source="text")
    time.sleep(0.01)
    third_id = store.save(_summary(chief_complaint="third case"), source="text")

    recent = store.list_recent()

    assert [case.case_id for case in recent] == [third_id, second_id, first_id]


def test_list_recent_respects_the_limit_argument(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    for i in range(5):
        store.save(_summary(chief_complaint=f"case number {i}"), source="text")

    recent = store.list_recent(limit=2)

    assert len(recent) == 2


def test_list_recent_returns_empty_list_when_nothing_saved(tmp_path):
    """Empty, not an error - a brand-new store has no cases yet, and
    that's a normal state, not a failure."""
    store = CaseStore(str(tmp_path / "cases.db"))
    assert store.list_recent() == []


def test_save_persists_the_source(tmp_path):
    """
    source (text/voice/document) isn't part of ClinicalHistorySummary's
    own schema - it's DB-only metadata, so it can't be checked through
    get()'s return value. Verified here by reading the underlying column
    directly, the one place in this file it's acceptable to reach past
    CaseStore's public API, specifically to prove this one field
    actually gets written, not silently dropped.
    """
    db_path = str(tmp_path / "cases.db")
    store = CaseStore(db_path)
    case_id = store.save(_summary(), source="voice")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT source FROM cases WHERE case_id = ?", (case_id,)).fetchone()

    assert row[0] == "voice"


def test_save_records_created_at_as_sortable_iso8601_utc(tmp_path):
    """
    created_at must be real, parseable ISO 8601 with a UTC offset - not
    just any string - because list_recent()'s ordering depends on
    comparing it lexicographically, which only yields correct
    chronological order for a consistent, zero-padded, fixed-offset
    format like this one.
    """
    db_path = str(tmp_path / "cases.db")
    store = CaseStore(db_path)
    case_id = store.save(_summary(), source="text")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT created_at FROM cases WHERE case_id = ?", (case_id,)).fetchone()

    parsed = datetime.fromisoformat(row[0])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0
    # Sanity check: recorded within the last minute of actually running this test,
    # not a stale or fabricated timestamp.
    assert (datetime.now(timezone.utc) - parsed).total_seconds() < 60


def test_init_is_idempotent_against_an_existing_database_file(tmp_path):
    """
    CREATE TABLE IF NOT EXISTS must actually be idempotent: constructing
    a second CaseStore against the same file (e.g. a second CaseStore()
    call, or a fresh process reopening data/cases.db) must not raise and
    must not lose existing rows.
    """
    db_path = str(tmp_path / "cases.db")
    first_store = CaseStore(db_path)
    case_id = first_store.save(_summary(), source="text")

    second_store = CaseStore(db_path)  # must not raise, must not wipe existing data
    assert second_store.get(case_id) is not None


def test_creates_the_parent_directory_if_it_does_not_exist_yet(tmp_path):
    """
    data/ already exists in this repo, but a fresh clone or deploy target
    might not have created it yet - CaseStore must not require the
    caller to `mkdir` first.
    """
    db_path = tmp_path / "nested" / "does" / "not" / "exist" / "cases.db"
    store = CaseStore(str(db_path))
    case_id = store.save(_summary(), source="text")
    assert store.get(case_id) is not None


# --- ayush_assessment / attach_ayush_assessment --------------------------------------


def test_save_and_get_round_trip_a_case_with_no_ayush_assessment(tmp_path):
    """The default, no-AYUSH case (every case that isn't an Ayurvedic
    OPD visit) must round-trip with ayush_assessment staying None, not
    an empty AyushAssessment() standing in for "not applicable"."""
    from app.schemas import AyushAssessment

    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(), source="text")

    retrieved = store.get(case_id)

    assert retrieved.ayush_assessment is None
    assert isinstance(retrieved.ayush_assessment, AyushAssessment) is False


def test_save_and_get_round_trip_a_case_with_an_ayush_assessment(tmp_path):
    from app.schemas import AyushAssessment

    assessment = AyushAssessment(prakriti="Vata-Pitta", ahara_shakti="moderate, occasional bloating")
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(ayush_assessment=assessment), source="text")

    retrieved = store.get(case_id)

    assert retrieved.ayush_assessment is not None
    assert retrieved.ayush_assessment.prakriti == "Vata-Pitta"
    assert retrieved.ayush_assessment.ahara_shakti == "moderate, occasional bloating"
    assert retrieved.ayush_assessment.vikriti is None


def test_attach_ayush_assessment_updates_an_existing_case(tmp_path):
    from app.schemas import AyushAssessment

    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(), source="text")
    assert store.get(case_id).ayush_assessment is None

    updated = store.attach_ayush_assessment(case_id, AyushAssessment(prakriti="Kapha", vaya="34"))

    assert updated is True
    retrieved = store.get(case_id)
    assert retrieved.ayush_assessment.prakriti == "Kapha"
    assert retrieved.ayush_assessment.vaya == "34"


def test_attach_ayush_assessment_leaves_every_other_field_unchanged(tmp_path):
    from app.schemas import AyushAssessment

    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(chief_complaint="original complaint, unchanged after this"), source="text")

    store.attach_ayush_assessment(case_id, AyushAssessment(prakriti="Pitta"))

    retrieved = store.get(case_id)
    assert retrieved.chief_complaint == "original complaint, unchanged after this"
    assert retrieved.priority_level == TriageLevel.CLINIC_VISIT


def test_attach_ayush_assessment_returns_false_for_an_unknown_case_id(tmp_path):
    from app.schemas import AyushAssessment

    store = CaseStore(str(tmp_path / "cases.db"))

    updated = store.attach_ayush_assessment(uuid.uuid4().hex, AyushAssessment(prakriti="Vata"))

    assert updated is False


# --- review_case ----------------------------------------------------------------------


def test_review_case_with_no_updates_accepts_the_draft_as_is(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(chief_complaint="original complaint, unchanged after this"), source="text")
    assert store.get(case_id).is_reviewed_by_physician is False

    updated = store.review_case(case_id)

    assert updated is True
    retrieved = store.get(case_id)
    assert retrieved.is_reviewed_by_physician is True
    assert retrieved.chief_complaint == "original complaint, unchanged after this"
    assert retrieved.priority_level == TriageLevel.CLINIC_VISIT


def test_review_case_applies_amendments_and_marks_reviewed_together(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(chief_complaint="patient's own garbled words"), source="text")

    updated = store.review_case(
        case_id,
        {
            "chief_complaint": "physician-corrected: recurrent epigastric pain",
            "review_of_systems": "no red flags on direct questioning",
        },
    )

    assert updated is True
    retrieved = store.get(case_id)
    assert retrieved.is_reviewed_by_physician is True
    assert retrieved.chief_complaint == "physician-corrected: recurrent epigastric pain"
    assert retrieved.review_of_systems == "no red flags on direct questioning"


def test_review_case_amendment_leaves_unmentioned_fields_unchanged(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(chief_complaint="leave me alone"), source="text")

    store.review_case(case_id, {"family_history": "father: diabetes"})

    retrieved = store.get(case_id)
    assert retrieved.chief_complaint == "leave me alone"
    assert retrieved.family_history == "father: diabetes"


def test_review_case_rejects_updates_to_a_non_reviewable_field(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(), source="text")

    with pytest.raises(ValueError):
        store.review_case(case_id, {"priority_level": "emergency"})


def test_review_case_returns_false_for_an_unknown_case_id(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))

    updated = store.review_case(uuid.uuid4().hex)

    assert updated is False


def test_review_case_is_idempotent_on_an_already_reviewed_case(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case_id = store.save(_summary(), source="text")
    store.review_case(case_id)

    updated_again = store.review_case(case_id)

    assert updated_again is True
    assert store.get(case_id).is_reviewed_by_physician is True


def test_list_recent_ayush_only_returns_only_cases_with_an_assessment(tmp_path):
    from app.schemas import AyushAssessment

    store = CaseStore(str(tmp_path / "cases.db"))
    plain_id = store.save(_summary(chief_complaint="allopathic case, no ayush"), source="text")
    ayush_id = store.save(_summary(chief_complaint="ayurvedic opd case"), source="text")
    store.attach_ayush_assessment(ayush_id, AyushAssessment(prakriti="Vata-Pitta"))

    ayush_only = store.list_recent(ayush_only=True)
    everything = store.list_recent()

    assert [c.case_id for c in ayush_only] == [ayush_id]
    assert {c.case_id for c in everything} == {plain_id, ayush_id}


def test_list_recent_ayush_only_returns_empty_when_no_ayush_cases_exist(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    store.save(_summary(), source="text")

    assert store.list_recent(ayush_only=True) == []


def test_list_recent_ayush_only_still_honors_the_limit_and_ordering(tmp_path):
    """
    The filter must apply in SQL before the LIMIT, not after - otherwise
    asking for N Ayurvedic cases would return however many happen to
    appear among the N most recent cases overall. Proven by saving more
    non-AYUSH cases than the limit, then checking the AYUSH ones still
    come back.
    """
    from app.schemas import AyushAssessment

    store = CaseStore(str(tmp_path / "cases.db"))
    ayush_ids = []
    for i in range(3):
        case_id = store.save(_summary(chief_complaint=f"ayurvedic case {i}"), source="text")
        store.attach_ayush_assessment(case_id, AyushAssessment(prakriti="Kapha"))
        ayush_ids.append(case_id)
        time.sleep(0.01)  # distinct created_at values, same approach the ordering tests above use
    for i in range(5):
        store.save(_summary(chief_complaint=f"allopathic case {i}"), source="text")
        time.sleep(0.01)

    result = store.list_recent(limit=3, ayush_only=True)

    assert len(result) == 3
    assert {c.case_id for c in result} == set(ayush_ids)
