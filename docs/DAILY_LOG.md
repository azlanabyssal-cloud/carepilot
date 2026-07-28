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
