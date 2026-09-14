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

## Day 10 — 2 Sep 2026

Push diagnostic run first, as instructed, and reported verbatim at the
start of the session: same `[rejected] main -> main (non-fast-forward)`
Days 7-9 already saw and fixed, each in their own container. Diagnosed
fresh: `HEAD` detached at `ab0fe58` (already matching `origin/main`
exactly), local `main` still stuck at `01785ef`. Confirmed `01785ef` is a
clean ancestor of `ab0fe58` (`git merge-base --is-ancestor`) before
touching anything, then fixed with `git checkout -B main HEAD` -
functionally the same fix Days 7-9 each ran. `git push origin main
--dry-run` then reported "Everything up-to-date." Fourth session in a row
this exact container artifact has recurred and been re-fixed - confirms
it is a genuine per-session container quirk, not a real access problem.

Before any build work, read `README.md`, `docs/DAILY_PROTOCOL.md`, and
`docs/INTERVIEW_NOTES.md` in full, per this routine's own instructions.
That read turned up a real problem with the *previous two sessions'* own
scoping, not a code bug: Days 8 and 9's "hardening" fixes were both made
to `ClinicalHistorySummary`/`app/agents/history_intake.py` - the
SIH26047 track's own output contract, consumed only by `/case-intake*`,
which `README.md`'s own Day 8 line already flags as "out of this
routine's own GPREC-placement scope per `docs/DAILY_PROTOCOL.md`."
`docs/DAILY_PROTOCOL.md`'s own end-of-day check #3 ("on-campus GPREC
specifically... not an off-campus story already ruled out of scope")
should have caught this on both days and didn't. Both fixes are real,
correct bug fixes - nothing was reverted - but the choice of *what to
work on* on those two days drifted outside this routine's own stated
scope. Flagged plainly in `README.md` and `docs/INTERVIEW_NOTES.md`
rather than smoothed over or repeated a third time.

Checked the GPREC checklist's next-undone items fresh, same discipline
as every prior day: no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this
environment, so SHAP/LIME and the evaluation harness's remaining 7 cases
are still blocked; `kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in`
still all return `connect_rejected` from this environment's outbound
proxy. All three still genuinely blocked, so today's Block 1 was
hardening again - this time actually inside the in-scope pipeline.

Found and fixed one real bug in the core, in-scope Triage-Reasoning
agent: `TriageDecision.rationale` (`app/schemas.py`) had zero validation
- not even a raw `min_length` floor - despite both
`AnthropicReasoningBackend._parse()` (`app/agents/triage.py`) and its
verbatim copy `GroqReasoningBackend._parse()`
(`app/agents/groq_backends.py`) building it from a model response line
the exact same way `chief_complaint`/`history_of_present_illness` are,
sharing the identical `.strip()`-leaves-invisible-Unicode-untouched gap.
Reproduced directly first - `AnthropicReasoningBackend._parse("LEVEL:
urgent\nRATIONALE: <three U+200B ZERO WIDTH SPACE>")` constructed a
`TriageDecision` with a rationale that is three characters long to
Python and completely blank to a human, with no error - before writing
any fix. Fixed with the same `Field(..., min_length=3)` plus the shared
`_visible_length()` validator pattern the other three fields already
use, plus one thing those fixes didn't need: `propose()` in both
backends now catches the resulting `ValidationError` and re-raises
`TriageBackendError`, so `app/main.py`'s existing `except
TriageBackendError` -> 503 handling catches it with zero changes needed
in `main.py`. Seven new regression tests across three layers (schema,
both backends' parse path, live `/assess` endpoint) - see
`docs/INTERVIEW_NOTES.md`, Day 10. Ran `pytest` - 163 passed (was 156 at
session start, zero regressions) - then separately started the real
`uvicorn` server and curled it directly: `/health`, `/assess` (red-flag
path, real `emergency` result), `/assess` without an API key on a
non-red-flag case (clean `503`, "Triage reasoning backend is not
configured."), and `/triage` (red-flag path, confirmed the existing,
already-safe rationale text - "Deterministic red-flag term(s)
detected:..." - still comes through unchanged, since that path never
calls `_parse()`).

Honest gap named, not fixed: the same five optional
`ClinicalHistorySummary` narrative fields Day 9 already named remain
unguarded - still not today's fix, since today deliberately stayed off
the SIH26047 track. `TriageDecision.confidence` and `TriageLevel` were
not re-audited beyond `rationale` today (both are structurally
lower-risk - `confidence` already has a numeric range constraint,
`TriageLevel` is a closed `Enum` - but that's a reason, not a proof).

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (see above). The evaluation harness's remaining 7 cases still
need a live `ANTHROPIC_API_KEY`. If those are still blocked tomorrow, the
in-scope pipeline's own remaining hardening targets are `TriageDecision.confidence`/`TriageLevel`
(named above, not yet re-verified) or a fresh full-file audit of
`app/agents/verify.py` and `app/agents/referral.py` for the same
failure class, neither of which has had this specific audit applied yet.

## Day 11 — 3 Sep 2026

Push diagnostic run first, as instructed, and reported verbatim at the
start of the session: `git push origin main --dry-run` reported
"Everything up-to-date" immediately - the first session in six that
didn't need a branch-pointer fix. `HEAD` was detached at the same commit
local `main` already pointed to, so `git checkout main` was a plain
attach, not a fast-forward repair. Recorded plainly rather than assumed
identical to Days 7-10's recurring symptom.

Checked the GPREC checklist's next-undone items fresh, same discipline
as every prior day: no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this
environment; `kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in` all still
return `CONNECT tunnel failed, response 403` from this environment's
outbound proxy - the sixth consecutive day this exact check has come
back identical. Both SHAP/LIME and CV-model training-data prep are still
genuinely blocked. Per `docs/DAILY_PROTOCOL.md`'s own fallback rule, and
per Day 10's own explicit pointer ("a fresh full-file audit of
`app/agents/verify.py` and `app/agents/referral.py` for the same failure
class"), today's hardening pass audited every in-scope agent module for
the validation-boundary failure class the last five days kept finding.

Found and fixed one real bug, one layer earlier than the last five days'
schema-field fixes: `AnthropicReasoningBackend._call`
(`app/agents/triage.py`) did `message.content[0].text` with **no guard
at all**, while every other third-party-API backend in this codebase
(`GroqReasoningBackend._call`, `app/adapters/bhashini.py`) already
catches `(KeyError, IndexError)` on the equivalent response-shape
parsing. Reproduced directly first: a `MagicMock`-based fake Anthropic
client returning a message with an empty `content` list made
`AnthropicReasoningBackend._call` raise a raw `IndexError`, confirmed
before any fix was written, and confirmed the same `IndexError`
propagates through `propose()` uncaught too, since `propose()`'s own
`except (APIConnectionError, RateLimitError, APIStatusError)` doesn't
match it - meaning it would have reached `/assess`/`/triage` as an
undocumented 500, the exact failure class the last five days already
fixed five times, just in a call site none of those audits had reason to
check (they were all auditing Pydantic schema fields one step
downstream of this one). Fixed with `try/except (IndexError,
AttributeError)` around the access, raising `TriageBackendError`
directly - the same pattern Groq's backend already uses - so
`app/main.py`'s existing 503 handling catches it with zero changes
needed there. Three regression tests across two layers (`_call`/`propose`
in isolation in `tests/test_triage.py`, live `/assess` endpoint in
`tests/test_main.py`), all monkeypatching the Anthropic client/`.create`
method itself rather than `_call`, so the actual new code path under
test really runs. Reinstalled `tesseract-ocr` (missing again in this
container, the sixth session in a row to need it). Ran `pytest` - 166
passed (was 163 at session start, zero regressions) - then separately
started the real `uvicorn` server and curled it directly: `GET /health`
returned `{"status":"ok"}`; `POST /assess` with a red-flag symptom
returned a real `{"level":"emergency", ...}` result with zero API key
needed; `POST /assess` with an ordinary symptom and no
`ANTHROPIC_API_KEY` returned the expected `503`, `"Triage reasoning
backend is not configured."` - both existing paths unchanged.

