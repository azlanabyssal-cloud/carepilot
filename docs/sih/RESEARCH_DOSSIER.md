# SIH26047 — master research dossier

**Purpose:** every piece of research this project has actually done on SIH26047 and the market context around it, in one place, with each claim tagged by how solid it is. Scattered facts across a long conversation are how errors slip in — this file exists so nothing here is a guess dressed up as a fact. If a claim in this file isn't tagged, that's a bug in this file — flag it.

**Tagging key:**
- 🟢 **VERIFIED** — read directly from a primary or near-primary source this project actually fetched, or a fact independently corroborated by 2+ unrelated sources.
- 🟡 **SECONDARY** — from a `WebSearch`-tool synthesis of third-party sources (blogs, guides). Plausible, cited, but not a primary document, because the primary document was unreachable.
- 🔴 **UNVERIFIED / OPEN GAP** — named explicitly because this environment could not check it. Needs a human, with normal internet access, to close.

---

## 1. The problem statement itself

🟡 **SIH26047, "Patient Case-Taking Software," Ministry of Ayush, department: All India Institute of Ayurveda, category Software, theme Smart Automation, idea-submission deadline 20 September 2026.**

Full text saved at `docs/sih/SIH26047_Patient_Case_Taking_Software.md`. Source: a third-party GitHub scrape (`NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements`, scrape timestamp 22 Aug 2026), **not** `sih.gov.in` directly — that domain returns `EGRESS_BLOCKED` from this environment on every fetch attempt made. The scrape is internally consistent (matches the official PS numbering scheme, matches the Ministry of Ayush's other listed 2026 entries) but has one acknowledged, flagged data-loss spot: an inline table at PS section 3.2 that didn't survive text extraction.

🔴 **OPEN GAP:** the real PS text on `sih.gov.in` has never been directly read by this project. If you can reach it from your own machine, that's the single highest-value fact-check available — confirm the four modules (A–D) match what's in our saved copy, and specifically check whether section 3.2's missing table contained anything not already captured.

## 2. A real research error, caught and corrected — worth recording, not hiding

🟢 **VERIFIED (self-correction, logged here for the record):** a team-recruitment flyer you found (`SIH26047_Team_Recruitment_Flyer.pdf`) described SIH26047 as being about NAMASTE/ICD-11 TM2 "dual-coding" — a real, WHO-recognized, actively-rolled-out Indian government initiative (confirmed: NAMASTE Portal is real, ICD-11 TM2 launched on WHO's browser February 2025, dual-coding is a real mandated system). **But that dual-coding requirement is problem statement `SIH25026`, a different PS, not `SIH26047`.** Confirmed two ways: (a) our own saved PS26047 text contains zero mentions of NAMASTE, ICD-11, or dual-coding anywhere — checked directly with `grep`, not by memory; (b) a separate search independently identified `SIH25026` by name as the NAMASTE/ICD-11 integration problem statement.

**Why this belongs in a research dossier, not just a chat message:** it's a demonstrated example of exactly the failure mode this whole document exists to prevent — a plausible-sounding, well-written, *wrong* source almost got treated as authoritative. The fix was cross-checking against our own already-verified primary text before accepting the new claim. That discipline needs to hold for every future finding too, including everything else in this file.

## 3. How SIH is actually judged

🟡 **SECONDARY**, but consistent across multiple independent third-party sources (hackathon-guide blogs, GeeksforGeeks contest-experience writeups) — no single primary AICTE rubric document was reachable:

- Multi-round scoring, each round scored 1–20 across criteria, weighted into a final score out of 100.
- Named criteria: innovation, technical implementation, usability, impact, clarity of presentation, fit to the stated problem.
- Most-repeated finding: judges reward a **narrow, stable, working prototype** over an ambitious, incomplete one.
- Second most-repeated: judges reward **solving the actual stated problem**, not technology-stack name-dropping.
- Team structure commonly reported: 6 students + 2 mentors, at least one female member — **this is a registration-eligibility fact, not a scoring one, and matters practically** (see Section 6).

🔴 **OPEN GAP:** no primary AICTE evaluation rubric PDF was found or fetched. If your SPOC has one, that supersedes everything in this section.

## 4. ABDM / FHIR technical feasibility — the numbers that reshaped the plan

🟡 **SECONDARY**, but cited consistently:

- ABDM sandbox registration → real M1 (ABHA ID creation/verification) integration: reported timeline **2–4 weeks**.
- Full HIP/HIU integration with consent-managed FHIR data exchange (M1+M2+M3): reported timeline **6–12 weeks**, including NHA sandbox testing.
- Standards: HL7 FHIR R4 with the ABDM Implementation Guide; ICD APIs (relevant to the *other* PS, `SIH25026`, not this one) use OAuth2 client-credentials auth.

**Why this matters concretely for SIH26047:** claiming a *full* ABDM/FHIR integration in a 36-hour build is not credible and a judge who knows ABDM will catch it (Section 3's "fit to the problem" criterion cuts both ways — overclaiming fit is itself a fit failure). The correctly-scoped move is real sandbox registration **now**, during prep time, with a working M1 call, presented honestly as a bounded proof — not a finished claim.

🔴 **OPEN GAP:** ABDM sandbox registration has not actually been started. This needs doing, not just planning — it's on the critical path given the 2–4 week timeline against a 20 September deadline.

## 5. The 2028 India AI/ML job market — what's real, cited

🟢/🟡 **Mixed** — market-size and headline growth numbers below are 🟡 secondary (industry-report and news-article synthesis, not a single authoritative dataset), but consistent across multiple independent sources, so treated as reliable directional signal:

- India's AI talent pool: ~650,000 → projected ~1.25 million by 2027, against 2.3 million+ open roles — a real, large, named talent gap.
- AI/ML hiring rose 33–34% year-on-year (most recent period reported); fresher hiring specifically up ~6% y/y.
- **Agentic AI / LLM application engineering named as the fastest-growing, least-saturated AI specialization**: "AI agent" skill job postings up 300%+ between Jan 2025–Mar 2026; NASSCOM projects 50,000+ specialized agentic AI roles needed by 2027 against ~18,000 GenAI/LLM engineers currently existing.
- Explicitly stated: *"Agentic AI Engineering requires strong Python and LLM application experience, but not the ability to train models from scratch."*
- Freshers: ₹6–10L (service companies) to ₹10–15L+ (product/startups) reported for AI/ML roles — consistent with, not contradicting, this project's original ₹7–11L target band.
- **Healthcare interoperability (FHIR + ABDM) named as a specific, funded, scarce niche**: ABDM capex ~$400M/year through 2026, $800M in state-level digital-health grants, 799.1 million ABHA accounts live (as of Aug 2025), explicit named demand for *"bridge professionals — people who understand both HL7 FHIR and India's ABDM architecture."*

🔴 **OPEN GAP:** none of this is from a single primary labor-market dataset (e.g., a NASSCOM or LinkedIn Economic Graph report directly fetched) — it's aggregated from multiple secondary articles that themselves cite such reports. Directionally credible given consistency across sources; not something to quote as a single hard statistic without checking the original report if this ever goes in front of a skeptical audience.

## 6. Real, unresolved risks — named plainly, not softened

- 🔴 **Team eligibility**: whether solo-in-practice building (teammates exist on paper, per your own statement, but aren't doing the technical build) satisfies your institute's internal-round rules has not been confirmed. The commonly-reported 6-student team-size rule is 🟡 secondary; your SPOC's actual rule is the only fact that matters and hasn't been checked.
- 🔴 **AYUSH/Dashavidha Pariksha domain accuracy**: no AYUSH-trained reviewer has looked at anything built so far. Still the single largest credibility risk given the sponsor (AIIA) is a real Ayurveda institution.
- 🔴 **Bhashini live API**: never called with real credentials in this environment. Orchestration logic is tested against a fake backend only.
- 🔴 **This environment's network restrictions**: `sih.gov.in`, Kaggle, data.gov.in, and most primary-source hosts are unreachable from here. Every 🟡-tagged fact above is a candidate for upgrading to 🟢 if checked from an unrestricted connection — see the cloud-vs-local recommendation given alongside this document.
- 🔴 **AI-assisted code policy — two secondary sources actively contradict each other, unresolved:** one search result states *"Use of GenAI tools is allowed for brainstorming and research only; pre-developed or AI-generated code is prohibited."* Another states *"AI assistants (ChatGPT, Copilot, etc.) permitted but must be declared in your submission — failure to disclose results in disqualification,"* and separately that judges "expect AI integration" and encourage tools like Claude/Cursor/Copilot for the 36-hour build. These cannot both be the literal rule as worded. Working theory (reasoning, not confirmed): the "prohibited" framing likely targets submitting a pre-existing product as if built fresh for this hackathon, not banning AI-assisted coding outright — but this is an inference, not a verified fact. **This needs your SPOC's direct confirmation before final submission** — specifically, whether AI-assistance must be declared, and where/how. Real disqualification risk either way if left unchecked.

---

**How to use this file going forward:** when new research comes in — from you, from me, from anything you find — it gets added here with an honest tag, not just stated in chat and forgotten. If a 🟡 or 🔴 item gets checked against a primary source, update its tag here. This file is the single source of truth for "what do we actually know," so it needs to stay accurate more than it needs to stay impressive.
