# SIH26047 — Patient Case-Taking Software

**This is the full, in-depth problem statement the project owner has directed CarePilot toward as a candidate SIH flagship submission.** Saved verbatim (reformatted for readability, encoding-corrected) so the whole team works from one authoritative copy instead of re-searching it each session. Reconciling this with CarePilot's existing GPREC-placement scope (`docs/DAILY_PROTOCOL.md`) is a separate, not-yet-done step — see the closing section below.

| Field | Value |
|---|---|
| PS Number | SIH26047 |
| Title | Patient Case-Taking Software |
| Organization | Ministry of Ayush |
| Department | All India Institute of Ayurveda |
| Category | Software |
| Theme | MedTech / BioTech / HealthTech |
| Idea submission deadline | 20 September 2026 |
| Submitted ideas (at time of retrieval) | 0 / 500 |

## Source and how this was retrieved

The official portal, **sih.gov.in**, is unreachable from this build environment (outbound network egress here is allow-listed, and `sih.gov.in` is not on that list — confirmed by a direct fetch attempt, not assumed). This document was originally retrieved from a third-party structured scrape of the SIH 2026 problem-statement list:

- Repository: [`NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements`](https://github.com/NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements) (public, MIT-style community mirror, not an official SIH resource)
- File: `data/sih2026_ps_20260822_211225.json`
- Scrape timestamp in that file: `2026-08-22 21:12:25`
- The raw record as retrieved (after fixing a `cp1252`/UTF-8 mojibake corruption present in the source file's dashes and quotes) is saved alongside this document at `data/sih/sih26047.json`.

**Update (30 Aug 2026) — independently corroborated.** The project owner pasted the PS26047 detail-page content directly (same "Problem Statement Details" layout the official portal uses). Compared line by line against the scrape above: **every section of body text matches — Background 1.1–1.3, Description 2.1–2.3, Expected Solution 3.1–3.4, all four modules, all five patient-journey steps — including the same unrecovered "Insert Table*3.2" gap and the same corrupted arrow characters in Module C's "Chief complaint ? HPI ? ..." line, both of which are now confirmed to be real defects in the source document itself, not artifacts introduced by the earlier scrape.** One real, corrected discrepancy: **the Theme field was wrong in the original scrape** — it said "Smart Automation"; the correct value, now used throughout this repo, is **"MedTech / BioTech / HealthTech."** Organization, department, category, PS number, title, and deadline all matched exactly and needed no correction.

**Honesty check, same standard as the rest of this repo's docs:** this still isn't a first-hand fetch of `sih.gov.in` performed by this project's own tools — it's a pasted copy, so the standard secondhand-source caveats apply in principle. In practice, the near-perfect match (down to shared, identically-located defects that would be extremely unlikely to arise independently in two different extractions) is strong evidence both are reading the same real underlying page, which is why the PS number, title, org, department, category, and deadline are now treated as confirmed rather than merely corroborated. The theme correction above is applied with the same confidence.

---

### Background

**1.1 The Clinical History-Taking Bottleneck in Indian Hospitals**

History taking — the structured elicitation of a patient's presenting complaints, history of present illness, past medical and surgical history, drug and allergy history, family and personal history, and a review of systems — is the single most important diagnostic activity in clinical medicine. Classical teaching holds that a well-conducted history yields the correct diagnosis in 70–80% of cases, even before examination or investigation. Yet in India's overburdened public hospital outpatient departments (OPDs), the time available for this critical interaction has collapsed to unsustainable levels.
India operates one of the most patient-dense healthcare systems in the world. Tertiary government hospitals and apex institutions routinely register 4,000–10,000 OPD patients per day, with a doctor-to-patient consultation time frequently reported between 2 and 5 minutes — among the shortest globally (study published in BMJ Open, 2017, across 67 countries placed India's average primary-care consultation at just over 2 minutes). Within this window, the physician must simultaneously elicit history, examine the patient, review prior records, formulate a diagnosis, counsel, and prescribe. The result is systematic under-elicitation of history, missed comorbidities, repeated questioning across visits, and diagnostic error.
AYUSH institutions face an additional layer of complexity. Ayurvedic history taking (Trividha, Ashtavidha, and Dashavidha Pariksha) requires detailed assessment of Prakriti (constitution), Vikriti (current imbalance), Agni (digestive capacity), Koshtha (bowel nature), Ahara-Vihara (diet and lifestyle), Nidana (causative factors), and Samprapti (pathogenesis) — a far more extensive history framework than allopathic intake. Capturing this depth manually within OPD time constraints is effectively impossible, forcing practitioners to abbreviate the very assessment that defines personalized Ayurvedic care.

**1.2 The Documentation and Records Fragmentation Problem**

Compounding the time problem is the fragmentation of patient records. Patients in India typically carry physical paper prescriptions, laboratory reports, discharge summaries, and imaging films from multiple prior providers. During consultation, the physician must manually scan through these unstructured documents — often handwritten, in varying languages, and chronologically disordered — consuming a significant fraction of the already-scarce consultation time. There is no point-of-entry mechanism to digitize, structure, and chronologically organize a patient's prior medical documents before they reach the consultation room.
The Ayushman Bharat Digital Mission (ABDM) has established the national digital health infrastructure — ABHA (Ayushman Bharat Health Account) IDs, the Health Information Exchange, and FHIR-based interoperability standards. However, the 'first-mile' problem remains unsolved: there is no efficient, patient-facing software platform that captures structured history and digitizes documents into the ABDM ecosystem before the clinical encounter begins.

**1.3 The Opportunity: AI-Powered Digital Clinical Intake Platform**

Self-service kiosks have transformed high-throughput service industries — ATMs in banking, self-check-in terminals in aviation, and ordering kiosks in quick-service restaurants — by offloading structured data-entry tasks from human staff to the user, dramatically improving throughput and accuracy. In healthcare, patient check-in kiosks are now widespread in developed-country hospitals, but these are limited to administrative check-in. None perform deep, AI-driven, multimodal clinical history acquisition with medical document digitization.
The convergence of mature enabling technologies — robust automatic speech recognition (ASR) for Indian languages and accents (Bhashini / AI4Bharat models), large language models for conversational clinical history elicitation, high-accuracy OCR for handwritten and printed medical documents, and ABDM's FHIR interoperability — now makes it feasible to build an AI-powered clinical history software platform.

### Description

**2.1 The Problem in Precise Terms**

There is no purpose-built, patient-facing software platform that enables patients to independently and comprehensively record their medical history — through both natural spoken conversation and guided touchscreen interaction — and simultaneously digitize their existing physical medical documents, generating a structured, physician-ready clinical history summary that integrates with the hospital information system and the ABDM ecosystem before the patient enters the consultation room.

**2.2 Why Existing Solutions Fall Short**

- Existing hospital registration systems (currently deployed in some Indian hospitals) capture only demographic and appointment data — name, age, department, token number. They do not elicit any clinical history or process medical documents.

- Mobile health apps and tele-triage chatbots require smartphone literacy, stable connectivity, and patient enrolment ahead of the visit — excluding the large elderly, rural, low-literacy, and first-visit patient populations who form the bulk of government hospital OPD load.

- Manual nurse-led triage / history desks are themselves human-resource-limited, do not scale to 5,000+ daily patients, and reintroduce the same time and transcription bottleneck the system is trying to eliminate.

- Generic document scanners digitize images but do not extract, structure, or chronologically organize clinical content, nor link it to a structured history or ABHA record.

**2.3 Specific Challenges a Solution Must Overcome**

- Multilingual, multi-accent voice capture in noisy hospital environments across Hindi, English, and major regional languages, for patients of varying literacy and digital comfort.

- Accessibility for low-literacy and elderly users through intuitive icon-driven UI, audio prompts, and conversational guidance — the software platform must be usable by a first-time, non-tech-savvy patient with zero training.

- Accurate clinical history structuring converting free-form patient narration into a standardized, physician-readable history (chief complaint, HPI, past history, drug/allergy, family, personal, review of systems) — and, for AYUSH settings, Dashavidha Pariksha parameters.

- Reliable medical document digitization OCR of handwritten and printed prescriptions, lab reports, and discharge summaries in multiple languages, with intelligent extraction of diagnoses, medications, and investigation values.

- Privacy, consent, and data security compliance with the Digital Personal Data Protection Act 2023 and ABDM consent framework — handling sensitive health data within a secure software environment.

### Expected Solution

**3.1 Solution Overview — 'MediKiosk' AI Clinical History Software Platform**

The proposed solution — tentatively designated MediKiosk — is a software platform that allows any patient to record a comprehensive medical history through natural voice conversation and guided touchscreen interaction, scan and digitize their existing physical medical documents, and generate a structured, physician-ready clinical history summary that is pushed to the hospital information system (HIS) and linked to the patient's ABHA record — all completed before the consultation, with minimal staff assistance required.

*(Note: the source document references an inline table at 3.2 that did not survive text extraction.)*

**3.3 Software & AI Stack (Integrated)**

**Module A — Conversational Multimodal History Engine**

A conversational AI engine that conducts a structured clinical history interview through both voice and touch. The patient speaks naturally in their preferred language; the engine asks intelligent follow-up questions (e.g., on stating 'chest pain', it probes onset, character, radiation, aggravating/relieving factors — the SOCRATES framework) and simultaneously offers touch-based multiple-choice options for patients who prefer tapping. Built on Indian-language ASR, a dialogue manager constrained by a clinical history ontology, and text-to-speech for audio prompts.

- Adaptive questioning: dynamically branches based on chief complaint and prior answers, mirroring a physician's clinical reasoning to elicit a complete HPI and review of systems

- Dual-mode input: every question answerable by speaking OR tapping, ensuring usability across literacy and comfort levels

- AYUSH history mode: for Ayurvedic OPDs, an extended interview capturing Dashavidha Pariksha (Prakriti, Vikriti, Sara, Samhanana, Pramana, Satmya, Sattva, Ahara Shakti, Vyayama Shakti, Vaya) and Ahara-Vihara assessment

- Red-flag detection: AI flags emergency symptoms (e.g., acute chest pain with dyspnoea, stroke symptoms) and triggers immediate priority alert to triage staff rather than routine queueing 

**Module B — Medical Document Digitization & Intelligence**

An integrated scanning and document-AI pipeline that allows the patient to upload prior prescriptions, lab reports, and discharge summaries. The system performs high-accuracy OCR (printed and handwritten, multilingual), then extract and structure clinical entities.

- Intelligent extraction: diagnoses, prescribed medications with dosages, investigation results with values and reference ranges, and procedure/surgery history

- Chronological organization: automatically dates and orders documents into a coherent medical timeline for the physician

- Abnormal-value highlighting: flags out-of-range lab values and potential drug interactions for physician attention 

**Module C — Structured History Summary Generator**

An AI summarization engine that synthesizes the conversational history and the digitized documents into a single, concise, physician-ready clinical summary in standard format — presented on the consultation screen the moment the patient enters the room. The physician reads a complete, structured history in seconds rather than spending minutes eliciting it, and can edit/confirm before saving.

- Standard clinical format: Chief complaint → HPI → Past medical/surgical → Drug & allergy → Family → Personal → ROS → Prior investigations summary

- Editable & verifiable: physician retains full control — the summary is a draft to accept, amend, or reject, never an autonomous diagnosis

- Bilingual output: patient-facing audio confirmation in local language; physician-facing summary in English/Hindi 

**Module D — Consent, Privacy & ABDM Integration**

A robust consent and security layer compliant with the Digital Personal Data Protection Act 2023 and the ABDM consent framework. The patient authenticates via ABHA ID, grants explicit consent for data capture and sharing, and the structured history is pushed to the hospital HIS/EMR and linked to the ABHA Personal Health Record via FHIR APIs.

- Secure processing: voice and document AI are processed securely within the software platform

- Session termination: temporary session data is cleared immediately after submission

- Consent-first design: granular, revocable consent with audio explanation for low-literacy patients 

**3.4 End-to-End Patient Journey**

- Step 1 — Identify: Patient logs into the software platform, enters/scans ABHA ID or Aadhaar details or registers as new; selects language; grants consent (audio-guided)

- Step 2 — Converse: AI conducts adaptive voice + touch history interview, capturing chief complaint, HPI, and full history; red flags trigger priority triage

- Step 3 — Scan: Patient uploads prior prescriptions, lab reports, and discharge summaries; AI digitizes, structures, and timelines them

- Step 4 — Summarize & Route: AI generates structured history summary, links to ABHA, pushes to HIS, updates the patient's digital record; summary appears on physician's screen at consultation

- Step 5 — Consult: Physician reviews complete history in seconds, edits/confirms, and devotes the full consultation to examination, reasoning, and counselling


---

## Why this matters for CarePilot specifically

This problem statement is a direct, sharper-scoped superset of what CarePilot already does — not a pivot to an unrelated domain:

- CarePilot's Intake Agent (`app/agents/intake.py`) already does structured, deterministic-plus-LLM history capture with a red-flag safety net — SIH26047's Module A ("Conversational Multimodal History Engine" with red-flag detection) is the same idea, generalized from a self-care/clinic/urgent/emergency triage output to a full physician-facing history summary.
- CarePilot's Bhashini adapter (`app/adapters/bhashini.py`) already does the multilingual voice capture Module A explicitly requires ("Multilingual, multi-accent voice capture... across Hindi, English, and major regional languages").
- CarePilot's OCR pipeline (`app/models/ocr.py`) is the seed of Module B ("Medical Document Digitization & Intelligence") — currently prescription/lab-report text extraction, not yet the full structured extraction (diagnoses, dosages, chronological ordering) SIH26047 calls for.
- CarePilot does **not** yet have: an AYUSH-specific history mode (Dashavidha Pariksha parameters), ABDM/ABHA/FHIR integration, a structured summary generator (Module C), or the consent/DPDP-compliant layer (Module D) — these are the real, honest gaps between what exists today and what this PS requires. Recorded here plainly, not glossed over, matching this project's existing documentation standard (see `docs/INTERVIEW_NOTES.md`).

**Not yet done:** `docs/DAILY_PROTOCOL.md` still records the original GPREC placement-prep goal and scope (including build-order and pre-authorization rules) and has not yet been updated to reflect an SIH-flagship direction. That update — deciding whether SIH26047 replaces, extends, or runs alongside the placement-prep goal, and what build order follows from it — needs an explicit decision from the project owner before the protocol doc (and downstream planning) is rewritten. This document exists to make that decision informed, not to presume its outcome.