Honest gap named, not fixed: the identical unguarded
`message.content[0].text` in `app/agents/history_intake.py`'s
`AnthropicHistoryDraftingBackend._call` is real and structurally
identical, but that module is `/case-intake*`'s own SIH26047 output
contract, out of this routine's own GPREC-placement scope per Day 10's
correction - so today's fix deliberately stayed inside
`app/agents/triage.py` only, the same scope discipline Day 10
established. Documented in `docs/INTERVIEW_NOTES.md`, Day 11.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (see above). The evaluation harness's remaining 7 cases still
need a live `ANTHROPIC_API_KEY`. `TriageDecision.confidence`/`TriageLevel`
(named in Day 10's own "what's next") still haven't been directly
re-audited. If tomorrow's build-order items are still blocked, remaining
in-scope hardening targets are that field-level re-check, or continuing
today's response-shape-parsing audit into `app/agents/verify.py` and
`app/agents/referral.py` specifically (today's audit covered them by
reading, not by writing a new defensive test for either, since neither
builds a model from unguarded parsed API output the way `triage.py`
does).

## Day 12 — 5 Sep 2026

**Push diagnostic, run first as instructed and reported verbatim:**
this session's own instructions specifically flagged that recent
automated runs, including a minimal diagnostic-only run, had failed to
push even a single-line change. `git remote -v` confirmed origin is
`https://github.com/azlanabyssal-cloud/carepilot`. `git push origin
main --dry-run` reported `[rejected] main -> main (non-fast-forward)` -
the exact symptom Days 7-10 already diagnosed and fixed four times.
Rather than stop at that error text (which is exactly where a prior
"diagnostic-only" run must have stopped, since it still reported
failure), this session compared the actual commit graph: `git log
--oneline -1 origin/main` and `git log --oneline -1 HEAD` were
identical (`45e2d87`, Day 11's last commit) - `HEAD` was detached and
already at `origin/main`'s tip. `git branch -a -v` showed the actual
cause: local branch `main` was still stuck at `8515dda` (Day 10's
commit, one behind `HEAD`). `git push origin main` pushes the *local
branch* `main`, not `HEAD`, so it was rejected for trying to push a
stale ref, not because of any GitHub permissions problem. Fixed
identically to Days 7-11: `git branch -f main HEAD && git checkout
main`, confirmed clean with `git status` ("nothing to commit, working
tree clean," "Your branch is up to date with 'origin/main'"). This is
the sixth session in which this exact stale-local-branch-ref artifact
has recurred and been re-fixed in under a minute - real, cheap, and
apparently a permanent feature of how this container's checkout step
leaves the repo at session start, not a regression in anything this
routine did.

Checked the GPREC checklist's next-undone items fresh: `env | grep -i
"anthropic\|groq"` and a direct check for a `.env` file both confirm no
`ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this environment;
`kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in` all still return
`CONNECT tunnel failed, response 403` from this environment's outbound
proxy - the seventh consecutive day this exact check has come back
identical. Both SHAP/LIME and CV-model training-data prep are still
genuinely blocked. Per Day 11's own "what's next" pointer, audited the
two named-but-unchecked areas: `TriageDecision.confidence` (already has
a real `ge=0.0, le=1.0` numeric range constraint - not the
invisible-content failure class this pass checks for) and `TriageLevel`
(a closed `Enum`, structurally safe) both came back clean; a fresh
full-file read of `app/agents/verify.py` and `app/agents/referral.py`
also came back clean - every `TriageDecision`/`ReferralResult` either
constructs from already-validated fields or fixed local strings, never
from unguarded third-party response parsing. Confirming these areas are
actually safe, not just assumed safe, is itself today's first real
result.

Found and fixed one real bug, one call site more specific than Day 11's:
`GroqReasoningBackend._call` (`app/agents/groq_backends.py`) already had
`except (KeyError, IndexError)` around
`response.json()["choices"][0]["message"]["content"]` - looking, at a
glance, like the exact defense-in-depth Day 11 added for the Anthropic
backend. But that guard only covers a malformed *already-parsed* JSON
shape. `response.raise_for_status()` only rejects a non-2xx status code
- a 200 response whose body isn't valid JSON at all (a misconfigured
proxy/gateway returning an HTML error page with a 200 status, a real,
documented failure mode for third-party HTTP APIs) makes
`response.json()` itself raise `json.JSONDecodeError`, a `ValueError`
neither `KeyError` nor `IndexError` catches. Reproduced directly first:
constructing a bare `httpx.Response(200, ..., content=b"not json")` and
calling `.json()` on it raises `json.JSONDecodeError`, confirmed in
isolation before touching any real code; then monkeypatched
`backend._client.post` to return exactly that malformed response and
called `GroqReasoningBackend._call(case)` directly - raised the raw,
uncaught `json.JSONDecodeError`, confirmed before any fix existed; then
called `.propose(case)` on the same fake client and confirmed the same
exception propagates through `propose()` uncaught too, since neither
`propose()`'s own `except (httpx.ConnectError, httpx.TimeoutException,
httpx.HTTPStatusError)` nor tenacity's own retry predicate
(`_is_retryable_http_error`) matches `json.JSONDecodeError` - meaning it
would reach any caller of `run_triage_reasoning()` built on this backend
as a raw, undocumented exception, same failure class as the five bugs
Days 6-11 already fixed, just never simulated at this exact call site
because every prior audit checked already-parsed values, not the JSON
parse step itself. Fixed by widening the `except` clause to
`(KeyError, IndexError, json.JSONDecodeError)`, reusing the same
`raise TriageBackendError(...)` conversion already there. Two new
regression tests
(`test_groq_reasoning_backend_call_converts_non_json_response_to_triage_backend_error`,
`test_groq_reasoning_backend_propose_converts_non_json_response_to_triage_backend_error`
in `tests/test_groq_backends.py`), both mocking `backend._client.post`
directly (not `_call`) so the real fixed code actually runs under test.
Reinstalled `tesseract-ocr` via `apt-get` (missing again in this
container, the seventh session in a row to need it). Ran `pytest` -
168 passed (was 166 at session start, zero regressions) - then
separately started the real `uvicorn` server and curled it directly:
`GET /health` returned `{"status":"ok"}`; `POST /assess` with a
red-flag symptom returned a real `{"level":"emergency", ...}` result
with zero API key needed; `POST /assess` with an ordinary symptom and no
`ANTHROPIC_API_KEY` returned the expected `503`, `"Triage reasoning
backend is not configured."` - both existing paths unchanged, since
today's fix only touches the Groq backend, which isn't wired into any
live endpoint yet.

Honest gap named, not fixed: the identical `GroqHistoryDraftingBackend._call`
gap in the same file (`app/agents/groq_backends.py`) is real and
structurally identical, but that backend serves `/case-intake*`'s
SIH26047 output contract, out of this routine's own GPREC-placement
scope per Day 10's correction - so today's fix deliberately stayed
inside `GroqReasoningBackend` only, the same scope discipline Day 10
established and Day 11 already held once. Documented in
`docs/INTERVIEW_NOTES.md`, Day 12.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (see above, seventh consecutive day). The evaluation harness's
remaining 7 cases still need a live `ANTHROPIC_API_KEY`. With
`TriageDecision.confidence`/`TriageLevel` and `verify.py`/`referral.py`
now confirmed clean, and the in-scope response-shape-parsing gaps in
both Anthropic and Groq triage backends now fixed, the next honest
places to look for a genuinely new instance of the validation-boundary
failure class are narrower: `app/adapters/bhashini.py`'s own four
`response.json()`-style parse sites (built early, Day 3, before this
specific JSON-decode-failure sub-case was ever considered) have not
been re-checked against today's exact finding, or a session could
finally move fully to build work the moment either an API key or
outbound access to a training-data source becomes available.

## Day 13 — 6 Sep 2026

**Push diagnostic, run first as instructed and reported verbatim:**
`git remote -v` confirmed origin is
`https://github.com/azlanabyssal-cloud/carepilot`. `git push origin
main --dry-run` reported `[rejected] main -> main (non-fast-forward)` -
the same symptom Days 7-12 already diagnosed and fixed seven times.
Verified with the same commit-graph comparison Day 12 established:
`git rev-parse HEAD`, `git rev-parse origin/main`, and `git rev-parse
refs/heads/main` printed separately - `HEAD` (`2de1e58`) already matched
`origin/main` exactly, while local `refs/heads/main` was stuck at
`8515dda` (Day 10's commit, three behind). Confirms this is the
standing stale-local-branch-ref artifact, not a GitHub access problem -
GitHub access was never the issue on any of these eight sessions. Fixed
with `git checkout -B main HEAD`, confirmed with a second `--dry-run`
reporting "Everything up-to-date" before any other work started.

Re-checked the checklist's next-undone items fresh, not assumed carried
over: no `ANTHROPIC_API_KEY`/`GROQ_API_KEY`/`BHASHINI_USER_ID`/
`BHASHINI_API_KEY` anywhere in this environment, and `kaggle.com`,
`data.gov.in`, and `aikosh.indiaai.gov.in` all still return `CONNECT
tunnel failed, response 403` from this environment's own outbound
proxy - the eighth consecutive day this exact check has come back
identical. SHAP/LIME, CV-model training, and the evaluation harness's
remaining 7 cases are all still genuinely blocked.

Per Day 12's own "what's next" pointer, audited `app/adapters/bhashini.py`'s
four `response.json()` call sites against Day 12's exact
`json.JSONDecodeError` finding for the first time - they were built Day
3, before that failure sub-case was ever considered, and had never been
re-checked against it. Found a real, in-scope bug: `_get_pipeline_config`
called `response.json()` entirely outside its own `except (KeyError,
IndexError, StopIteration)` block, and `_post_inference` had no guard of
any kind around its own `response.json()`. A 200 response with a
non-JSON body - the same misconfigured-proxy/gateway failure mode Day 12
already fixed for the Groq backend - raised a raw `json.JSONDecodeError`
straight through `transcribe()`, `translate()`, and `synthesize()`, none
of whose `except (KeyError, IndexError)` clauses caught it. In scope,
not SIH26047: `RealBhashiniAdapter` is exactly what the core
`/assess/voice` endpoint (`app/main.py`) constructs and calls.

Reproduced directly before writing any fix: mocked `httpx.post` to
return a 200 response with a non-JSON body, called
`RealBhashiniAdapter.transcribe()` directly, and watched the raw
`json.JSONDecodeError` propagate uncaught. Then traced it through the
real FastAPI app with `TestClient(app, raise_server_exceptions=True)`,
confirming the same raw exception reached `/assess/voice` uncaught,
since `app/main.py`'s existing `except BhashiniAdapterError` around
`bhashini_to_intake()` doesn't match it. Confirmed the second parse site
(`_post_inference`) independently, with a fake `httpx.post` returning a
valid pipeline-config response followed by a non-JSON inference
response.

Fixed by widening `transcribe()`'s, `translate()`'s, and `synthesize()`'s
own `except (KeyError, IndexError)` clauses to include
`json.JSONDecodeError` (covers `_post_inference`'s unguarded parse, since
it's always called inside these methods' own try blocks), and by moving
`_get_pipeline_config`'s `response.json()` call inside its existing try
block so it converts to `BhashiniAdapterError` at the same place its
sibling parsing errors already do, keeping that method's own documented
promise ("raises `BhashiniAdapterError` directly on an unexpected
response shape") literally true rather than relying only on the
callers' outer catch.

Five new regression tests, all confirmed to fail against the pre-fix
code (via `git stash` on just `app/adapters/bhashini.py`, re-run,
watched them fail with the real traceback, then restored the fix)
before being counted as passing: four in `tests/test_bhashini.py`
covering both parse sites across all three public methods
(`transcribe`/`translate`/`synthesize`, so the fix is proven applied to
each one's own separate `except` clause, not just the first), and one
in `tests/test_main.py` running the real `RealBhashiniAdapter` - not a
fake substituted for it - through the live `/assess/voice` endpoint with
fake-but-present credentials and a monkeypatched `httpx.post`,
confirming a clean `503` instead of a raw 500. Ran `pytest` from a
completely fresh venv (`python3.13 -m venv`, `pip install -r
requirements.txt` from the clean clone, `tesseract-ocr` reinstalled via
`apt-get` - this container also started with neither, the eighth
session in a row to need both) - **173 passed, up from 168 at session
start, zero regressions**. Then separately started the real `uvicorn`
server and curled it directly: `GET /health` returned `{"status":"ok"}`;
`POST /assess` with a red-flag symptom returned a real
`{"level":"emergency", ...}` result with zero API key needed;
`POST /assess/voice` without Bhashini credentials returned the expected
`503`, `"Bhashini backend is not configured."` - both existing paths
unchanged. Documented in `docs/INTERVIEW_NOTES.md`, Day 13, including an
honest discussion of when this now-three-times-repeated failure class
(Day 11 Anthropic, Day 12 Groq, today Bhashini) would be worth fixing
structurally instead of per call site - judged not yet, with the actual
threshold named (a fourth occurrence in a fourth differently-shaped
API).

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (eighth consecutive day). The evaluation harness's remaining 7
cases still need a live `ANTHROPIC_API_KEY`. With today's fix, every
known instance of the "unguarded third-party response parsing" failure
class across all three backends (Anthropic, Groq, Bhashini) that this
routine has audited is now fixed - the next genuinely new place to look,
if the pattern holds, is a fourth differently-shaped integration this
routine hasn't built yet, or a session could finally move fully to build
work the moment either an API key or outbound access to a
training-data source becomes available.

## Day 14 — 7 Sep 2026

**Push diagnostic, run first as instructed and reported verbatim:**
`git remote -v` confirmed origin is
`https://github.com/azlanabyssal-cloud/carepilot`. `git push origin main
--dry-run` reported `[rejected] main -> main (non-fast-forward)` - the
same symptom Days 7-13 already diagnosed and fixed nine times. Verified
with the same commit-graph comparison Day 12 established: `git rev-parse
HEAD` (`3dfbf01`) already matched `origin/main` exactly, while local
`refs/heads/main` was stuck at `8515dda` (Day 10's commit, three behind -
one of the three intervening commits was a same-day SIH26047-track
session's own work, already merged to `origin/main` before this session
started). Confirmed with `main..origin/main`/`origin/main..main` that
zero local commits would be lost. Fixed with `git checkout -B main
origin/main`, confirmed with a second `--dry-run` reporting "Everything
up-to-date" before any other work started.

Re-checked the checklist's next-undone items fresh: no
`ANTHROPIC_API_KEY`/`GROQ_API_KEY`/`BHASHINI_USER_ID`/`BHASHINI_API_KEY`
anywhere in this environment, and `kaggle.com`, `data.gov.in`, and
`aikosh.indiaai.gov.in` all still `connect_rejected` ("organization
policy") from this environment's own outbound proxy - the ninth
consecutive identical result. SHAP/LIME, CV-model training, and the
evaluation harness's remaining 7 cases are all still genuinely blocked.

Re-read every in-scope file in full (`app/schemas.py`,
`app/agents/intake.py`, `app/agents/triage.py`,
`app/agents/groq_backends.py`'s `GroqReasoningBackend` half,
`app/agents/verify.py`, `app/agents/referral.py`,
`app/adapters/bhashini.py`, `app/main.py`'s in-scope routes) rather than
assuming Days 6-13's response-parsing bug class still had unaudited
instances - it didn't; every call site already hardened stayed hardened,
and a same-day SIH26047-track session (commit `3dfbf01`, already on
`origin/main` before this session started) had independently closed the
remaining out-of-scope instances in `app/adapters/abdm.py` and
`GroqHistoryDraftingBackend`. An honest null result on that specific bug
class, stated plainly rather than manufactured.

Found a real bug of a different shape instead, in
`app/agents/intake.py`'s `scan_red_flags()` - Entry 1's own red-flag
scanner, the project's oldest component. Every multi-word entry in
`RED_FLAG_TERMS` ("chest pain", "difficulty breathing", "severe
bleeding", "sudden weakness", "slurred speech", "high fever with stiff
neck", "not breathing") was matched with a plain `term in lowered`
substring check requiring the exact single-space spelling. Reproduced
directly first: `scan_red_flags("I have chest  pain since morning")`
(double space), a newline variant, a triple-space variant, and a tab
variant all returned `[]` instead of catching the term. A double space
is an ordinary mobile-keyboard typo, not a contrived input - and unlike
every prior day's bug, this one fails silently: no exception, nothing in
the logs, the case just quietly falls through to the Triage-Reasoning
Agent instead of short-circuiting to `EMERGENCY`, defeating the "two
independent mechanisms" defense Entry 1 exists for.

Fixed by collapsing any run of whitespace (spaces, tabs, newlines) to a
single space before matching. Single-word terms were unaffected;
`case.symptom_text` itself is untouched, only what the scanner compares
against. Four new regression tests in `tests/test_intake.py`, three
confirmed to fail against the pre-fix code (`AssertionError: assert
'chest pain' in []`) before being counted as passing, plus a fourth
proving the fix doesn't over-match unrelated text with irregular
whitespace. Ran `pytest` from a fresh venv (`python3.13 -m venv`,
`tesseract-ocr` reinstalled via `apt-get` - the ninth session in a row to
need both) - **189 passed, up from 185 at session start, zero
regressions**. Then started the real `uvicorn` server and curled it
directly: the original single-space "chest pain since this morning"
still returned `emergency`; the double-space and newline variants now
*also* correctly returned `emergency`, where they previously would have
silently fallen through; an ordinary non-red-flag case with no
`ANTHROPIC_API_KEY` still returned the expected `503`. Documented in
`docs/INTERVIEW_NOTES.md`, Day 14.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (ninth consecutive day). The evaluation harness's remaining 7
cases still need a live `ANTHROPIC_API_KEY`. Today's audit found the
whole in-scope response-parsing bug class this routine has chased since
Day 11 genuinely closed out - the next hardening pass should look for a
fresh failure class entirely (today's whitespace-normalization bug is
one example of what that can look like: re-examine an old, "settled"
component's actual matching/parsing behavior against realistic input
variation, not just re-check the same third-party-API-parsing shape a
tenth time), or a session could move fully to build work the moment an
API key or outbound data-source access becomes available.

## Day 15 — 8 Sep 2026

**Push diagnostic, run first as instructed and reported verbatim:**
`git remote -v` confirmed origin is
`https://github.com/azlanabyssal-cloud/carepilot`. `git push origin main
--dry-run` reported `Everything up-to-date` immediately - no rejection,
the first genuinely clean start since Day 11. Verified with the same
commit-graph comparison Day 12 established: `git rev-parse HEAD`,
`git rev-parse origin/main`, and `git rev-parse refs/heads/main` all
printed the identical hash (`962550b`) before any other work started -
no stale local `main` pointer to fix today.

Re-checked the checklist's next-undone items fresh: no
`ANTHROPIC_API_KEY`/`GROQ_API_KEY`/`BHASHINI_USER_ID`/`BHASHINI_API_KEY`
anywhere in this environment, and `kaggle.com`, `data.gov.in`, and
`aikosh.indiaai.gov.in` all still `CONNECT tunnel failed, response 403`
from this environment's own outbound proxy - the tenth consecutive
identical result. SHAP/LIME, CV-model training, and the evaluation
harness's remaining 7 cases are all still genuinely blocked.

Followed Day 14's own named direction for the next hardening pass -
re-examine an old, "settled" component's actual matching/parsing
behavior against realistic input variation, one layer past the red-flag
scanner Day 14 already fixed. Found a real, in-scope bug in
`AnthropicReasoningBackend._parse` (`app/agents/triage.py`) and its
verbatim copy `GroqReasoningBackend._parse` (`app/agents/groq_backends.py`):
both matched each line of the model's raw response with
`line.upper().startswith("LEVEL:")` / `"RATIONALE:"`, with no leading
whitespace stripped from the line first. A response indented by even one
leading space - a markdown bullet, a numbered step, or a code-fence
remnant, all realistic LLM formatting habits despite the prompt asking
for "exactly two lines, no other text" - silently missed both prefixes.

Reproduced directly before writing any fix:
```python
from app.agents.triage import AnthropicReasoningBackend
raw = "  LEVEL: emergency\n  RATIONALE: Severe crushing chest pain radiating to the arm."
AnthropicReasoningBackend._parse(raw).level   # -> TriageLevel.URGENT, not EMERGENCY
```
Confirmed identically in `GroqReasoningBackend._parse`. This is a worse
failure than a genuinely unparseable response's safe `URGENT` default:
here the model's judgment was correctly `emergency`, and the parser
silently de-escalated it one level - exactly the wrong-direction failure
this project's own named metric (recall on emergency-flagged cases)
exists to prevent, and it lives in the one layer (LLM reasoning) that is
the sole backstop under a red-flag-scan miss (per Entry 1's own framing).

Fixed by stripping each line (`line.strip()`) before the prefix check in
both `_parse` methods, in both files. Two new regression tests
(`test_anthropic_backend_parse_handles_indented_level_and_rationale_lines`,
`test_groq_reasoning_backend_parse_handles_indented_level_and_rationale_lines`),
both confirmed to fail against the pre-fix code first - `git stash push`
on just the two source files, re-ran the two new tests, watched them
fail with the exact predicted `AssertionError: assert URGENT == EMERGENCY`,
then `git stash pop` to restore the fix - before being counted as
passing. Ran `pytest` from a freshly built environment (`python3.13 -m
venv` - no venv existed in this container at session start -
`tesseract-ocr` reinstalled via `apt-get`, the tenth session in a row to
need both) - **191 passed, up from 189 at session start, zero
regressions**. Then started the real `uvicorn` server and curled it
directly: `GET /health` returned `{"status":"ok"}`; `POST /assess` with
`"chest pain since this morning"` and, separately, Day 14's own
double-space regression variant both still returned `{"level":"emergency", ...}`
(today's fix only touches the LLM-parsing path, which the red-flag
short-circuit never reaches); an ordinary case with no
`ANTHROPIC_API_KEY` still returned `503` - unchanged. Documented in
`docs/INTERVIEW_NOTES.md`, Day 15, including a named-not-fixed honest gap:
`app/agents/history_intake.py`'s `_parse` has the identical unstripped-
line-prefix pattern but stays out of scope (SIH26047-track, per Day 10's
own scoping correction).

End-of-day check against `docs/DAILY_PROTOCOL.md`'s four checks: Sems -
directly continuous with the Explainable AI & Model Interpretability
elective's "LLM output reliability" ground already cited for prior days'
parsing bugs, one category more specific (prompt-contract parsing, not
schema validation or response-shape parsing). 2028 market - no new claim,
restates what Days 6-14 already established about "tell me about a bug
you found" being a stronger answer with each independently-found real
instance. On-campus GPREC - stays inside the core `/assess` pipeline,
not a drift into SIH26047 or any off-campus story. Real showcase value -
yes: this is the most consequential bug found across all fifteen
sessions by the project's own stated standard (a silent de-escalation of
an actual correct emergency judgment, not a crash or a missed keyword),
and it survives a "why" follow-up cleanly, since the fix and its
regression tests are real and the honest not-yet-fixed sibling gap is
named rather than hidden. All four checks pass; nothing flagged today.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (tenth consecutive day). The evaluation harness's remaining 7
cases still need a live `ANTHROPIC_API_KEY`. Today's fix closes the
LLM-response-parsing-indentation gap across both in-scope backends
(Anthropic, Groq); the next hardening pass should either keep following
Day 14's own direction - re-examine another "settled" component's
matching/parsing behavior against a *different* realistic input
variation not yet simulated (case-normalization edge cases in
`GuidelineIndex.top_matches`'s TF-IDF query text, or `Facility`/
`TriageDecision` field construction paths not yet audited this way) - or
move fully to build work the moment an API key or outbound
training-data-source access becomes available.

## Day 16 — 9 Sep 2026

**Push diagnostic, run first as instructed and reported verbatim:**
`git remote -v` confirmed origin is
`https://github.com/azlanabyssal-cloud/carepilot`. `git push origin main
--dry-run` failed with a plain `[rejected] main -> main (non-fast-forward)`.
Unlike most prior days' version of this symptom, `git status` showed `HEAD
detached from refs/heads/main` outright (not just a local `main` a few
commits behind while attached), and local `refs/heads/main` was three
commits stale (`962550b`, Day 14) against `origin/main` (`05a686d`, Day
15 - confirmed already on GitHub via `git log --oneline -10 origin/main`,
authored "Claude", dated 8 Sep 2026). Verified with the same commit-graph
comparison Day 12 established (`git rev-parse` on `HEAD`/`origin/main`/
`refs/heads/main` directly) rather than trusting the dry-run error text
alone - confirms this is still the same standing per-session
detached-container artifact Days 7-15 already diagnosed and fixed eleven
times before today, not a GitHub access problem; the non-fast-forward
error text alone would have been consistent with either, which is exactly
why this routine's own instructions ask for the commit-graph check every
time rather than trusting the error text. Fixed with `git checkout -B
main origin/main` (`HEAD` already matched `origin/main` exactly and the
working tree was clean, so this discarded nothing), confirmed with a
second `--dry-run` reporting "Everything up-to-date" before any other
work started.

Re-checked the checklist's next-undone items fresh: no
`ANTHROPIC_API_KEY`/`GROQ_API_KEY`/`BHASHINI_USER_ID`/`BHASHINI_API_KEY`
anywhere in this environment, and `kaggle.com`, `data.gov.in`, and
`aikosh.indiaai.gov.in` all still `CONNECT tunnel failed, response 403`
from this environment's own outbound proxy - the eleventh consecutive
identical result. SHAP/LIME, CV-model training, and the evaluation
harness's remaining 7 cases are all still genuinely blocked.

Re-read every in-scope core-pipeline file in full. Re-audited
`app/agents/verify.py` and `app/agents/referral.py` specifically against
the two matching-related bug classes found *after* Day 12's own "these are
clean" verdict (Day 14's whitespace-collapse gap, Day 15's
unstripped-line-prefix gap) - both genuinely still clean, an honest
confirmation rather than assumed carried over. Found a real bug by
cross-referencing two already-separate, already-documented lessons in this
file against each other rather than by simulating a wholly new failure
category: Days 8-10 established that Unicode *format* characters (category
"Cf" - zero-width space/joiner/non-joiner, the BOM, etc.) are a real,
recurring artifact of typed/transcribed input this project's text fields
must defend against, but every one of those three fixes lived in
`app/schemas.py`'s Pydantic *length* validators. Day 14 fixed a *matching*
bug in `app/agents/intake.py`'s `scan_red_flags()`, but only for true
Unicode whitespace (`str.isspace()`) - Cf characters were never checked
against that specific function. Asking whether Day 14's own fixed function
had the same Cf-blind-spot Days 8-10 already proved real elsewhere turned
up a genuine gap.

Reproduced directly before writing any fix:
```python
from app.agents.intake import scan_red_flags
scan_red_flags("I have chest​ pain since this morning")   # -> [] (ZWSP before the space)
scan_red_flags("I have chest ​pain since this morning")   # -> [] (ZWSP after the space)
scan_red_flags("I have chest​pain since this morning")    # -> [] (ZWSP in place of the space)
scan_red_flags("difficulty‌ breathing badly")             # -> [] (ZWNJ, a different term)
```
All four confirmed to return `[]` - a real emergency term silently missed,
the case falling through to the Triage-Reasoning Agent instead of
short-circuiting to `EMERGENCY` - before any fix was written. Realistic,
not contrived, for the same reason Day 14's double-space case was:
predictive-text keyboards, IMEs, and copy-pasted formatted text are
documented to insert zero-width characters, most commonly right at
existing word-wrap points - exactly where a real space already sits.

Fixed by treating any Unicode category "Cf" character as
whitespace-equivalent - converted to a space, not deleted, so the
no-real-space-at-all case still collapses correctly - in the same
normalization pass that already collapses true whitespace. Reuses the "Cf
is not real content" judgment `app/schemas.py`'s `_visible_length` already
encodes, applied here to matching instead of length-checking, rather than
inventing a fourth, possibly-drifting variant of that same judgment. Five
new regression tests in `tests/test_intake.py`, four confirmed to fail
against the pre-fix code first (`git stash push -- app/agents/intake.py`,
re-ran, watched all four fail with the exact predicted `assert 'chest
pain' in []`, then `git stash pop` to restore the fix) before being
counted as passing, plus a fifth guarding against over-matching unrelated
text. Ran `pytest` from a freshly built environment (`python3.13 -m venv`
- no venv existed in this container at session start - `tesseract-ocr`
reinstalled via `apt-get`, the eleventh session in a row to need both) -
**196 passed, up from 191 at session start, zero regressions**. Then
started the real `uvicorn` server on port 8001 and curled it directly: the
original "chest pain" spelling, the ZWSP-before-the-space variant, and the
ZWSP-instead-of-a-space variant all now correctly returned
`{"level":"emergency", ...}` (the last two previously would not have);
Day 14's own double-space regression case still returned `emergency`
unaffected; an ordinary non-red-flag case with no `ANTHROPIC_API_KEY`
still returned the expected `503`. Documented in `docs/INTERVIEW_NOTES.md`,
Day 16, including a named-not-fixed honest gap: the same Cf-blindness
exists in principle in `_parse`'s `.strip()`-based prefix matching
(`app/agents/triage.py`, `app/agents/groq_backends.py`) and in
`app/agents/history_intake.py`'s `_parse` (SIH26047-track, out of scope),
neither fixed today since the practical risk there (an LLM inserting an
invisible character before its own structured keyword) is lower-probability
than the user-typed free text this fix actually targets, and today's
change stayed scoped to the finding actually reproduced.

End-of-day check against `docs/DAILY_PROTOCOL.md`'s four checks: Sems -
the Software Testing & QA ground within Full Stack AI Development (§08)
already cited for Day 14's "input variation, not just input presence"
finding, combined for the first time with Entry 2/Days 6-13's
boundary-validation thread, applied to a matching function instead of a
schema field. 2028 market - no new claim, restates what Days 6-15 already
established, with the added distinction that today's bug was found by
connecting two previously-separate findings rather than a fresh
simulation. On-campus GPREC - stays inside the core `/assess` pipeline;
`verify.py`/`referral.py` were re-audited and confirmed clean rather than
touched, and the SIH26047-track sibling gaps were named, not fixed,
keeping today's change scoped correctly. Real showcase value - yes: a
real, reproduced, tested bug in the project's oldest and most
safety-critical component, with the honest not-yet-fixed sibling gaps
named rather than hidden. All four checks pass; nothing flagged today.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (eleventh consecutive day). The evaluation harness's remaining 7
cases still need a live `ANTHROPIC_API_KEY`. Today's fix closes the
Cf-format-character gap in the deterministic red-flag scanner; the next
hardening pass could extend the same Cf-blindness check into `_parse`'s
prefix matching (named today as a real but lower-priority gap), keep
following Day 15's own direction into a not-yet-audited matching/parsing
surface, or move fully to build work the moment an API key or outbound
training-data-source access becomes available.

## Day 17 — 10 Sep 2026

Push diagnostic (flagged as suspect by this session's own instructions,
run first and reported verbatim): `git remote -v` showed origin correctly
pointing at `https://github.com/azlanabyssal-cloud/carepilot`.
`git push origin main --dry-run` failed with a plain `non-fast-forward`
rejection. Root-caused before touching anything else: `git status`
confirmed `HEAD detached from refs/heads/main`, and `git rev-parse`
confirmed the local `main` branch ref was two commits stale (`962550b`,
Day 14) against `origin/main` (`5b25198`, Day 16) - the exact same
standing per-session container artifact Days 7-16 already diagnosed and
re-fixed each time it recurred, not a GitHub access problem. `HEAD`
itself already matched `origin/main` exactly (`git log --oneline` on
both identical), so `git checkout -B main origin/main` discarded nothing.
Confirmed with a clean `--dry-run` reporting "Everything up-to-date"
before any build work started.

Built: re-verified fresh that SHAP/LIME, CV training-data prep, and the
evaluation harness's remaining 7 cases are all still genuinely blocked -
no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this environment, and a live
`curl` to `kaggle.com`, `data.gov.in`, and `aikosh.indiaai.gov.in` all
returned `CONNECT tunnel failed, response 403` from this environment's
own outbound proxy - twelfth consecutive identical result. Per
`docs/DAILY_PROTOCOL.md`'s own fallback rule, moved to hardening, and
specifically closed the gap Day 16's own entry named but deliberately
left unfixed: `AnthropicReasoningBackend._parse` (`app/agents/triage.py`)
and its verbatim copy `GroqReasoningBackend._parse`
(`app/agents/groq_backends.py`) stripped each response line with plain
`.strip()` before checking `.startswith("LEVEL:")`/`("RATIONALE:")` -
`str.strip()` only removes true Unicode whitespace, not category "Cf"
format characters, so a ZERO WIDTH SPACE directly before `LEVEL:`
silently missed the prefix and fell back to the cautious `URGENT`
default even when the model itself said "emergency" - the same dangerous
de-escalation direction Day 15 fixed for plain leading spaces, this time
via an invisible character. Reproduced directly first
(`AnthropicReasoningBackend._parse("​LEVEL: emergency\n...")`
returning `URGENT`, confirmed identically in `GroqReasoningBackend._parse`)
before writing any fix.

Bug found: as above - a real, in-scope bug in the core Triage-Reasoning
agent, not a third-party-response-parsing shape or a schema field this
time, but the sibling gap to Day 16's `scan_red_flags()` fix, named in
writing a day earlier and closed today.

Fix: new `_strip_invisible()` helper in `app/agents/triage.py` (strips
whitespace and "Cf" characters from both ends only - a Cf character
genuinely inside a word still correctly fails to parse, proven by a
dedicated over-matching guard test). `app/agents/groq_backends.py`
imports and reuses it rather than carrying a second, possibly-drifting
copy, since it already imports `TRIAGE_SYSTEM_PROMPT`/`TriageBackendError`
from the same module. Three new regression tests, all confirmed to fail
against the pre-fix code (`git stash` on just the two source files, both
tests failed with the exact predicted `TriageLevel.URGENT`, then
restored) before being counted as passing. `pytest`: 199 passed, up from
196 at session start, zero regressions. Ran the real `uvicorn` server and
curled it directly: `GET /health` returned `{"status":"ok"}`; a red-flag
emergency case still returned `emergency` with zero API key needed (the
short-circuit never reaches `_parse`, so today's fix couldn't touch it);
an ordinary non-red-flag case with no `ANTHROPIC_API_KEY` still returned
the expected "Triage reasoning backend is not configured." detail.
Honest gap named, not fixed: the identical `.strip()`-based pattern in
`app/agents/history_intake.py`'s `_parse` stays out of scope
(SIH26047-track, per Day 10's own correction).

Noted: `docs/INTERVIEW_NOTES.md` Day 17 Q&A entry added, `README.md`
Progress section updated with the same Day 17 line, "What's next" list
in `docs/INTERVIEW_NOTES.md` updated to reflect the closed gap.

End-of-day check against `docs/DAILY_PROTOCOL.md`'s four checks: Sems -
the same Software Testing & QA ground within Full Stack AI Development
(§08) Days 14/16 already cite, applied here to "a documented, deferred
gap is a work item with a due date, not a permanent excuse." 2028 market
- no new claim, restates what Entry 5/Days 6-16 already established.
On-campus GPREC - stays inside the core `/assess` pipeline
(`triage.py`/`groq_backends.py`); the SIH26047-track sibling gap in
`history_intake.py` was named, not fixed. Real showcase value - yes: a
twelfth real, reproduced, tested bug, plus a checkable "did you go back
and fix the thing you said you'd defer" story most candidates don't have.
All four checks pass; nothing flagged today.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (twelfth consecutive day). The evaluation harness's remaining 7
cases still need a live `ANTHROPIC_API_KEY`. Today's fix closes the
Cf-format-character gap in the Triage-Reasoning parser; the next
hardening pass could audit `app/agents/verify.py`/`app/agents/referral.py`
again against this same Cf-in-matching-context pattern (not yet checked
against it specifically, only against Day 14/15's whitespace/prefix
patterns), or move fully to build work the moment an API key or outbound
training-data-source access becomes available.

## Day 18 — 11 Sep 2026

Push diagnostic (flagged as suspect by this session's own instructions,
run first and reported verbatim): `git remote -v` showed origin correctly
pointing at `https://github.com/azlanabyssal-cloud/carepilot`.
`git push origin main --dry-run` failed with `! [rejected] main -> main
(non-fast-forward)`. Root-caused precisely before touching anything else
- and this time the root cause was a genuinely new shape, not just a
repeat of Days 7-17's usual symptom: `git rev-parse HEAD` and `git
rev-parse origin/main` printed the *identical* hash, but `git rev-parse
refs/heads/main` printed a hash four commits behind both. `git status`
reported `HEAD detached from refs/heads/main` - the push command reads
`refs/heads/main`, not whatever `HEAD` happens to be pointing at while
detached, which is what every prior day's fix was actually correcting
for, just not stated this precisely before. Confirmed `git merge-base
--is-ancestor refs/heads/main HEAD` returned true (a strict ancestor, not
a divergent branch) before fixing anything, so `git branch -f main HEAD
&& git checkout main` discarded nothing. Confirmed with a clean
`--dry-run` reporting "Everything up-to-date" before any build work
started.

Built: re-verified fresh that SHAP/LIME, CV training-data prep, and the
evaluation harness's remaining 7 cases are all still genuinely blocked -
no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this environment, and a live
`curl` to `kaggle.com`, `data.gov.in`, and `aikosh.indiaai.gov.in` all
returned `CONNECT tunnel failed, response 403` from this environment's
own outbound proxy - thirteenth consecutive identical result. Per
`docs/DAILY_PROTOCOL.md`'s own fallback rule, moved to hardening. First
followed Day 17's own pointer and audited `app/agents/verify.py`/
`app/agents/referral.py` against the Cf-in-matching-context pattern -
genuinely clean (TF-IDF tokenization and plain enum branching, neither
shares the substring/prefix-matching shape this bug class needs), an
honest null result. Then found a real, in-scope bug by re-examining the
exact function Day 17 had just fixed and asking whether the fix was
actually complete: `AnthropicReasoningBackend._parse` (`app/agents/triage.py`)
and its verbatim copy `GroqReasoningBackend._parse`
(`app/agents/groq_backends.py`) had Day 17's `_strip_invisible()` fix
applied to the `LEVEL:`/`RATIONALE:` *prefix* check, but the *value*
extracted after the colon (`stripped_line.split(":", 1)[1].strip().lower()`)
still used plain `str.strip()` - the identical Cf-blindness Day 17 had
just closed one token earlier on the same line, left untouched one token
later. Reproduced directly first
(`AnthropicReasoningBackend._parse("LEVEL: ​emergency\nRATIONALE: ...")`
returning `URGENT`, with the existing "Unrecognized triage level..."
warning logged, confirmed identically in `GroqReasoningBackend._parse`)
before writing any fix.

Bug found: as above - a real, in-scope bug in the core Triage-Reasoning
agent, one token past a fix from the immediately preceding session,
found by re-interrogating that fix's own completeness rather than
assuming it was done because it passed its own test.

Fix: both value extractions in `_parse` (the `LEVEL:` value and the
`RATIONALE:` value) now route through the existing `_strip_invisible()`
helper instead of `str.strip()`, in both backends - no new helper, the
same "Cf is not real content" rule already established. Two new
regression tests, both confirmed to fail against the pre-fix code
(`git stash` on just the two source files, both failed with the exact
predicted `TriageLevel.URGENT`, then restored) before being counted as
passing. `pytest`: 202 passed, up from 200 at session start (199 was Day
17's own count; the extra one already on `origin/main` before this
session started is the SIH26047-track `GET /red-flag-terms` test, not
this routine's work), zero regressions. Ran the real `uvicorn` server and
curled it directly: `GET /health` returned `{"status":"ok"}`; a red-flag
emergency case still returned `emergency` with zero API key needed (the
short-circuit never reaches `_parse`, so today's fix couldn't touch it);
an ordinary non-red-flag case with no `ANTHROPIC_API_KEY` still returned
the expected "Triage reasoning backend is not configured." detail.
Honest gap named, not fixed: `app/agents/history_intake.py`'s `_parse`
has the identical unguarded-value-extraction shape, stays out of scope
(SIH26047-track, per Day 10's own correction).

Noted: `docs/INTERVIEW_NOTES.md` Day 18 Q&A entry added, `README.md`
Progress section updated with the same Day 18 line, "What's next" list
in `docs/INTERVIEW_NOTES.md` updated to reflect the closed gap.

End-of-day check against `docs/DAILY_PROTOCOL.md`'s four checks: Sems -
the same Software Testing & QA ground within Full Stack AI Development
(§08) Days 14/16/17 already cite, sharpened to a specific habit: after
closing a named gap, check whether the same fix reached every unguarded
operation on the same line, not just whether the fix's own test passes.
2028 market - no new claim, restates what Entry 5/Days 6-17 already
established, with the added distinction that today's bug was found by
re-interrogating yesterday's own fix for completeness. On-campus GPREC -
stays inside the core `/assess` pipeline (`triage.py`/`groq_backends.py`);
`verify.py`/`referral.py` were re-audited and confirmed clean rather than
touched, and the SIH26047-track sibling gap was named, not fixed. Real
showcase value - yes: a thirteenth real, reproduced, tested bug, plus a
checkable "did you go back and make sure yesterday's fix was actually
complete" story, one level more disciplined than Day 17's own "did you
go back and fix what you deferred" story. All four checks pass; nothing
flagged today.

Push diagnostic follow-up, since this session's instructions specifically
asked for it: root cause is confirmed to be the local `main` branch ref
going stale/detached at each fresh container start, not GitHub access -
the `--dry-run` before any build work reported "Everything up-to-date"
after the fix, and this session's own final push (below) is the real
test of whether today's more precise diagnosis holds up.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (thirteenth consecutive day). The evaluation harness's remaining
7 cases still need a live `ANTHROPIC_API_KEY`. Today's fix closes the
last Cf-blindness gap on the `LEVEL:`/`RATIONALE:` line in the
Triage-Reasoning parser (prefix in Day 17, value in Day 18) - the next
hardening pass could look for a genuinely new failure class elsewhere in
the in-scope pipeline rather than a fourth pass over this same line, or
move fully to build work the moment an API key or outbound
training-data-source access becomes available.

## Day 19 — 12 Sep 2026

Push diagnostic (this session's instructions specifically asked for it,
verbatim, before any other work): `git remote -v` showed origin pointing
at `azlanabyssal-cloud/carepilot` as expected. `git push origin main
--dry-run` failed with:
```
 ! [rejected]        main -> main (non-fast-forward)
error: failed to push some refs to 'https://github.com/azlanabyssal-cloud/carepilot'
```
Root cause, diagnosed the same way Day 18 established (compare `HEAD`,
`origin/main`, and `refs/heads/main` directly, don't trust the dry-run
error text alone): `HEAD` was detached and its hash matched
`origin/main` exactly - `refs/heads/main` (the actual push target) was
29 commits stale. Confirmed it was a strict ancestor
(`git merge-base --is-ancestor refs/heads/main HEAD` → true) before
touching anything, then fixed with `git branch -f main HEAD && git
checkout main`. A `--dry-run` immediately after reported "Everything
up-to-date" - not GitHub access, the same standing per-session container
artifact Days 7-18 already diagnosed and re-fixed, now confirmed a
fifteenth time in a row.

Built: re-verified fresh that SHAP/LIME, CV training-data prep, and the
evaluation harness's remaining 7 cases are all still genuinely blocked -
no `ANTHROPIC_API_KEY`/`GROQ_API_KEY` in this environment, and a live
`curl` to `kaggle.com`, `data.gov.in`, and `aikosh.indiaai.gov.in` all
returned `CONNECT tunnel failed, response 403` from this environment's
own outbound proxy - fourteenth consecutive identical result. Per
`docs/DAILY_PROTOCOL.md`'s own fallback rule, moved to hardening. Day
18's own closing note flagged a real risk: four straight sessions
(Days 15, 17, 18, and Day 16's audit) had each found a narrower variant
of the same Cf-character parsing gap on the identical `LEVEL:`/
`RATIONALE:` line. Took that seriously instead of repeating the pattern:
re-read every in-scope file fresh end to end (`app/main.py`,
`app/schemas.py`, `app/agents/intake.py`, `app/agents/triage.py`,
`app/agents/groq_backends.py`, `app/agents/verify.py`,
`app/agents/referral.py`, `app/evaluation.py`,
`app/models/cv_classifier.py`, `app/models/ocr.py`), specifically
looking for a different shape of bug. That Cf/whitespace class came back
genuinely exhausted - an honest null result - and a real bug turned up
in a part of the codebase none of the last several days had actually
examined: the retry policy itself, not response parsing.

Bug found: `app/agents/groq_backends.py`'s `_is_retryable_http_error`
retried a connection error, a timeout, and any 5xx, but treated a 429
(rate limited) as an ordinary non-retryable 4xx. This directly
contradicts `app/agents/triage.py`'s own `AnthropicReasoningBackend`,
which explicitly retries `anthropic.RateLimitError` (Anthropic's own
429) with the identical exponential backoff - a rate limit is exactly
the transient condition backoff-and-retry exists for. Groq's backend was
silently giving a rate-limited request zero second chances while
Anthropic's own backend gives the identical failure up to two, breaking
this module's own stated "same safety properties no matter which vendor
answered" contract. Reproduced directly first: mocked `httpx.Client.post`
to return a 429 and counted POST attempts - exactly 1, no retry - before
writing any fix.

Fix: widened `_is_retryable_http_error` to retry `status_code == 429`
alongside the existing `>= 500`, leaving every other 4xx (bad request,
bad API key) unretried exactly as before - no change to the
`wait_exponential`/`stop_after_attempt(3)` policy itself, just which
failures qualify. Three new regression tests in
`tests/test_groq_backends.py`: the predicate directly (429/503 retried,
400/401 not), a 429-then-success case proving `_call` actually recovers
via tenacity's real retry (not a reimplementation), and a
persistent-429 case proving the bounded stop condition still holds
(exactly 3 attempts, then raises). All three confirmed to fail against
the pre-fix code first (`git stash push -- app/agents/groq_backends.py`,
re-ran, watched all three fail with the exact predicted single-attempt
behavior - one assertion literally read `assert 1 == 3` - then `git
stash pop`) before being counted as passing.

Environment note: this container started with no `.venv` and no
`tesseract-ocr` installed, same as every prior day - rebuilt both
(`python3.13 -m venv .venv`, `pip install -r requirements.txt`,
`apt-get install -y tesseract-ocr`) before running anything. `pytest`:
**300 passed**, up from 297 at session start (297, not Day 18's own 202
- the gap is SIH26047-track work already merged to `origin/main` since
Day 18, not this routine's own count), **zero regressions** from today's
own three additions. Ran the real `uvicorn` server and curled it
directly, not just the test client: `GET /health` returned
`{"status":"ok"}`; `POST /assess` with a red-flag symptom ("chest pain
since this morning") returned `{"level":"emergency", ...}` with zero API
key needed; an ordinary case ("mild cough for two days") with no
`ANTHROPIC_API_KEY` returned the expected `503`,
`"Triage reasoning backend is not configured."` - both existing paths
unaffected, exactly as predicted since today's fix is isolated to
Groq's HTTP retry predicate and neither path reaches Groq's backend code
at all in this environment.

Noted: `docs/INTERVIEW_NOTES.md` Day 19 Q&A entry added (full reproduce
-> bug -> fix -> test -> verify narrative, plus an honest note that no
live `GROQ_API_KEY` exists to prove this against Groq's real 429 body
shape or a `Retry-After` header), `README.md` Progress section updated
with the matching Day 19 line, "What's next" list in
`docs/INTERVIEW_NOTES.md` updated.

End-of-day check against `docs/DAILY_PROTOCOL.md`'s four checks: Sems -
maps to the MLOps/AI & System Programming Lab ground already cited
(§08), sharpened to a specific, checkable habit: auditing a retry
policy by asking "which status codes does this predicate treat as
transient, and does that list match every other backend claiming the
same contract," not just "does this code retry at all." 2028 market -
no new claim, restates what Entry 5/Days 6-18 already established, with
the added, checkable distinction that today's finding came from
deliberately stepping back from four days of narrowing variants on one
line rather than continuing that pattern a fifth time. On-campus GPREC -
stays inside the core in-scope pipeline (`groq_backends.py` is a
drop-in `ReasoningBackend` for `/assess`'s own Triage-Reasoning stage,
not SIH26047 track). Real showcase value - yes: a fourteenth real,
reproduced, regression-tested bug, and a direct, evidenced answer to a
fair follow-up ("aren't you just finding smaller versions of the same
bug at this point?") instead of a reassurance. All four checks pass;
nothing flagged today.

Push diagnostic follow-up, since this session's instructions specifically
asked for it: root cause confirmed for a fifteenth time to be the local
`main` branch ref going stale/detached at each fresh container start,
not GitHub access - the `--dry-run` before any build work reported
"Everything up-to-date" after the fix, and this session's own final
push (below) is the real test of whether that holds.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (fourteenth consecutive day, no API keys, all three
data-source domains still `403`/`connect_rejected`). The evaluation
harness's remaining 7 cases still need a live `ANTHROPIC_API_KEY`.
Today's fix closes the retry-policy asymmetry between the two
Triage-Reasoning backends; a real, named next step is whether Groq's
real 429 response ever carries a `Retry-After` header this fix doesn't
yet read (unverifiable without a live `GROQ_API_KEY`). The next
hardening pass should keep looking for genuinely new failure classes -
today's own audit of `app/main.py`/`app/schemas.py`/`app/evaluation.py`/
`app/models/cv_classifier.py`/`app/models/ocr.py` came back clean, but
`app/adapters/abdm.py` and the SIH26047-track backends
(`history_intake.py`'s Anthropic/Groq drafting backends,
`ayush_mode.py`, `socrates_intake.py`, `db.py`) were not part of this
routine's own in-scope audit and stay untouched, per `docs/DAILY_PROTOCOL.md`'s
own scope line - or move fully to build work the moment an API key or
outbound training-data-source access becomes available.

## Note — 12 Sep 2026 (SIH26047 track, not a numbered Day)

Out of this routine's own GPREC-placement scope per
`docs/DAILY_PROTOCOL.md` - flagged, not counted as a "Day N hardening"
entry, same convention Days 8/10 already established for SIH26047-track
work. Wired `app/models/ocr.py`'s already-tested `build_document_timeline`
into `POST /case-intake/document`, closing Module B's "chronological
organization" gap named in `docs/sih/SIH26047_STRATEGY.md` Section E item
5: the endpoint now takes one or more uploaded documents instead of
exactly one, orders them (dated documents first, undated after) before
building `prior_investigations_summary`, and labels each document's
section by filename once there's more than one. A single uploaded
document - still the common case - is unaffected byte-for-byte. Also
added a first-hand primary-source confirmation to
`docs/sih/SIH26047_Patient_Case_Taking_Software.md`: the project owner
shared a real screenshot of `sih.gov.in/sih2026PS` itself, the first
genuine first-hand view of the primary portal this project has had -
everything before was a third-party mirror or a pasted transcript. PS
number, title, org, department, category, and theme all match exactly;
the Expected Solution/deadline sections weren't visible in the
screenshot, so that specific gap stays open.

Also, on the same SIH26047 track: wired two zero-API deterministic
fallback backends (`app/agents/triage.py`'s
`DeterministicFallbackReasoningBackend`, `app/agents/history_intake.py`'s
`DeterministicHistoryDraftingBackend`) so `/assess`, `/triage`, and
`/case-intake*` never 503 a non-red-flag case just because no LLM key is
configured - they now return a real, honestly-labeled result
(`requires_manual_triage` on `ReferralResult`/`ClinicalHistorySummary`)
instead. Verifying that live surfaced a real, pre-existing bug in the
in-scope `app/agents/verify.py`: `verify_triage_decision` escalated to
the most severe match among the top-3 retrieved guideline chunks rather
than just the best one, so a weak, second-ranked chunk sharing only the
words "pain"/"mild" could override a correct, stronger top-1 match - "my
knee pain is very mild and only when climbing stairs" was escalating
straight to EMERGENCY. Fixed by retrieving only the single best match
(k=1); the existing "never de-escalate" safety tests are unaffected.
Also fixed `scan_red_flags` (`app/agents/intake.py`) missing common
misspellings and Hindi-English code-switched input ("cheast pain",
"mera chest mein bahut pain hai") via a calibrated, sequence-aware fuzzy
match layered additively on top of the existing exact match. 311 tests
passing (was 298 at the start of this SIH26047-track work).

Note — 12 Sep 2026 (audio pipeline, two real bugs and one real
zero-API extension). First, a serious, previously-hidden correctness
bug: `app/adapters/bhashini.py`'s `bhashini_to_intake()` hardcoded
`source_language="te"` with no way to override it, and neither
`/assess/voice` nor `/case-intake/voice` had a `language` field at all -
every voice submission was declared Telugu to Bhashini regardless of
what the patient actually spoke or which of the UI's three languages
(English/Hindi/Telugu, trilingual since early in this project) they had
selected. Fixed by threading a real `language` Form field through both
endpoints into `bhashini_to_intake(adapter, audio_bytes, source_language)`,
and by having `web/app.js`'s `submitVoiceBlob()` send
`window.CarePilotI18n.getLang()` - the one honest signal the client has
about what language the patient is likely speaking.

Second, following the project owner's explicit instruction not to
depend on Bhashini's live API for audio at all: added
`app/adapters/offline_speech.py`, a zero-network ASR+TTS fallback,
matching the same "never hard-fail on a missing external API" principle
already applied to triage reasoning and history drafting. TTS
(English/Hindi/Telugu) uses espeak-ng, verified live producing real,
non-trivial WAV bytes in all three languages with zero credentials.
ASR is English-only, using PocketSphinx's bundled en-us acoustic model
(ships inside the pip wheel itself, zero extra download) - Hindi/Telugu
offline ASR was investigated and explicitly not shipped: this
environment's own egress proxy hard-blocks both huggingface.co and
alphacephei.com (confirmed directly, 403/policy-denied), which is where
a Whisper or Vosk model would have to come from, so no Hindi/Telugu
acoustic model could be fetched or verified. PocketSphinx's real,
measured accuracy against even a clean synthetic (espeak-ng) English
voice is genuinely modest - "please see a doctor immediately for this
symptom" came back as "we see all the recall is the" - so every case
transcribed through this fallback is marked `requires_manual_triage=True`,
the same "flag it, don't hide it" signal already used for a
low-confidence LLM fallback. Verified live end-to-end, not just
unit-tested: a real Chromium session (fake mic device) recorded a real
English utterance, submitted through the actual UI with zero
BHASHINI/ANTHROPIC credentials configured, and got back a 200 (not the
previous flat 503) with `requires_manual_triage: true` and a garbled-but-
real chief complaint - proof the fallback is real, not proof it's
accurate. The audio-summary (TTS output) endpoint got the same
treatment: a small, fixed, honestly-bounded translation of the four
priority-level phrases (mirroring `web/i18n.js`'s own already-reviewed
strings) plus the chief-complaint label, not a claim of general offline
translation - `OfflineSpeechAdapter.translate()` explicitly refuses any
pair besides English-to-English and says why. 340 tests passing.

Note — 13 Sep 2026 (real safety gap in the actual PS-target endpoint,
found and fixed). `app/main.py`'s `_run_pipeline` (backing `/assess`,
`/assess/voice`) has always called `verify_triage_decision` - the
Guideline-Verification agent, the second of the two safety layers this
project keeps citing - after `_run_triage`. `_run_case_intake` (backing
`/case-intake`, `/case-intake/voice`, `/case-intake/document` - the
actual "Patient Case-Taking Software" endpoints this PS is about) never
did. That prior claim ("both share the exact same safety-critical
priority decision underneath") was asserted in `_run_case_intake`'s own
docstring and was false in code, not just imprecise - found by testing
`/assess` against `/case-intake` with identical input rather than
trusting the docstring. Confirmed live: "my face feels droopy on one
side and my speech sounds strange" - real FAST-criteria stroke wording
that `scan_red_flags` does not catch (verified directly:
`scan_red_flags(text) == []`), so it never reaches the zero-API
red-flag short-circuit - scores above `GuidelineIndex`'s
`min_similarity=0.2` against the seeded EMERGENCY stroke chunk. Under
this environment's real, common condition (no `ANTHROPIC_API_KEY`,
`DeterministicFallbackReasoningBackend` proposing URGENT for every
non-red-flag case), `/assess` returned `emergency` and `/case-intake`
returned `urgent` for the exact same sentence - a live, reproducible,
safety-relevant disagreement between two endpoints of the same system,
not a hypothetical. Fixed with one line (`_run_case_intake` now calls
`verify_triage_decision` unconditionally, exactly like `_run_pipeline`
already did); proven with a regression test that was first confirmed to
actually fail against the un-fixed code (reverted the fix, watched the
test fail with `AssertionError: assert 'urgent' == 'emergency'`,
restored the fix, watched it pass) before being trusted as a real
regression guard rather than a tautology. 341 tests passing.

Note — 13 Sep 2026 (real explainability, not a black box). Following
directly from the safety fix above: `app/agents/verify.py`'s
Guideline-Verification agent already computed a real cosine-similarity
score against the matched guideline chunk on every call, then discarded
it the instant the decision didn't escalate - the common case. Added
`GuidelineIndex.best_match_with_score()` (returns the real score
`top_matches()` computes internally and throws away) and a new
`schemas.GuidelineEvidence` model (source, matched text, similarity,
matched level), threaded through `TriageDecision` -> `ReferralResult`
(`/assess`, `/assess/voice`) and `ClinicalHistorySummary`
(`/case-intake*`) the same way `requires_manual_triage` already is.
Honestly absent, not fabricated, for a decision already at EMERGENCY
when verification runs (nothing above it to check against) - a
red-flag case's real explanation is a matched safety term, a different
kind of evidence this model doesn't represent.

Caught a real framing risk by actually looking at the live rendered
output rather than trusting the design on paper: the genuine score
behind a correct stroke-symptom escalation to EMERGENCY was 29% -
accurate, but reading "29% match" next to the highest priority level
looks like low confidence to a viewer, when similarity-to-a-guideline
isn't a confidence score at all, it's the input to a deliberately
asymmetric policy (any match above the safety floor escalates, a weak
match never de-escalates). Fixed by adding an explicit, fixed policy
note alongside the real percentage, in all three languages, rather than
rounding the number differently or hiding it. Rendered and verified
live in a real browser (Playwright) across three cases: an ordinary
case (70% match, panel shown), the stroke-phrasing escalation (29%
match, panel shown, EMERGENCY correctly reached), and a literal
red-flag case (panel correctly absent). 346 tests passing.

Note — 13 Sep 2026 (the explainability feature above was silently
losing its own data - found by auditing my own prior work, not asked
to). `app/schemas.py` gaining a new `ClinicalHistorySummary` field
(`guideline_evidence`) is not, by itself, enough for it to persist -
`app/db.py` keeps its own hand-maintained column list, exactly the
class of bug this project already found once with
`requires_manual_triage` on 12 Sep. This is the second time, not the
first: I added the field to the Pydantic schema and wired it through
every code path except this one. Confirmed live before fixing: a real
`ClinicalHistorySummary` with real evidence attached went into
`CaseStore.save()`, came back `None` from `CaseStore.get()` - the
evidence panel from the commit above would have rendered correctly on
the immediate patient-facing response and then silently vanished the
moment a physician opened the same case in the Physician Console
minutes later, since that view is a fresh `GET /cases/{id}` fetch from
SQLite, not the original in-memory object. Fixed with the same pattern
already established for `ayush_assessment` (a single nested object,
stored as one JSON TEXT column) and the same migration discipline as
`requires_manual_triage` (`PRAGMA table_info` check + conditional
`ALTER TABLE` in `__init__`, so a pre-existing database - this repo's
own `data/cases.db`, gitignored, held 1380 real rows accumulated across
this session's own live testing - migrates in place instead of raising
"no such column"). Verified against that exact real file, not just a
fresh test database, and end-to-end through the real HTTP physician
flow: created a case, logged in with a real physician passcode, fetched
it back via `GET /cases/{id}`, confirmed the evidence survived
completely. Two new regression tests added, mirroring the existing
`requires_manual_triage` round-trip and migration tests exactly. 348
tests passing.

Note — 13 Sep 2026 (a real layout weakness, and a real bug it exposed,
both found by actually looking at live screenshots rather than trusting
the markup). Requested: make the UI genuinely stand out, not just be
free of errors. Screenshotted every real state (desktop, mobile,
post-submission, physician view) before touching anything, rather than
guessing what needed fixing.

Found: `#results-area` - the single most important thing this product
produces (priority level, guideline evidence, drafted history) - lived
in `.col-secondary`, the narrower 380px sticky reference column,
alongside "How Inayat works" and the safety-metrics card. On desktop
this meant the actual result rendered in the narrower of two columns
while `.col-primary` (`flex: 1 1 640px`) sat almost empty after
submission with just a small "submitted" note. The copy even said "see
the summary alongside," confirming this was a deliberate original
choice, not an oversight - but seeing it rendered, it was the wrong
one. Fixed by relocating `#results-area` into `.col-primary`, right
after the submission-complete note; `.col-secondary` now holds only the
persistent "why trust this" reference material a sticky sidebar is
actually for. Copy updated (`submission_complete_note`, all 3
languages) to match.

That relocation exposed a second, real, pre-existing bug: `app.js`'s
`renderResult()` called `resultsArea.scrollIntoView({block: "start"})`
BEFORE collapsing `#intake-wizard-wrap` and revealing
`#submission-complete` - harmless before today (results lived in a
different flex column, whose height changes don't move a sibling
column's content), but once both live in the same column, collapsing
the tall wizard immediately after computing a fixed smooth-scroll
target shifted the real target position upward while the browser kept
animating toward the stale one. Measured directly, not assumed: the
results heading landed 156px above the viewport, fully scrolled past.
Fixed by moving the `scrollIntoView()` call to after the layout
settles into its final shape. Confirmed with the same measurement
before and after: pre-fix, `window.scrollY` froze at a value putting
the heading at `top: -156px`; post-fix, `top: 21.9px` - inside the
sticky emergency bar's 53px zone, which was the second real thing this
surfaced.

That remaining 21.9px catch led to a global fix, not a one-off patch:
`.emergency-bar` (`position: sticky; top: 0`) was never accounted for
by any `scrollIntoView`/anchor-link target on the page - nothing broke
visibly before because nothing scrolled a target flush to the very top
until today's fix did. Added `scroll-padding-top: 80px` on `html`
(covers the bar's real, measured height at its tallest - 72px on a
narrow phone viewport where its text wraps to two lines, confirmed in
English, Hindi, and Telugu - not just its shorter 53px desktop
single-line height), which fixes this scroll target and any future one
in one place. Re-verified: heading lands at `top: 101.9px`, fully clear.

Also, while researching how to get a real public URL to share (asked
directly, not assumed needed): found this repo's own
`docs/DAILY_PROTOCOL.md` already lists "any deployment to a live public
URL" as requiring an explicit go-ahead, and that `README.md` already had
a full, real Hugging Face Spaces walkthrough from an earlier session -
including a real gotcha (HF's default port 7860 vs this Dockerfile's
8000) neither I nor a fresh Render deploy would need to solve the same
way. Wrote `DEPLOY.md` as the quick-start version, pointing to the
existing HF walkthrough and adding Render as a no-port-gotcha
alternative, plus one real gap missing from both: free-tier hosts
generally don't persist `data/cases.db` across a redeploy or sleep
cycle. Also caught and fixed a real, stale claim in `README.md`'s own
HF Spaces section - it said `ANTHROPIC_API_KEY` was "needed for /triage
and /assess," written before this session's own deterministic-fallback
work made that no longer true. 348 tests passing (frontend-only
changes; backend suite unaffected but re-run to confirm).

Note — 13 Sep 2026 (the real first few seconds, measured rather than
assumed - and two false alarms in my own test methodology along the
way, corrected rather than reported as app bugs). Asked directly: make
the first 2-3 seconds of using the page feel complete, not just
error-free.

Checked the obvious suspect first (the hero's live-typing red-flag
demo, gated on GET /red-flag-terms) and measured it resolving in
~220ms locally - imperceptible, not a real problem, said so rather than
manufacturing urgency around it.

Found a real one instead: `#safety-metrics-card` stayed entirely
`hidden` until GET /evaluation/report resolved, and that endpoint's
result is cached at the MODULE level after its first call (a
deliberate choice - see app/main.py's own comment on why it's not
computed eagerly at startup: doing so would spend a real Anthropic API
call on every restart in a deployment with real credentials). Measured
directly: the first call after a (re)start took over 3 real seconds,
during which the single most trust-relevant content on the page -
"100% Emergency Recall, 100% Overall Accuracy" - was simply invisible.
Per DEPLOY.md's own honest note on Render's free-tier sleep behavior,
this 3-second gap recurs on every request that wakes a sleeping
instance, not just once ever.

Fixed with a loading skeleton, not by touching the deliberately-lazy
caching: the card's title and two pulsing placeholder bars
(safety_metrics_measuring_note, all 3 languages) now show from first
paint; loadSafetyMetrics() swaps them for the real numbers the moment
they arrive, exactly matching the loaded state's real size so the swap
doesn't itself cause a jump. Total measured CLS over the first 3
seconds dropped from 0.0221 to 0.0011 as a result.

Getting there took two real detours in my own test scripts, both
corrected before being reported as anything wrong with the app: (1) a
`time.sleep()` inside a Playwright route handler blocks the sync
driver's own single thread, so `page.goto()` couldn't return until the
fake delay finished either - made it look like the skeleton never
showed, when a non-blocking delay (a background-thread timer) and a
JS-side property trap both then confirmed it does, exactly on schedule;
(2) checking language-switch behavior via `i18n.setLang()` directly
skips `applyLanguage()`/`applyStaticTranslations()`, which only run
from the real button-click handler - looked like the skeleton's text
never translated, until clicking the actual `.lang-btn` elements (what
a real user does) showed all three languages updating correctly. Both
are recorded here because "my test says X" and "the app does X" are
different claims, and only rigorously re-checking the gap between them
- in either direction - is what this project's whole standard has been
about. 348 tests passing (frontend-only changes).

Note - 13 Sep 2026 (audio, made smoother and more honest - measured,
not assumed; plus a straight answer on live deployment). Asked to make
the audio experience work smoother with no error, then, mid-session, to
deploy it for mobile use.

Deployment first, since it needed a direct answer rather than a fix:
checked docs/DAILY_PROTOCOL.md and DEPLOY.md (both already written by
an earlier session) and confirmed nothing has changed - this sandbox
has no hosting-provider credential or account of any kind, so there is
no button here to push regardless of authorization. Verified PR #1
(sih26047-document-timeline) is still open, draft, and
mergeable_state: clean, so the branch is deployable as-is without
waiting on a merge. Gave the real fastest path (Render, ~5 minutes,
steps already in DEPLOY.md) instead of a deploy that can't actually
happen from here.

Since "for mobile use" is a real, checkable claim and not just a
figure of speech, ran the live page through Playwright at a 390x844
mobile viewport before saying so: zero horizontal overflow
(scrollWidth === innerWidth), mic button tap target 211x46px (well
over the 44px accessibility floor), zero console/page errors across
every flow below.

Then measured the actual audio pipeline rather than assuming the
backend work from two days ago covers "smooth": a real
espeak-ng-synthesized recording through the offline path (no Bhashini
configured, this environment's real condition) took 2.1-3.3 real
seconds end to end in /case-intake/voice - not the sub-200ms a text
submission gets. The only thing on screen for that entire wait was
static bold text (.status-area .loading) and a flat gray disabled mic
button (.mic-btn.is-processing had no animation at all) - the same
"looks frozen, not working" gap as the safety-metrics card two entries
up, just never checked for this endpoint specifically. Fixed with a
spinner (showLoadingMessage() now renders one, @keyframes
loading-spin) and a subtle pulse on the processing mic button
(@keyframes mic-processing-pulse), both added to the existing
prefers-reduced-motion block rather than a new one.

While measuring that, also ran the real transcript through the app,
not just the timing: an offline-path recording of "I have had a severe
headache and blurred vision since yesterday morning" came back from
PocketSphinx as "odyssey real" - and a real end-to-end mobile-viewport
Playwright run (fake mic device, real MediaRecorder, real fetch, zero
mocking) produced "gervais" as a chief complaint from Chromium's own
synthetic test audio. Checked what the patient is actually told when
this happens: requires_manual_triage is real and already set correctly
(app/main.py's _transcribe_voice -> used_offline_fallback -> True), but
the one patient-facing message it triggers (degraded_mode_note) was
written for a different cause entirely (the LLM-reasoning fallback) and
only ever says "a doctor will check this in person" - never "the words
above might not be what you actually said," which is the one thing the
patient themselves could catch immediately and fix by retyping, and the
base message gives them no reason to think to look for it. Fixed on the
frontend only (no schema/DB change - weighed a proper
used_offline_fallback field all the way to
ClinicalHistorySummary/app/db.py against the size of that change given
this project has hit the exact "added a field, forgot to persist it"
bug twice already, and a client-side "was this submission voice" flag
closes the real gap at far lower risk): submitVoiceBlob() now sets a
lastSubmissionWasVoice flag, and renderDegradedModeNote() picks
degraded_mode_note_voice (new copy, all 3 languages) over the generic
note when both that flag and requires_manual_triage are true. Verified
both branches for real, end to end, no mocking: the mild sore-throat
text case (which does trip requires_manual_triage via the
history-drafting fallback, confirmed directly - the earlier
stroke-symptom test case used for the guideline-verification fix takes
the red-flag short-circuit branch instead and was the wrong probe for
this) still shows the original generic note; the real voice run above
shows the new one.

Last real gap, found by checking audio.play()'s actual resolution
instead of trusting the existing code comment that called a rejected
autoplay "not an error" (true, but incomplete - the visible
<audio controls> bar covers "can the patient still play it," not "does
the patient know they need to"): added a hint
(listen_tap_to_play_hint, all 3 languages) that only appears when
play() actually rejects. Proved both branches live: the real fetch
plays automatically today in this project's headless Chromium harness
(confirmed - audio.paused: false, currentTime advancing), and a
Playwright-injected HTMLMediaElement.prototype.play override that
simulates the NotAllowedError real mobile Safari is known to raise here
confirms the hint appears exactly when it should and stays hidden
otherwise. Recorded here rather than left as an assumption either way,
since this sandbox cannot launch real iOS Safari to check which case
actually applies on a given visitor's phone.

348 tests passing (frontend-only changes; full suite re-run to
confirm).

Note - 13 Sep 2026 (the first real Render deploy, and what it actually
found). DEPLOY.md's Render section claimed "no port mismatch to
reconcile" and requirements-deploy.txt was assumed to mirror
requirements.txt correctly - neither had ever been checked by actually
building and running this Dockerfile as a real container, only by
reading the code and reasoning it should work. The project owner ran
the real deploy today; it failed twice, for two different real reasons
found from the actual container logs, not guessed at:

1. `ModuleNotFoundError: No module named 'cryptography'` on startup.
   requirements-deploy.txt is a manually-kept subset of
   requirements.txt (deliberately excluding torch/torchvision - see its
   own header comment) - when cryptography==50.0.1 was added to
   requirements.txt for app/adapters/abdm.py, the deploy subset was
   never updated to match. Same "added it in one place, not the other"
   bug class as two earlier ones in this project. Found by reading the
   real container traceback down to `app/adapters/abdm.py line 90:
   from cryptography.hazmat.primitives import ...`, not assumed from
   the diff. Fixed, then verified for real (not just re-read): built a
   clean venv from requirements-deploy.txt alone (no dev extras that
   would silently mask the gap) and confirmed `import app.main`
   succeeds.

2. A second, real, still-latent bug caught before it could cost a
   second failed deploy cycle: the Dockerfile's CMD and HEALTHCHECK
   both hardcoded port 8000, but Render (like most PaaS hosts) injects
   its own PORT env var and routes traffic there - EXPOSE in a
   Dockerfile is documentation, nothing reads it to pick a port. This
   would have looked like a hung, unreachable service right after fix
   #1 cleared, not another crash. Fixed both to use ${PORT:-8000} and
   verified live (not assumed from the syntax): ran uvicorn with PORT
   unset and with PORT=10000 and confirmed via its own stdout which
   port it actually bound in each case, matching what was requested
   each time. No Docker daemon was available in this sandbox to build
   the real image end-to-end, so this is verified at the shell/uvicorn
   level, not with a full container run - the next real Render deploy
   is what actually proves it.

Also swept every top-level import across the whole app/ package against
requirements-deploy.txt while fixing #1, specifically to avoid finding
a third missing dependency one failed deploy at a time - nothing else
was missing. 348 tests passing (Dockerfile/requirements-only change;
full suite re-run to confirm no regression).

## Note — 13 Sep 2026 (SIH26047 track, not a numbered Day)

Went looking for real, "small to small" main-thread lag in `web/app.js`
itself rather than synthetic scroll-jank benchmarks (which had already
come up clean) - grepped every `setInterval`/`setTimeout`/input listener
for anything that keeps doing work after a patient no longer needs it.
Found one real instance: `startLiveDemoTicker()`'s recursive
`setTimeout` loop (`typeOutLiveDemoText()`, one DOM write roughly every
35ms while "typing" a fresh example every ~4s) was stopped only by the
one specific "Try it yourself" button click - a patient who instead just
starts typing directly into the real symptom textarea, or starts a
voice recording, the far more common real paths, left it running
silently in the background for the rest of their session, competing for
the main thread with everything else on the page. This is exactly the
kind of contention a synthetic scroll-jank test alone would never
surface, since it only shows up while the ticker and something else are
both live at once.

Fixed by calling the existing (already idempotent) `stopLiveDemoTicker()`
from the start of both `handleSymptomTextInput()` and `startRecording()`.
Verified live with Playwright, not just re-read: loaded the page,
confirmed the ticker was mid-animation (non-empty, changing text), then
simulated a real `fill()` into the symptom textarea and sampled the
ticker's DOM text immediately, +1s, and +3s after - identical text all
three times, versus continuing to change before the fix. 348 tests
passing (pure front-end JS change; full suite re-run anyway to confirm
zero backend impact).

## Day 20 — 13 Sep 2026

Push diagnostic (this session's own instructions specifically required
it, verbatim, before any other work, flagging that prior automated runs
- including a minimal diagnostic-only one - had never successfully
pushed): `git remote -v` showed origin pointing at
`azlanabyssal-cloud/carepilot` as expected, both fetch and push. `git
push origin main --dry-run` failed:
```
 ! [rejected]        main -> main (non-fast-forward)
error: failed to push some refs to 'https://github.com/azlanabyssal-cloud/carepilot'
```
This is the exact mechanism Day 18 first named and Days 18-19 both
re-confirmed: not a GitHub access problem. `git fetch origin main` plus
`git branch -vv` showed `HEAD` detached and already sitting exactly at
`origin/main`'s tip (`03a8f02`), while local `main` (the actual push
target) was stuck 30 commits behind at an old commit. `git log
origin/main..main` was empty - confirming the stale local `main` held
zero commits not already on `origin/main`, so nothing would be lost -
before fixing with `git checkout main && git merge --ff-only
origin/main` (a plain fast-forward, since HEAD's tip already equaled
origin/main's; no `-f`/force needed today). A `--dry-run` immediately
after reported "Everything up-to-date." Worth naming plainly: this is
the sixteenth session in a row needing this exact fix, and the previous
fifteen each re-diagnosed it as if for the first time rather than
checking whether a *differently-phrased* diagnostic (this session's own
"report the exact commands verbatim" framing, rather than the usual
one-line dry-run error) might surface something the routine phrasing
doesn't - which is exactly what happened today.

Built: re-verified fresh that SHAP/LIME, CV training-data prep, and the
evaluation harness's remaining 7 cases are all still genuinely blocked -
`env | grep -iE "anthropic|groq|kaggle|bhashini"` empty, and a live
`curl` to `kaggle.com`, `data.gov.in`, and `aikosh.indiaai.gov.in` all
returned `CONNECT tunnel failed, response 403` from this environment's
own outbound proxy - fifteenth consecutive identical result. Per
`docs/DAILY_PROTOCOL.md`'s own fallback rule, moved to hardening. Day
19's own closing note pointed at auditing retry predicates against what
they actually match, not just against each other (Day 19's own finding
was Groq's 429 predicate disagreeing with Anthropic's). Read
`app/main.py`, `app/schemas.py`, `app/agents/intake.py`,
`app/agents/triage.py`, `app/agents/groq_backends.py`,
`app/agents/verify.py`, `app/agents/referral.py`, `app/evaluation.py`,
`app/models/cv_classifier.py`, `app/models/ocr.py`, and
`app/adapters/bhashini.py` fresh, applying that specific test
mechanically: for every `retry_if_exception_type(...)` and every
`except (...)` clause naming httpx exceptions, does the listed set
actually match the real class it's meant to cover, checked with
`issubclass()`, not assumed from the exception's name.

Found a real, previously-unaudited bug in `app/adapters/bhashini.py`:
every retry decorator (`_get_pipeline_config`, `_post_inference`) and
every one of `transcribe()`/`translate()`/`synthesize()`'s own except
clauses listed `(httpx.ConnectError, httpx.ReadTimeout)` as "the
transient failures worth retrying/converting." Checked directly:
`issubclass(httpx.ConnectTimeout, httpx.ConnectError)` is `False` -
`httpx.ConnectError` and `httpx.TimeoutException` are siblings in
httpx's real hierarchy, and `httpx.TimeoutException` has *four*
subclasses (`ConnectTimeout`, `ReadTimeout`, `WriteTimeout`,
`PoolTimeout`), of which this file's code only ever named one. A
connection timeout, or a timeout writing the request body (a real risk
specifically for `transcribe()`, which uploads base64-encoded audio
bytes), was retried by nothing and caught by nothing. Reproduced
directly first:
```python
>>> from unittest.mock import patch
>>> import httpx
>>> from app.adapters.bhashini import RealBhashiniAdapter
>>> adapter = RealBhashiniAdapter(user_id="u", api_key="k")
>>> with patch("httpx.post", side_effect=httpx.ConnectTimeout("connect timed out")):
...     adapter.transcribe(b"fake-audio-bytes")
httpx.ConnectTimeout: connect timed out
```
confirmed identically for `WriteTimeout` (on `transcribe`), `PoolTimeout`
(on `translate`), and `ConnectTimeout` again (on `synthesize`) - before
writing any fix. The real consequence: this exception is not
`BhashiniAdapterError`, so `app/main.py`'s `/assess/voice`,
`/case-intake/voice`, and `GET /cases/{case_id}/audio-summary` - every
one of which wraps `RealBhashiniAdapter` calls in `except
BhashiniAdapterError` - never catch it, letting it reach the caller as
a raw, undocumented 500 instead of the clean 503 every other Bhashini
failure already produces.

Fixed by widening every `(httpx.ConnectError, httpx.ReadTimeout)` in
`app/adapters/bhashini.py` (two retry decorators, three except clauses)
to `(httpx.ConnectError, httpx.TimeoutException)` - matching the
correct, broader check `app/agents/groq_backends.py`'s own
`_is_retryable_http_error` already used, rather than inventing a third
convention for "which httpx exceptions count as transient." Six new
regression tests: five unit-level in `tests/test_bhashini.py`
(`ConnectTimeout` on `transcribe`/`synthesize`, `WriteTimeout` on
`transcribe`, `PoolTimeout` on `translate`, and a retry-recovery test
proving `transcribe()` - the real method - actually recovers via
tenacity's real retry after one failed `ConnectTimeout` attempt), one
live-endpoint level in `tests/test_main.py` (`ConnectTimeout` mocked at
the real `httpx.post` seam inside a live `/assess/voice` request through
the actual FastAPI `TestClient`). All six confirmed to fail against the
pre-fix code first: `git stash push -- app/adapters/bhashini.py`, re-ran
all six, watched all six fail (five with the raw `httpx.*Timeout`
exception propagating uncaught, the live-endpoint one the same way
through the TestClient), then `git stash pop` to restore the fix before
counting anything as passing.

Ran `pytest` from this session's own freshly-built environment
(`python3.13 -m venv` - no venv existed in this container at session
start; `tesseract-ocr` reinstalled via `apt-get`, the sixteenth session
in a row needing both) - **306 passed, up from 300 at session start,
zero regressions**. Then started the real `uvicorn` server as its own
OS process (not just the TestClient) with fake-but-present
`BHASHINI_USER_ID`/`BHASHINI_API_KEY` and a monkeypatched `httpx.post`
raising `ConnectTimeout`, and curled `/assess/voice` directly:
```
$ curl -s -w '\nHTTP_STATUS:%{http_code}\n' -X POST http://127.0.0.1:8002/assess/voice \
    -F 'audio=@symptom.flac;type=audio/flac' -F 'age=30'
{"detail":"Bhashini request failed."}
HTTP_STATUS:503
```
matching the server's own log line `"Bhashini request failed: Bhashini
ASR request failed after retries: simulated connect timeout"`. Also
re-verified, on the same running server, the paths this fix could not
have touched: `GET /health` returned `{"status":"ok"}`; `POST /assess`
with a red-flag symptom ("chest pain since this morning") still
returned `emergency` with zero API key needed; an ordinary non-red-flag
case ("mild cough for two days") with no `ANTHROPIC_API_KEY` still
correctly returned `503`, `"Triage reasoning backend is not
configured."`.

Noted: `app/adapters/abdm.py` (SIH26047-track, out of this routine's own
scope) was not audited today for the identical retry-predicate pattern -
named here rather than silently assumed clean, the same way Day 12
named `GroqHistoryDraftingBackend._call`'s then-unfixed sibling gap for
a later session.

End-of-day check against `docs/DAILY_PROTOCOL.md`'s four questions:
Sems - yes, the same AI & System Programming Lab / MLOps-elective ground
(§08) Day 3 and Day 13 already cite, sharpened to a specific, mechanical
habit: checking a retry/except exception-type list against the real
library hierarchy with `issubclass()` rather than trusting a plausible
exception name. 2028 market - no new claim, restates what Entry 5/Days
6-19 already established, with the added, checkable distinction that
today's audit method (checking each predicate against the library's own
class hierarchy) is a more general technique than Day 19's own
same-file cross-backend comparison, and found a real bug in a third,
different backend module. On-campus GPREC - stays inside the core
in-scope pipeline (`app/adapters/bhashini.py` is what `/assess/voice`,
a core-pipeline endpoint, actually calls - not SIH26047 track, even
though `/case-intake/voice` also happens to use it). Real showcase value
- yes: a sixteenth real, reproduced, regression-tested bug, plus a
direct, evidenced answer to "how do you actually check whether a retry
policy is correct, not just present" (checked against the real
exception hierarchy, not assumed from the name). All four checks pass;
nothing flagged today.

Push diagnostic follow-up, since this session's instructions
specifically asked for it: root cause confirmed for a sixteenth time to
be the local `main` branch ref going stale/detached at each fresh
container start, not GitHub access - today's diagnostic went one step
further than prior days by reporting the raw `git remote -v` and
`--dry-run` output verbatim first, exactly as asked, before any
diagnosis or fix. This session's own final push (below) is the real
test of whether the fix holds.

What's next: still SHAP/LIME and CV-model training, both genuinely
blocked (fifteenth consecutive day, no API keys, all three
data-source domains still `403`/`connect_rejected`). The evaluation
harness's remaining 7 cases still need a live `ANTHROPIC_API_KEY`.
Today's fix closes a real gap in Bhashini's own timeout handling; a
real, named next step is auditing `app/adapters/abdm.py` for the
identical `httpx` retry-predicate pattern (not done today, SIH26047-
track and out of this routine's scope, but worth flagging for a session
that does cover that track). The next hardening pass should keep
applying today's own general method (checking exception-type lists
against the real library hierarchy with `issubclass()`) to any other
third-party-API call site in the in-scope pipeline not yet checked this
way - or move fully to build work the moment an API key or outbound
training-data-source access becomes available.

## Note — 13 Sep 2026, merge (SIH26047 track, not a numbered Day)

Merging today's own Day 20 (`main`) into this branch surfaced a real
conflict in `app/adapters/bhashini.py`/`tests/test_bhashini.py`: both
branches had independently fixed the same underlying gap (an
`httpx`-exception list narrower than what it claimed to cover) in
different, non-overlapping ways - this branch (12 Sep) widened the three
`except` clauses to the parent `httpx.TransportError`, `main`'s Day 20
widened the two `@retry` decorators to `(httpx.ConnectError,
httpx.TimeoutException)`. Kept both: the broader except-clauses (already
covering `httpx.ProxyError`, which `main`'s narrower pair does not) and
`main`'s retry-decorator widening (which this branch never touched, so
its `ConnectTimeout`/`WriteTimeout`/`PoolTimeout` requests previously
weren't retried at all, only eventually caught).

Resolving the conflict also surfaced two real, separate mistakes, caught
by re-running tests after merging rather than trusting the auto-merge:
1. The module docstring's PROXY-ERROR ADDENDUM still claimed "the retry
   decorators' own narrower (httpx.ConnectError, httpx.ReadTimeout) set
   is deliberately unchanged" - true when written, false the moment
   `main`'s widening merged in. Corrected to point at the decorators'
   own (now-accurate) comment instead of restating a set that no longer
   matched the code below it.
2. `main`'s own new end-to-end test,
   `test_assess_voice_returns_503_not_500_when_bhashini_times_out_connecting`
   (`tests/test_main.py`), sent `b"fake-audio-bytes"` as the upload -
   correct on `main`, where `transcribe()` never transcodes audio at
   all, but wrong once merged with this branch's 12 Sep fix, which runs
   every input through real ffmpeg-based `_transcode_to_wav()` first.
   Confirmed directly (`_transcode_to_wav(b"fake-audio-bytes")` raises
   its own "Could not decode uploaded audio" `BhashiniAdapterError`
   immediately) that the test's mocked `httpx.ConnectTimeout` was never
   actually reached - it passed, but for the wrong reason, landing on
   the same generic fallback-exhausted 503 any bad upload produces. This
   is the exact gotcha `tests/test_main.py`'s own `_tiny_wav_bytes()`
   helper already exists to prevent (see its docstring), just not yet
   applied to a test written on a different branch that didn't have it
   yet. Fixed by switching the test to `_tiny_wav_bytes()`, matching the
   sibling test directly above it in the same file. 354 tests passing
   after the merge (was 348 on this branch before merging, 306 on
   `main` - the 6-test gap is exactly Day 20's own additions, confirmed
   by running the full suite after every conflict resolution, not just
   after the last one).

## Note — 13 Sep 2026, voice-input follow-up (SIH26047 track, not a numbered Day)

A live report came in that voice input "doesn't listen to the person
completely." Investigated by actually reproducing it, not by guessing:
synthesized a real ~20-second, multi-sentence espeak-ng recording and ran
it through the exact pipeline `/assess/voice` uses when no Bhashini
credentials are configured (the state this prototype is deployed in
right now) - `_transcode_to_wav()` then `OfflineSpeechAdapter.transcribe()`
(PocketSphinx). Found and fixed two real, confirmed bugs in that path:

1. `_transcode_to_wav()` piped ffmpeg's WAV output through `pipe:1`
   (stdout). A pipe isn't seekable, so ffmpeg couldn't go back and fill
   in the real RIFF/data chunk sizes once encoding finished - it wrote
   the placeholder `0xFFFFFFFF` into both fields instead, confirmed
   directly on a real transcoded file, not assumed from ffmpeg's docs.
   Fixed by giving ffmpeg a real temp file as its output target instead.
2. `OfflineSpeechAdapter.transcribe()` hardcoded `wav_bytes[44:]` to
   strip the WAV header, assuming ffmpeg's output is always the minimal
   44-byte header. False for this project's actual ffmpeg: every
   transcoded file carries a "LIST"/"INFO" chunk (ffmpeg tagging its own
   encoder version) between `fmt ` and `data`, pushing the real audio
   start to byte 78, not 44 - confirmed by locating the literal `data`
   marker. The old code was fed 34 bytes of WAV chunk metadata as if
   they were the first 17 audio samples, on every single recording
   through this path. Fixed by parsing the real `data` chunk instead of
   assuming a fixed offset.

Honest finding, not spun into more than it is: bug #2's actual impact,
worked out precisely rather than assumed, is a ~1ms prefix of
decoder-confusing garbage before the complete, correctly-aligned real
audio (34 is an even byte count, so the 16-bit sample boundaries of the
real audio after it are undisturbed on this exact chunk size) - real and
worth fixing, but not remotely enough on its own to explain "doesn't
listen to the person completely." Checked the actual, harder-to-hear
truth directly rather than stopping at the easy fix: transcribed a short,
clean synthetic phrase ("I have a fever and a headache") through the
now-fixed pipeline and got "some of the law on that and i" back - and a
tail-only clip of just the long recording's last sentence produced
similar unrelated word-salad whether decoded alone or as part of the
full recording, evidence the full duration genuinely is being processed,
just decoded very badly throughout. This matches
`app/adapters/offline_speech.py`'s own pre-existing, already-disclosed
docstring caveat about PocketSphinx's real, measured accuracy ceiling
against even a clean synthetic voice - not a new problem, and not one
either of today's real fixes could have solved, because the actual
bottleneck is the acoustic model itself, not this project's plumbing
around it. Stated plainly rather than deflected to "get an API key":
without either a live cloud ASR credential (Bhashini) or a better local
model, this offline fallback's transcripts will keep reading as close to
unusable for arbitrary spoken symptoms - today's two fixes make the
pipeline correct, not accurate, and those are different claims.

Two new regression tests added and confirmed to fail against the
pre-fix code before being counted as passing (`git stash` on
`app/adapters/bhashini.py` alone, watched the new
`test_transcode_to_wav_writes_real_chunk_sizes_not_the_ffmpeg_pipe_placeholder`
fail with the exact predicted `4294967295`, then restored): that one in
`tests/test_bhashini.py`, plus two more in `tests/test_offline_speech.py`
(`TestPcmDataFromWav`) proving the exact byte-level regression against a
hand-built WAV fixture with a known PCM payload, independent of whatever
ffmpeg version is installed. 357 tests passing (was 354, zero
regressions). Also ran the real `uvicorn` server (no API keys set,
matching this prototype's actual deployed configuration) and posted a
real synthetic WAV to `/assess/voice` directly: succeeded end-to-end,
`requires_manual_triage: true` correctly set for the offline-fallback
path.

## Note — 13 Sep 2026, "audio won't progress smoother" (SIH26047 track, not a numbered Day)

Follow-up to the voice-input note above: a further live report that
audio "won't progress smoother" - investigated by testing the OUTPUT
side this time (the "Listen" playback of the spoken audio summary), not
assuming it was the same input-side bug just reported again. Drove the
real recording UI end-to-end with Playwright's fake-microphone flags
(`--use-fake-device-for-media-stream` feeding a real synthesized WAV,
not a mock of the JS), through the real `/case-intake/voice` submission,
to the real "Listen" button and the real `<audio>` element it creates.
Sampled `currentTime`/`paused`/`readyState` at 150ms resolution during
playback and checked for `longtask` entries over 100ms the whole time:
progression was linear and gap-free (`readyState` stayed 4, `paused`
stayed false, no stalls), and zero long tasks during playback. The
playback *mechanism* is not stuttering - checked directly, not assumed
from "it worked in the demo."

That leaves what "smoother" is actually describing: the voice itself.
`OfflineSpeechAdapter.synthesize()` (the path used whenever Bhashini
isn't configured, i.e. right now) uses espeak-ng, a formant synthesizer
- the same family of technique as 1980s-90s screen-reader voices, not a
modern neural TTS model. That is a real, inherent quality ceiling this
module's own docstring never previously disclosed for synthesize()
(only transcribe()'s accuracy got a caveat). Checked whether a better
offline option exists before writing anything: `pip install piper-tts`
succeeds (the package is on PyPI), but its actual voice models are
hosted on huggingface.co, which returns a live, confirmed 403 in this
environment - the identical restriction already documented for Vosk/
Whisper ASR models, now separately confirmed for TTS too. No viable
offline upgrade path exists here.

What IS real and fixable: espeak-ng's own un-set default rate is 175
words/minute - measured directly (not assumed) against this project's
own audio-summary template text at 175/160/145/130, 175 produced the
shortest, most rushed output of the four (5.9s vs 8.23s at 130).
Slowing formant-synthesized speech is a documented way to reduce how
clipped/rushed it sounds. Set `-s 145` (on the slower half of what was
tried, not the slowest) in `OfflineSpeechAdapter.synthesize()`, and
added the missing VOICE-QUALITY CAVEAT to the module docstring. Stated
as precisely as it can honestly be stated: this should reduce how
rushed the speech sounds - a claim about rate, backed by a real
measurement - not a fix for the underlying mechanical timbre, and NOT
confirmed by ear, because nothing in this project's toolchain can
listen to audio and judge how it sounds, only inspect its bytes,
duration, and format. Said plainly rather than oversold, matching how
the input-side note above was written.

One new regression test (`test_passes_the_tuned_slower_rate_to_espeak_ng`
in `tests/test_offline_speech.py`), confirmed to fail against the
pre-fix code first (`git stash` on `app/adapters/offline_speech.py`
alone, watched it fail on the missing `-s` flag, then restored). 358
tests passing (was 357, zero regressions).

## Day 21 — 14 Sep 2026

Push diagnostic (again required verbatim before any other work): `git
remote -v` showed the expected origin. `git push origin main --dry-run`
failed `non-fast-forward`. `git status` showed `HEAD` detached;
`git rev-list --left-right --count main...origin/main` showed local
`main` was **71 commits** behind `origin/main` (the largest drift any
session has hit - `HEAD` itself already matched `origin/main`'s tip
exactly). Confirmed local `main` was a strict ancestor
(`git merge-base --is-ancestor main origin/main`) before fast-forwarding
with `git checkout main && git merge --ff-only origin/main`. A
`--dry-run` immediately after reported "Everything up-to-date." Same
root cause Day 20 already pinned down precisely, just a bigger number
this time - not a new failure mode.

Re-verified fresh: no `ANTHROPIC_API_KEY`/`GROQ_API_KEY`/`BHASHINI_*` in
this environment, and `kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in`
all still `CONNECT tunnel failed, response 403` - sixteenth consecutive
identical result. SHAP/LIME, CV training-data prep, and the evaluation
harness's remaining 7 cases stay genuinely blocked. Moved to hardening
per `docs/DAILY_PROTOCOL.md`'s own fallback rule.

Built: rather than a fourth pass over retry predicates (Days 19-20
already audited every backend that has one), asked a more basic
question - which in-scope modules has this routine never actually
opened. Grepped `docs/INTERVIEW_NOTES.md` for "offline_speech" first:
zero matches across 20 days of entries, despite
`app/adapters/offline_speech.py` being wired directly into the core
`/assess/voice` endpoint as the fallback when Bhashini is unavailable.
Read the whole file fresh and found a real bug:
`OfflineSpeechAdapter.transcribe()`'s PocketSphinx decode call had no
timeout at all, even though a `_TRANSCRIPTION_TIMEOUT_SECONDS = 30`
constant already sat, defined but unused, right next to
`_SYNTHESIS_TIMEOUT_SECONDS` (which espeak-ng's own subprocess call in
the same file does use). Every other blocking call in the voice
pipeline - espeak-ng, ffmpeg's transcode, every Bhashini httpx call - is
bounded at 30 seconds; this was the one exception, and nothing on
`/assess/voice` caps uploaded audio length or size server-side (the
3-minute cap in `web/app.js` is a frontend `MediaRecorder` auto-stop
only, not enforced by the API). Reproduced directly first: synthesized
~250 seconds of speech with espeak-ng, ran it through the real decode
path, and timed it - ~60 seconds of real decode time, confirming decode
time scales with audio length with nothing bounding it. An arbitrarily
long direct POST (bypassing the frontend's cap entirely) could tie up a
worker thread for an unbounded duration.

Fixed with a new `_run_with_timeout()` helper in
`app/adapters/offline_speech.py`: runs the decode on a background
thread via `concurrent.futures.ThreadPoolExecutor` and bounds the
caller's wait with `Future.result(timeout=...)`. PocketSphinx has no
interrupt/cancel hook, so a timed-out call can't be force-stopped -
`executor.shutdown(wait=False)` lets the orphaned thread finish in the
background instead of blocking the timeout on it, the same tradeoff
`asyncio.to_thread()` itself already accepts on cancellation.
`transcribe()` now calls `_run_with_timeout(_decode,
_TRANSCRIPTION_TIMEOUT_SECONDS)` - wiring in the constant that already
existed - and converts `concurrent.futures.TimeoutError` to a clear
`OfflineSpeechAdapterError` naming the timeout.

Four new regression tests in `tests/test_offline_speech.py`: three
exercise `_run_with_timeout()` directly (a fast call returns normally; a
2-second sleep with a 0.1s timeout raises in under 1 second of real wall
-clock time, not just "raises the right exception"; a call that raises
its own exception propagates it unchanged), one proves the real wiring
end to end (real espeak-ng audio, real transcode, real `Decoder`, with
`_TRANSCRIPTION_TIMEOUT_SECONDS` monkeypatched to `0.0001`). All four
confirmed to fail against the pre-fix code first (`git stash` on
`app/adapters/offline_speech.py` alone, all four failed with
`ImportError: cannot import name '_run_with_timeout'`, then restored).
362 tests passing (was 358 at session start, zero regressions). Also ran
the real `uvicorn` server as its own OS process and curled it directly:
`GET /health` returned `{"status":"ok"}`; the red-flag emergency path
still returned `emergency` with zero API key needed; a real synthetic
English WAV posted to `/assess/voice` (no Bhashini credentials
configured, routed through the exact fixed code path) completed
normally with `requires_manual_triage: true` set, proving the fix
doesn't disturb the ordinary well-under-timeout case.

Noted: fixed to `docs/INTERVIEW_NOTES.md` and `README.md`'s Progress
section (Day 21 entries added to both, plus the "What's next" list).
Honest gap named, not fixed today: `app/models/ocr.py`'s
`pytesseract.image_to_string()` call has the identical shape (a
blocking native call, no timeout, no server-side upload-size cap) -
`pytesseract` actually accepts a `timeout` kwarg natively, so a fix
there would likely be smaller than today's, but it wasn't reproduced or
measured today and is a real next place to look, not assumed covered.

What's next, unchanged: SHAP/LIME (blocked on the CV model, which is
itself blocked on training data), CV training-data prep (blocked on
`kaggle.com`/`data.gov.in`/`aikosh.indiaai.gov.in`, all still 403 from
this environment's outbound proxy), and the evaluation harness's
remaining 7 cases (need a live `ANTHROPIC_API_KEY`, still unset).
