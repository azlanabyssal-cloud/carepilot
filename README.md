# CarePilot

Agentic rural health-triage and referral copilot. **A triage aid, not a
diagnostic tool** — every design decision below exists to route a person
to the right level of care, never to replace one.

Status: all four core agents built, tested, and running end-to-end via
`/assess`. See `docs/INTERVIEW_NOTES.md` for the reasoning behind each
decision as it was made — that file is the real changelog, including two
real bugs found and fixed.

## Problem

A first-mile triage question — "is this self-care, a clinic visit, or an
emergency" — answered for someone without easy doctor access, who may not
be English-fluent, and needs an answer now.

## Architecture

```
Patient input (text / voice / image)
        │
        ▼
  Intake Agent            ← done: normalizes input, runs a deterministic
        │                     red-flag keyword scan before any model sees it
        ▼
  Triage-Reasoning Agent   ← done: LLM proposes self-care / clinic / urgent /
        │                     emergency; red-flag cases short-circuit here
        ▼
  Guideline-Verification   ← done: TF-IDF retrieval over data/guidelines/,
        │                     escalation-only, never lowers a proposed level
        ▼
  Referral Agent           ← done: self-care instructions, a named facility,
                               or an emergency message - never a diagnosis
```

## Progress

- [x] Data contracts (`app/schemas.py`)
- [x] Intake Agent + rule-based emergency pre-filter (`app/agents/intake.py`) — tested, running
- [x] Triage-Reasoning Agent (`app/agents/triage.py`) — Anthropic backend, retry/backoff, graceful failure without a key, red-flag short-circuit — tested and running
- [x] Guideline-Verification Agent (`app/agents/verify.py`) — TF-IDF retrieval over a starter guideline corpus, escalation-only logic — tested and running
- [x] Referral Agent (`app/agents/referral.py`) — self-care/facility/emergency branching over a small, sourced Kurnool-district facility list — tested and running, full pipeline wired into `/assess`
- [ ] Bhashini (Telugu) input layer — optional, added after the English core is solid
- [ ] CV image-triage model
- [ ] Docker + cloud deployment
- [ ] SHAP/LIME explainability report
- [ ] Evaluation: recall on emergency-flagged cases (the metric that matters, not accuracy)

## Running it

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"symptom_text": "chest pain since this morning", "age": 45, "duration_days": 0}'
```

`/intake` and `/triage` also exist as narrower, independently testable slices of the same pipeline — see `app/main.py`.

## Data sources — what's real, and what still needs replacing

- **Facilities** (`data/facilities/kurnool_facilities.json`): the first two entries are real, sourced facilities — one verified directly against Kurnool district's own government portal (kurnool.ap.gov.in), one from a government-hospital directory listing. The third is an explicitly labeled placeholder pending a real PHC name from the district's own published PHC directory.
- **Guideline corpus** (`data/guidelines/seed_guidelines.json`): every entry is labeled `STARTER_SEED` — written for this repo, not extracted from a verified ICMR/WHO document. Replace before claiming "real government data" anywhere this project is presented.
- **Bhashini APIs** — real, government-run, not yet integrated (see Progress above).
- **AIKosh / data.gov.in** — the intended source for the eventual CV-model training data and a larger, verified guideline corpus; not yet pulled in.

## Ethical framing (read before demoing this to anyone)

- Not diagnostic, ever — the system's only outputs are self-care guidance,
  a named facility referral, or an emergency flag.
- Health data used for evaluation must be public or de-identified.
  DPDP Act 2023 considerations apply if this ever handles real patient data.
- The metric that matters is **recall on emergency-flagged cases** — a
  missed emergency is a far worse failure than an unnecessary referral.
