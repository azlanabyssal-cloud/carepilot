# Daily Log

Short, honest, factual. What got built, what didn't, what broke. No
inflation - a light day should read as a light day. Created retroactively
on Day 4 (28 Jul 2026); docs/DAILY_PROTOCOL.md asked the daily cloud
routine to maintain this from Day 1, but the routine has never
successfully run to completion (see Day 4 entry), so nothing was written
here until now.

## Day 1 — 25 Jul 2026

Built: Intake, Triage-Reasoning, Guideline-Verification, Referral agents
- all 4 core agents, tested, wired into `/assess`. Repo renamed
Arogya Sahayak → CarePilot, moved to `/carepilot`, put on GitHub
(public). Daily cloud routine configured. One real bug found and fixed:
`/triage` constructed the Anthropic backend before checking the red-flag
short-circuit, breaking the one path that's supposed to work with zero
API dependency.

## Day 2 — 26 Jul 2026

Built: `app/models/ocr.py` (Tesseract-based prescription reading) and
`app/models/cv_classifier.py` (MobileNetV3-Small transfer-learning
pipeline, untrained). `docs/STUDY_GUIDE.md` created - tiered, basic-to-
expert interview notes. One real wrong assumption caught: OCR
"preprocessing improves accuracy" turned out false on a low-contrast test
case (misread AMOXICILLIN as ANTONICILLIN). 35 tests passing by end of day.

## Day 3 — 27 Jul 2026

