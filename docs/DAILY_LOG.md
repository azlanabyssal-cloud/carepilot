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
