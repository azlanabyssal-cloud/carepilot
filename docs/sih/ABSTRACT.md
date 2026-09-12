# SIH26047 — Idea Submission Abstract (MediKiosk / CarePilot)

**Purpose of this file:** the actual submission-portal text (per `docs/sih/README.md`'s own reported field structure: Idea Title, Proposed Solution, Technical Approach, Feasibility and Viability, Impact and Benefits, Research). Every claim below is either something this repo has built and tested, or is explicitly marked as planned/unverified — matching the honesty standard `docs/sih/RESEARCH_DOSSIER.md` and `docs/DAILY_LOG.md` already hold every other document in this project to. This is a draft for a human (the team/SPOC) to review, trim to the portal's actual character limits, and submit — not something to paste in unedited.

---

## Idea Title

**MediKiosk — AI-Assisted Patient Case-Taking for the 2-Minute OPD Consult**

## Problem (background, in one paragraph)

Indian tertiary OPDs see 4,000–10,000 patients a day with consultations averaging just over two minutes (BMJ Open, 2017, 67-country study) — too little time to elicit a complete history, the step classical teaching credits with 70–80% of correct diagnoses on its own. AYUSH institutions carry an even heavier history-taking load (Dashavidha Pariksha's ten-parameter constitutional assessment). Patients also arrive holding physical prescriptions, lab reports, and discharge summaries with no way to digitize or chronologically organize them before the consultation. No existing tool — registration kiosks, tele-triage chatbots, or manual nurse-led triage — captures structured clinical history *and* digitizes prior documents *before* the patient reaches the doctor.

## Proposed Solution

A software platform that lets a patient, while waiting, (1) describe their symptoms by typing, speaking, or both, (2) photograph any prior prescriptions/lab reports/discharge summaries, and (3) receive — and hand their physician — a structured, physician-ready case summary (Chief Complaint → HPI → Past/Drug/Family/Personal History → Review of Systems → Prior Investigations) before the consultation begins. The system never diagnoses or prescribes: every summary is an editable AI-drafted scribe's note a physician reviews, amends, or confirms — never an autonomous decision.

Two design commitments run through the whole system, verified by this project's own tests, not asserted:

1. **A deterministic safety net that never depends on a live AI backend.** A fixed, auditable red-flag term scanner (now fuzzy-matched against misspellings and Hindi-English code-switched input, e.g. "cheast pain", "mera chest mein bahut pain hai") short-circuits straight to an EMERGENCY escalation before any model call — measured at 100% recall on the deterministic subset of an 11-case author-labeled evaluation set (`GET /evaluation/report`, real-time, no cached numbers). When the LLM-backed reasoning path itself is unavailable — no key, no network, a rate limit — the system degrades to a conservative, honestly-labeled result (`requires_manual_triage`) instead of failing outright, verified live against a running server with all API keys removed.
2. **Radical honesty about what's real versus planned.** Every capability below is labeled by its actual state, not its intended one.

## Technical Approach

- **Backend:** Python/FastAPI, four-agent pipeline (Intake → Triage-Reasoning → Guideline-Verification → Referral), Anthropic Claude for LLM reasoning/drafting with automatic fallback to deterministic logic.
- **Document digitization (Module B):** Tesseract OCR + regex-based structured extraction (diagnoses, medications+dosages, lab values with abnormal-range flagging, dates) — real and tested against rendered synthetic prescriptions, not yet validated against genuinely messy handwriting. Multiple uploaded documents are chronologically organized (dated documents first) before summarization.
- **Voice input/output:** Bhashini (MeitY) ASR/translation/TTS adapter. Browser audio is transcoded to 16kHz mono WAV via ffmpeg before reaching Bhashini's API (browsers record WebM/Opus, which Bhashini does not accept) — orchestration logic is tested end-to-end; the live Bhashini API itself has never been called with real credentials from this environment and is explicitly flagged as unverified, not claimed as proven.
- **Persistence:** SQLite (`app/db.py`), one physician-queryable table, not a JSON blob — real column-level querying, migration-safe.
- **AYUSH mode:** an opt-in Dashavidha Pariksha interview scaffold, ten parameters split into patient-self-reportable (kiosk-askable) versus physician-examination-only fields, each gloss corroborated against cited Ayurvedic-informatics literature — explicitly labeled a starting scaffold pending review by an AYUSH-qualified clinician, not a validated clinical instrument.
- **Consent/privacy:** explicit consent gate before any case is persisted; a document-backed intake path shares the same gate.

## Feasibility and Viability

**Feasible now, real and running:** the red-flag safety net, OCR/document-digitization pipeline, chronological document ordering, and the zero-API fallback layer all work with no external dependency and are covered by an automated test suite (323 tests passing as of 12 Sep 2026 — see `docs/DAILY_LOG.md` for the day-by-day build history this number comes from). **Feasible with real, bounded effort, not yet done:** ABDM/ABHA sandbox integration (public timelines for a first working M1/ABHA-ID call run 2–4+ weeks; a full HIP/HIU FHIR exchange runs materially longer per more recent vendor guidance) and a real Bhashini live-credential test. **Named risk, not hidden:** OCR accuracy on genuinely messy handwritten prescriptions is unverified; the Dashavidha Pariksha content needs a real AYUSH/BAMS-qualified reviewer before any claim of clinical validity.

## Impact and Benefits

Gives a physician a complete, structured history in seconds instead of the minutes a 2–5 minute consult cannot spare, without replacing clinical judgment. A patient's own OCR'd prior records travel with them instead of being re-elicited from memory at every visit. The red-flag layer is designed as a second, independent safety net beneath the AI reasoning layer specifically so a model failure or outage cannot silently downgrade a genuine emergency.

## Research

Grounded in classical clinical-history-taking literature (70–80% diagnostic yield from history alone) and a 2017 BMJ Open 67-country primary-care consultation-length study; Ayurvedic Dashavidha Pariksha parameter definitions cross-checked against cited literature (Zenodo, AyurVAID, JAIMS, CCRAS) rather than paraphrased from memory; ABDM integration timelines sourced from multiple independent 2025–2026 integration guides (flagged as vendor-authored, and therefore checked for the obvious sales incentive to understate effort). Full source-graded detail, including everything marked unverified and why, is kept current in `docs/sih/RESEARCH_DOSSIER.md` and `docs/sih/SIH26047_STRATEGY.md` in this repository — available to any reviewer who wants the primary trail behind every claim above, not just the claim itself.