Built: `Dockerfile`/`.dockerignore` (built, run, `/health` verified live,
1.82GB image) and `app/adapters/bhashini.py` (Telugu ASR+translation
adapter, honestly unverified against the real API). Built via two
parallel subagents - first attempt with worktree isolation failed
instantly (session root isn't a git repo), retried without it. 43 tests
passing by end of day.

## Day 4 — 28 Jul 2026

Built: wired the Bhashini adapter into a live `POST /assess/voice`
endpoint - it existed since Day 3 but nothing called it until today.
Found and closed a real gap: zero automated tests existed for the
FastAPI layer itself before today (every endpoint check across 3 days
was manual curl) - `tests/test_main.py` now covers `/health`, `/intake`,
`/assess`, and `/assess/voice`. 52 tests passing by end of day.

**Daily cloud automation: confirmed broken, not just slow.** 4
consecutive scheduled/manual fires, zero commits. Ran a minimal
diagnostic (git remote/status/whoami + one trivial test commit+push) -
it also failed to push a single line, isolating the problem to push
access in the cloud sandbox, not task complexity. Root cause not fully
identified (no access to the cloud session's raw logs from here). Prompt
updated to at least commit locally and report the exact push failure
honestly on future runs, rather than silently produce nothing.

## Day 5 — 29 Jul 2026

Built: `app/evaluation.py` + `data/evaluation/test_cases.json` - the
evaluation harness, on the checklist unbuilt since Day 1. Real result
from an actual run, no live API key: 4/11 cases evaluable (the
deterministic red-flag path), 100% emergency recall on that subset, 7
cases correctly reported as skipped with the real reason. Recall
arithmetic hand-verified against a known answer in
`test_compute_report_emergency_recall_is_correct_with_a_known_false_negative`,
not just assumed correct because the code ran. 58 tests passing by end
of day (was 52).

## Day 6 — 29 Aug 2026

A full month gap since Day 5 - the daily cloud routine stayed broken the
entire time (see Day 4). This run's own push diagnostic confirms it's
still broken: `git push origin main --dry-run` returns a 403, "Claude
doesn't have GitHub access to azlanabyssal-cloud/carepilot for your
organization." Work below is committed locally in this session's
ephemeral container only - not pushed, not visible on GitHub yet.

Checked the next-undone checklist items for real instead of assuming:
SHAP/LIME is scoped to the CV classifier once trained (it isn't, and
isn't wired into `/assess`); CV training-data prep needs Kaggle/AIKosh,
and `curl` to `kaggle.com`, `data.gov.in`, and `aikosh.indiaai.gov.in`
all returned a 403 from this environment's own outbound proxy - a real,
tested result. The evaluation harness's remaining 7 cases need a live
`ANTHROPIC_API_KEY`, also unset here. All three genuinely blocked, so
today's Block 1 was hardening, per `docs/DAILY_PROTOCOL.md`'s own rule
for that situation.

Found and fixed one real bug: `POST /assess/voice` (`app/main.py`)
crashed with a raw, unhandled 500 if the Bhashini translation came back
empty or under 3 characters (silence, a garbled clip) - a
`pydantic.ValidationError` from `PatientInput`'s own `min_length=3`,
raised manually inside the handler, which FastAPI does not auto-convert
to a clean error the way it does for request-body validation. Fixed with
a `try/except ValidationError -> HTTPException(422, ...)`, matching the
status code `/intake` already uses for the same underlying failure on
typed input. Two regression tests added
(`test_assess_voice_returns_422_not_500_on_empty_translation`,
`test_assess_voice_returns_422_not_500_on_too_short_translation`).
Reinstalled `tesseract-ocr` (missing in this session's container, which
had been failing 3 OCR tests before that) so the full suite could
actually run clean. 60 tests passing by end of day (was 58), verified by
running `pytest` and separately curling a live `uvicorn` instance
(`/health`, `/assess` red-flag path, `/assess/voice` without
credentials - all behaving as documented). Documented in
`docs/INTERVIEW_NOTES.md`, Day 6.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked in this environment (see above) until either network access to
a real dataset source or a live `ANTHROPIC_API_KEY` is available. Daily
cloud automation is still broken and needs a human to fix GitHub access
for this org - not something further diagnosis from inside this
container can resolve.

## Day 7 — 30 Aug 2026

**The daily cloud automation actually worked today - and Day 6's "403,
no GitHub access" diagnosis was wrong.** Same diagnostic
(`git remote -v` then `git push origin main --dry-run`) run first, as
instructed, but this time it failed with `[rejected] main -> main
(non-fast-forward)`, not a 403. Investigated instead of repeating the
old claim: this container's local `main` branch ref was stale (5
commits behind), while `HEAD` was detached at a commit that already
matched `origin/main` - a prior session's commits had already reached
GitHub, the local branch pointer just never caught up. `git branch -f
main HEAD && git checkout main` fixed it; the dry-run then reported
"Everything up-to-date," and this session's real commits pushed
successfully. Corrected in `docs/INTERVIEW_NOTES.md`'s new Day 7 entry
rather than left standing.

Noted for the record, not acted on unilaterally: this repo's `main` now
also contains a substantial, separately-documented Smart India
Hackathon (SIH26047 / "MediKiosk") track - `docs/sih/`, an ABDM adapter,
a Groq backend, a demo frontend, structured OCR extraction, and a new
`/case-intake` endpoint - added in an interactive session earlier today
(commits `e0582e1` through `6d3612a`), not by this automated routine.
`docs/DAILY_PROTOCOL.md` and this routine's own instructions still scope
today's work strictly to the GPREC-placement checklist, so today's
Block 1/2 stayed on that checklist; the SIH track's own scope and
priority is the project owner's call, flagged to them directly rather
than assumed here.

Checked the GPREC checklist's next-undone items for real, same as Day
6: SHAP/LIME still blocked (CV classifier not trained/wired),
`ANTHROPIC_API_KEY`/`GROQ_API_KEY` still both unset, and
`kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in` still all
`CONNECT tunnel failed, response 403` from this environment's proxy -
re-tested today, not assumed carried over. All three still genuinely
blocked, so today's Block 1 was hardening again, per
`docs/DAILY_PROTOCOL.md`'s own rule.

Found and fixed two real bugs. First: `pip install -r requirements.txt`
failed outright on a clean venv - an earlier session today added
`google-genai==2.20.0` "for the Gemini backend work" that was never
actually written (`grep` for `genai`/`Gemini` under `app/` returns
nothing), and its `pydantic>=2.12.5` requirement conflicted with this
project's pinned `pydantic==2.9.2`. Fixed by removing the unused
dependency - anyone cloning this repo right now would have hit this
immediately. Second: `POST /case-intake` crashed with a raw 500 if the
AI history-drafting backend returned a short-but-non-empty
`chief_complaint` (e.g. `"ok"`) - the same failure class as Day 6's
`/assess/voice` bug (a manually-constructed Pydantic model bypassing
FastAPI's automatic request-boundary validation), just triggered by the
backend's own output this time. Fixed with a
`try/except ValidationError -> HTTPException(503, ...)` in
`app/main.py`. Both reproduced first with `TestClient(app,
raise_server_exceptions=True)` before being fixed, and both have
regression tests. Reinstalled `tesseract-ocr` (missing again in this
container). 110 tests passing (was 109 immediately after the dependency
fix, 110 after the regression test), verified from a freshly recreated
venv, not an already-patched one - and separately verified against a
live `uvicorn` instance: `/health`, `/assess` (red-flag path),
`/case-intake` (red-flag path and no-API-key path) all curled directly
and behaving as documented. Documented in `docs/INTERVIEW_NOTES.md`,
Day 7.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (see above). The evaluation harness's remaining 7 cases still
need a live `ANTHROPIC_API_KEY`. Daily cloud automation is now confirmed
working - today's commits pushed to `origin/main` successfully.

## Day 8 — 31 Aug 2026

Push diagnostic (`git remote -v`, `git push origin main --dry-run`) run
first, as instructed. Same `[rejected] main -> main (non-fast-forward)`
Day 7 already saw and fixed - because Day 7's fix (`git branch -f main
HEAD && git checkout main`) was a container-local git-state repair, and
this routine's containers don't persist between runs. Each fresh
container starts detached with the same stale local `main` pointer (still
at `01785ef`, 25+ commits behind) that predates Day 7 entirely. Re-ran the
identical fix; `git push origin main --dry-run` then reported
"Everything up-to-date," and this session's commits pushed successfully.
Documented in `docs/INTERVIEW_NOTES.md`'s new Day 8 entry so a future
session doesn't have to re-diagnose this from scratch - the fix is real
and cheap but needs re-running every fresh container, not once.

Checked the GPREC checklist's next-undone items fresh, same discipline as
Days 6/7: no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this environment, so
SHAP/LIME and the evaluation harness's remaining 7 cases are still
blocked; `kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in` still all
return `connect_rejected` from this environment's outbound proxy - same
result as Days 6 and 7. All three still genuinely blocked, so today's
Block 1 was hardening again, per `docs/DAILY_PROTOCOL.md`'s own rule.

Noted for the record, not acted on or re-documented here (same boundary
Day 7 already drew): a substantial interactive SIH26047 session continued
between Day 7's automated run and this one (`docs/sih/`, `/case-intake/voice`,
`/case-intake/document`, case persistence via `app/db.py`, audio output,
a redesigned demo frontend - commits `1801076` through `f7abd11`). Real,
tested, already pushed, and out of this routine's own GPREC-placement
scope - flagged to the project owner, not this routine's to judge or
absorb into today's checklist.

Found and fixed one real bug, by reading that new code with the same
scrutiny already applied to the original four agents: `ClinicalHistorySummary
.chief_complaint` (`app/schemas.py`) could be satisfied by a string made
entirely of invisible Unicode format characters (e.g. three U+200B ZERO
WIDTH SPACE) - the exact same failure class Day 1 already fixed for
`PatientInput.symptom_text`, never applied to this newer field added by
the SIH track. Traced to a real, reachable path:
`app/agents/history_intake.py`'s `_parse()` only rescues an *empty*
`CHIEF_COMPLAINT` line, and `str.strip()` doesn't remove invisible format
characters, so a plausible backend response produces a
`ClinicalHistorySummary` a physician would open and see as completely
blank, silently persisted as if it were real. Fixed with a shared
`_visible_length()` helper reused by both `PatientInput` and
`ClinicalHistorySummary`'s own field validators, so the two fields can't
drift apart again. Four new regression tests across three layers (schema,
agent parse path, live `/case-intake` endpoint) - see
`docs/INTERVIEW_NOTES.md`, Day 8. Ran `pytest` - 150 passed (was 146 at
session start, zero regressions) - then separately started the real
`uvicorn` server and curled it directly: `/health`, `/assess` (red-flag
path), `/case-intake` (red-flag path, real persisted `case_id`, a
`GET /cases/{case_id}` round-trip), and `/case-intake` without an API key
on a non-red-flag case (clean `503`) - all behaving as documented.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (see above). The evaluation harness's remaining 7 cases still
need a live `ANTHROPIC_API_KEY`. Daily cloud automation's real,
recurring failure mode is now understood and documented (container-local
git-state fix, not a one-time repair) - future sessions should expect to
re-run it, not be surprised by it.

## Day 9 — 1 Sep 2026

Push diagnostic (`git remote -v`, `git push origin main --dry-run`) run
first, as instructed, and reported verbatim at the start of the session:
same `[rejected] main -> main (non-fast-forward)` Days 7 and 8 already
saw and fixed, each in their own container. Confirms Day 8's own
prediction - the fix is container-local and doesn't persist, so it needs
re-running every fresh session, not once. Diagnosed fresh rather than
assumed: `HEAD` detached at `fcb7d07` (already matching `origin/main`),
local `main` still stuck at `01785ef`. Confirmed `01785ef` is a clean
ancestor of `fcb7d07` (`git merge-base --is-ancestor`) before touching
anything, then fast-forwarded with `git checkout main && git merge
--ff-only origin/main` - functionally the same fix as Days 7/8's `git
branch -f main HEAD`. `git push origin main --dry-run` then reported
"Everything up-to-date."

Checked the GPREC checklist's next-undone items fresh, same discipline as
Days 6-8: no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this environment, so
SHAP/LIME and the evaluation harness's remaining 7 cases are still
blocked; `kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in` still all
return `CONNECT tunnel failed, response 403` from this environment's
outbound proxy - same result as Days 6-8. All three still genuinely
blocked, so today's Block 1 was hardening again, per
`docs/DAILY_PROTOCOL.md`'s own rule.

Found and fixed one real bug, by auditing `app/agents/history_intake.py`'s
`_parse()` for every field sharing the fallback pattern Day 8 already
proved unsafe for `chief_complaint`, not by waiting for a new incident:
`ClinicalHistorySummary.history_of_present_illness` (`app/schemas.py`)
had no validation at all - not even `min_length` - despite `_parse()`
using the identical `fields.get("HPI") or case.symptom_text` fallback
that fails silently on invisible-Unicode-only input (e.g. three U+200B
ZERO WIDTH SPACE characters), the same shape Day 8 already proved reaches
this code from a plausible backend response. Reproduced directly first -
constructing the schema with an invisible-only value, then tracing it
through the real `_parse()` path - before writing any fix. Fixed by
giving `history_of_present_illness` the same `Field(..., min_length=3)`
plus the shared `_visible_length()` Cf-filter validator `chief_complaint`
already uses, rather than a third, possibly-drifting copy of the same
check. Six new regression tests across three layers (schema, agent parse
path, live `/case-intake` endpoint) - see `docs/INTERVIEW_NOTES.md`, Day
9. Ran `pytest` - 156 passed (was 150 at session start, zero
regressions) - then separately started the real `uvicorn` server and
curled it directly: `/health`, `/case-intake` (red-flag path, real
persisted `case_id`), `/assess` (red-flag path), and `/case-intake`
without an API key on a non-red-flag case (clean `503`) - all behaving as
documented.

Honest gap named, not fixed: the five optional narrative fields
(`past_medical_surgical_history`, `drug_allergy_history`,
`family_history`, `personal_history`, `review_of_systems`) still have no
invisible-content guard. Lower-stakes than the two required fields, since
their correct default is already `None`, but a real, named next place to
look rather than silently assumed covered by today's fix.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (see above). The evaluation harness's remaining 7 cases still
need a live `ANTHROPIC_API_KEY`. The five optional `ClinicalHistorySummary`
narrative fields still lack an invisible-content guard - named above as
the next hardening target if the build-order items are still blocked
tomorrow.
