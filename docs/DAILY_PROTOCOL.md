# Daily Work Protocol — CarePilot

Day One: 25 July 2026. Goal: high LPA through GPREC's own on-campus
placement process, 2028. Target band: ₹7–11L (TCS Prime/Digital,
Infosys Digital-Specialist) — real, proven by two CSM students in
GPREC's own 2025 data, not aspirational.

This file is the standing rule for every work session on this project.
Once invoked to work on CarePilot, these rules apply without re-asking
for permission each time — that authorization is granted here, once,
not re-litigated block by block.

## The two blocks, every working day

### Block 1 — Build, ~55 minutes
- Work the next undone piece in build order: CV image-triage model →
  Bhashini vernacular layer → Docker deployment → SHAP/evaluation pass.
- Real code, real tests, actually run — never claimed done without proof.
- If a piece can't finish in the block, stop at a clean, passing
  checkpoint. Never leave the repo in a broken state between sessions.

### Block 2 — Notes, ~55 minutes
For whatever Block 1 produced (or the most recent unnoted piece):
- Plain explanation of what was built and why, in the same voice as
  `docs/INTERVIEW_NOTES.md`.
- Real interview Q&A pairs — not generic theory, tied to an actual file
  and line in this repo.
- Explicit tie to GPREC coursework (which Sem, which elective) where one
  exists — don't force one where it doesn't.
- Explicit tie to 2028 market relevance — why a recruiter would care,
  sourced from what's already verified in the placement report, not
  restated as a new claim.

### End-of-day check (not time-boxed — a checklist, not a block)
Before calling the day done, check both blocks against:
1. **Sems** — does today's work map to real GPREC coursework, or drift
   into something the syllabus doesn't back?
2. **2028 market** — does it still sit on a growing skill category, or
   has today's work quietly wandered into something saturating?
3. **On-campus GPREC specifically** — does it still serve the ₹7–11L
   on-campus target, not an off-campus story that was already ruled
   out of scope?
4. **Real showcase value** — would this survive a TCS Prime or SAP Labs
   interviewer's follow-up question, or does it only sound good until
   someone asks "why"?

Anything that fails a check gets flagged and fixed the same day, the
same way the two real bugs and the stale-doc errors already found in
this project were — named plainly, not smoothed over.

## What's pre-authorized, and what isn't

**No permission needed, every day:** writing and editing code, tests,
and docs inside this project's own directories; running the local test
suite; running the local dev server for verification; updating
`README.md` and `docs/INTERVIEW_NOTES.md` to match reality.

**Still requires an explicit go-ahead:** anything destructive; any
external network call beyond what's already approved (the Anthropic
API, public government/open-data sources); any deployment to a live
public URL; pushing this repo to GitHub or any remote; any change to
project scope or goal from what's recorded above.

## The honest limit on "daily," recorded plainly

There is currently no mechanism that runs this protocol in the
background while you're not in a session — a cloud-scheduled routine
needs this repo on GitHub (it isn't), and local scheduling only survives
for 7 days and dies when the app closes. Until one of those is set up
deliberately, "daily" means: this protocol runs automatically, without
re-asking, every time work on CarePilot resumes — not that it runs
unattended while you're away. That distinction is recorded here so it's
never quietly overstated later.
