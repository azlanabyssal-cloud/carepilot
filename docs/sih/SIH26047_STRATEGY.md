# SIH26047 — deep-reasoning strategy: how CarePilot/MediKiosk wins, not just competes

**Purpose of this document:** a single, honest, load-bearing strategy artifact — not a pep talk. Every claim below is tagged as either (a) sourced from `docs/sih/SIH26047_Patient_Case_Taking_Software.md` (the PS text itself), (b) sourced from a cited web search this session actually ran, or (c) this project's own reasoning/judgment, clearly marked as such. Nothing here is invented statistics or fabricated authority — see the Honesty Ledger at the end for exactly what is and isn't verified.

**One framing note up front, stated plainly rather than left implicit:** "top 1% mentors" and "top 1% HRs" below means this analysis is run *through the lens of* the actual evaluation criteria real SIH judges and technical hiring panels are documented to use (cited in Section A) — not a claim that named real individuals were consulted. Pretending otherwise would be exactly the kind of overclaiming this project's own docs (`docs/INTERVIEW_NOTES.md`) have consistently refused to do, and doing it here would undercut the credibility this document exists to build.

---

## TL;DR verdict

CarePilot is **not** starting from zero on SIH26047 — the red-flag safety net, the Bhashini multilingual voice adapter, and the OCR seed are real, working, tested components that map directly onto PS26047's Module A and Module B. That is a genuine head start over a team starting today from a blank repo.

But CarePilot **cannot win on those alone**, because every serious team will also reach for "LLM does triage + Whisper does voice + Tesseract does OCR" — that combination is now the *default*, not a differentiator. The actual winnable edge is in the three things almost no other team will do correctly, because each requires either real domain knowledge, real government-rail understanding, or real engineering discipline under a 36-hour clock:

1. **A correctly-scoped, honestly-labeled AYUSH/Dashavidha Pariksha history mode** — not decorative Sanskrit terms bolted onto a generic symptom form.
2. **A demonstrated, working understanding of the ABDM sandbox (M1/ABHA at minimum)** — not a slide claiming "ABDM integrated" with nothing behind it.
3. **A stable, narrow, live-demoable core loop** — judges are documented to reward a working MVP over an ambitious broken one, every time.

Everything below explains why, in depth, and what to actually build.

---

## Section A — The SIH meta-game: what's actually being optimized for

This is not "build the coolest AI demo." SIH is a government-run, ministry-sponsored program (AICTE/MoE), and the problem statement itself was written by a real institution — the **All India Institute of Ayurveda** (department field in the PS record) — that has to live with whatever gets built if it's ever adopted. That changes what wins.

From this session's own research into how SIH is actually judged (WebSearch, cited — treat as credible synthesis from multiple hackathon-guide sources, not a primary SIH document, since `sih.gov.in` itself is unreachable from this environment):

- **Judging is staged and scored, not vibes-based**, and as of an 11 Sep 2026 research pass, two separate weighted rubrics are reported for the two stages that actually apply before the Grand Finale:
  - **Internal Hackathon (institute level, screens which team represents GPREC at all):** Problem Understanding & Impact **25%**, Innovation & Technical Excellence **30%**, Feasibility/Practicability/Scalability **25%**, Solution Quality & Presentation **20%**.
  - **National idea-submission stage (the PPT, decided per source without a live demo):** five criteria reported — Innovation, Invention, Technical Feasibility, Impact and Benefits, Architecture. One source states roughly **5 teams are shortlisted per problem statement nationally** — against up to 500 submitted ideas on a popular PS, per the 0/500 counter already recorded in this doc's own metadata table. That ratio is the real competitive bar this plan has to clear, not an abstraction.
  - Still 🟡 secondary (third-party guide synthesis, not a primary AICTE rubric document — `sih.gov.in` remains unreachable, re-confirmed 11 Sep 2026), but now sourced from articles specific to the PPT-scoring mechanics rather than generic hackathon advice, so treated as more reliable than the earlier, vaguer "1–20 per criterion" figure it supersedes.
- **How well the solution fits the stated problem statement is explicitly scored** (both rubrics above name it in some form — "Problem Understanding & Impact" internally, an implicit fit criterion nationally). Scope drift is a scored-down failure mode, not a neutral one.
- **The single most repeated, most concrete finding across sources:** *"Judges consistently favor a stable, working prototype over an ambitious build with incomplete functionality."* A narrow thing that actually runs beats a broad thing that crashes on stage.
- **Second most repeated finding:** *"Judges evaluate how effectively you solve the stated problem — not how many buzzword technologies you cram in."* A RAG pipeline, three LLM calls, and a vector database do not impress a judge who asked whether the red-flag detector actually catches "can't catch my breath" — this project's own existing Entry 1 in `docs/INTERVIEW_NOTES.md` is a stronger answer to a judge than any tech-stack slide.
- **Third:** *"Winners researched the real need behind their problem"* — i.e., judges can tell the difference between a team that read the PS once and a team that understands *why* 2-minute OPD consultations, Dashavidha Pariksha, and the ABDM first-mile gap are real, specific, named problems (all three are explicit in the PS text, not paraphrased by us).

**What this means concretely:** the PPT/idea-submission stage and the Grand Finale are judged on different things. The PPT stage (6-slide AICTE format, per `docs/sih/README.md`) is judged on **problem understanding + solution clarity + feasibility narrative** — you do not need a finished product to win it, you need to visibly understand the problem better than the other 200+ teams who were handed the exact same PS text. The Grand Finale (36 hours, live) is judged on **a working core loop that survives being poked at live** — not on how many modules exist as slides.

---

## Section B — PS26047 decomposed: commodity vs. differentiating sub-problems

The PS names four modules (A–D) plus a patient journey. Not all four are equally hard, and not all four are equally *judged*. Sorting them by real difficulty and real differentiation value:

| Sub-problem | Difficulty | Differentiation value | Why |
|---|---|---|---|
| Basic symptom chatbot (single LLM call, English only) | Low | **~zero** | This is what every team defaults to. CarePilot already has this (Triage-Reasoning Agent) — table stakes, not a selling point on its own. |
| Multilingual voice capture (Bhashini/AI4Bharat) | Medium-high | **Medium** | Genuinely hard to get right for noisy hospital audio and Indian accents — most teams will fake this with browser `SpeechRecognition` (English-only, silently fails on Telugu/Hindi) rather than real Bhashini integration. CarePilot's `app/adapters/bhashini.py` is real, tested orchestration logic — but **honestly unverified against the live API** (documented in this repo already). That gap needs closing before it's a real differentiator, not just a claimed one. |
| OCR + structured document digitization (Module B) | Medium-high | **Medium-high** | Handwritten Indian prescription OCR is a genuinely hard CV problem — most teams will demo it once on a clean printed sample and never mention the failure rate on real handwriting. CarePilot's `app/models/ocr.py` already has the intellectual honesty pattern needed here (Day 2's documented OCR-preprocessing bug) — extending it to *structured extraction* (diagnoses, dosages, chronological ordering, abnormal-value flagging) is real, unclaimed work. |
| Adaptive, ontology-driven history interview (SOCRATES framework, Module A) | High | **High** | The PS explicitly names the SOCRATES framework (onset, character, radiation, aggravating/relieving factors) for follow-up questioning. A single LLM prompt that "asks good questions" is not the same as a dialogue manager constrained by a clinical ontology that branches deterministically on chief complaint. Building the second, even a minimal version, is visibly more sophisticated to a judge who knows what SOCRATES is — and AYUSH judges will know. |
| **AYUSH/Dashavidha Pariksha history mode** | **Very high** | **Highest** | This is the one sub-problem that requires actual domain research most engineering teams will not do, because it requires understanding Prakriti, Vikriti, Agni, Koshtha, Ahara-Vihara, Nidana, Samprapti as *real diagnostic categories*, not just impressive vocabulary. It is also the one part of the PS that is **specific to this exact ministry** — a generic health-tech team building for a generic hospital PS would never build this. Getting it even partially right, and being honest about what's approximate vs. clinically validated, is the single highest-leverage differentiator available, because the judging panel (AIIA-affiliated) can tell instantly whether it's real or decorative. |
| Structured summary generator (Module C) | Medium | Medium | Mostly an engineering/prompting problem once A and B exist. Real, but not where the competition is won or lost. |
| **ABDM/ABHA/FHIR integration + DPDP-compliant consent (Module D)** | **Very high** | **High** | See Section D below — this is a real government-infrastructure integration, not a UI feature. Almost no team will do more than a fake "Connect ABHA" button. Doing the *sandbox* version honestly, and being explicit about what's real vs. simulated, is a second highest-leverage differentiator — for the opposite reason from Dashavidha Pariksha: it signals engineering maturity and understanding of India's actual digital-health rails, which is exactly what a ministry sponsor is trying to select for. |

**The strategic conclusion:** the bottom two rows (AYUSH-specific mode, ABDM sandbox integration) are where "top 1%" is actually earned, precisely because they are the two things a generic "SIH prototype factory" team — the ones cloning a GitHub Whisper+GPT template — will not bother building. Everything above them is necessary but not sufficient.

---

## Section C — The "1000 same prototypes" pattern: what losing looks like, specifically

Concretely, and without exaggeration, the median SIH26047 submission this cycle will look like:

- A React or Flutter frontend with a chat bubble UI.
- One LLM call (GPT-4o/Gemini/Claude via API) that asks "What are your symptoms?" and free-text summarizes the answer.
- Browser-native or Google STT for "voice input" — which does not meaningfully support Telugu/Hindi/regional-language ASR in noisy real conditions, and the team will not test it under noise because it's inconvenient to admit it doesn't work.
- A generic OCR call (Tesseract or a cloud OCR API) run once on a clean, printed sample prescription image — never tested against actual handwriting, because handwriting OCR accuracy is embarrassingly low and nobody wants to show that on stage.
- A slide that says "Integrated with ABDM/ABHA" with no working sandbox account, no client ID, and no actual API call ever made — because most teams will not discover that ABDM sandbox registration and M1 integration takes real setup time (see Section D) until it's too late to do it properly, and will bluff instead.
- No mention of Dashavidha Pariksha beyond a single slide bullet copy-pasted from the PS text itself, with no actual interview logic behind it — because building it requires research the team didn't do.
- A consent screen that is a checkbox, not an actual DPDP-Act-aligned data-handling architecture.

None of this is a strawman — it follows directly from what's *easy* to fake versus what requires real work, combined with the well-documented judging preference (Section A) for teams that visibly understand the problem. A judge who has seen 40 submissions that week can tell the difference between "we called an LLM API" and "we built a dialogue manager constrained by a clinical ontology" within about 90 seconds of a live demo.

---

## Section D — Real challenges and risks, stated brutally, not softened

Matching this project's own established standard (`docs/DAILY_PROTOCOL.md`'s honesty rule, `docs/INTERVIEW_NOTES.md`'s bug-disclosure pattern) — here is what will actually go wrong if this isn't planned for:

1. **Bhashini is still unverified against the live API.** `docs/INTERVIEW_NOTES.md` (Day 3) already states this plainly: no live `BHASHINI_USER_ID`/`BHASHINI_API_KEY` has ever been used in this environment. If the grand finale venue has no internet access to Bhashini's servers, or the pipeline ID has rotated (a named, existing risk in that same doc), the "multilingual voice" pillar of the whole pitch fails live. **Mitigation:** get real credentials and test against the live API *before* the finale, not during it; have a scripted fallback demo path (pre-recorded audio + cached response) that is explicitly labeled as a fallback, not passed off as live.

2. **ABDM/FHIR integration is a multi-week government-infrastructure project, not a hackathon feature.** Verified via this session's own research: ABDM sandbox registration + a real ABHA (M1) flow is reported to take **2–4 weeks**; a full HIP/HIU + consent-managed FHIR data exchange (M1+M2+M3) is reported at **6–12 weeks**, including NHA sandbox testing. **This means: promising full ABDM integration for a 36-hour build is not credible, and a judge who knows ABDM (plausible, given the sponsor) will catch it immediately.** The honest, winning move is the opposite of overclaiming: register for the ABDM sandbox *now* (before the finale, during prep time), get as far as a real M1/ABHA-ID creation-and-verification call working against the sandbox, and present that specific, bounded, real integration — with the rest of the FHIR/HIU pipeline shown as an honest, scoped "next step" architecture diagram, exactly like this project already does for Docker/HF-Spaces deployment in `README.md`. Partial-and-real beats complete-and-fake with this specific judging panel.

3. **Ayurvedic domain accuracy is a credibility cliff, not a feature to skip.** Nobody currently on this project has stated AYUSH/Ayurveda medical training. Building a Dashavidha Pariksha interview mode without a domain-knowledgeable reviewer risks either (a) getting it embarrassingly wrong in front of judges who are Ayurveda-affiliated by profession, or (b) it being so shallow (a few vocabulary terms in a dropdown) that it reads as decoration, which is arguably worse than not attempting it, because it signals the team didn't take the ministry's actual specialty seriously. **This is the single highest-priority open risk in this whole plan** — it needs either a real AYUSH-side advisor/mentor consulted before the finale, or a very deliberately scoped, honestly-labeled "starter" implementation (same pattern as `data/guidelines/seed_guidelines.json`'s `STARTER_SEED` labeling) that doesn't claim more clinical validity than it has.

4. **OCR on real handwritten prescriptions will underperform whatever the demo shows on a clean sample.** Already a documented, honest pattern in this repo (Day 2's OCR-preprocessing bug). The same discipline needs to apply here: test on genuinely messy samples before the demo, know the real failure rate, and be ready to state it if asked — "here's what it gets right, here's what it doesn't yet" is a stronger answer than a demo that quietly only ever shows the one sample that works.

5. **Time.** The idea-submission deadline is **30 September 2026** (extended from the originally-confirmed 20 September — see `docs/sih/SIH26047_Patient_Case_Taking_Software.md`'s 11 Sep 2026 update for the evidence) — a PPT + short demo video, not a finished product. The 36-hour build only happens *if shortlisted*, which the user has already correctly scoped ("if we get shortlisted then we will deploy it"). That means the immediate, real, near-term deliverable is **not** a finished MediKiosk platform — it's a compelling, honest, technically-credible 6-slide narrative plus a demo video that shows the *real, currently-working* slice (red-flag intake, Bhashini orchestration, OCR) without overclaiming the rest. Building the full four-module platform now, before shortlisting, is effort spent on the wrong artifact.

6. **CarePilot's current output shape doesn't match the PS's required output shape.** CarePilot today outputs a *triage level* (self-care/clinic/urgent/emergency) + referral. PS26047 wants a *structured physician-ready history summary* (chief complaint → HPI → past history → drug/allergy → family → personal → ROS → prior investigations), which is a different, richer output than a triage label. The triage level can be one *input* into that richer summary (e.g., as the red-flag/priority field), but reframing "CarePilot the triage bot" as "MediKiosk the history-intake platform" is a real architectural pivot, not a rename — this needs to be reflected honestly in the eventual `docs/DAILY_PROTOCOL.md` scope rewrite, not glossed over.

---

## Section E — The differentiation thesis: what to actually build, in priority order

Given Sections B–D, here is the bet, ranked by leverage-per-hour:

1. **Reframe the output contract first** (cheap, structural, unblocks everything else): extend `TriageDecision`/`ReferralResult`-equivalent schemas toward a `ClinicalHistorySummary` shape (chief complaint, HPI, past/drug/family/personal history, ROS, red-flag/priority field) that *subsumes* the current triage level rather than replacing it. This is the single change that turns "a triage bot" into "a history-intake platform" honestly, using code that already exists.
2. **Close the Bhashini live-verification gap** — get real credentials, make one real call, document the real result (success or the specific failure) in `docs/INTERVIEW_NOTES.md` the same way every other honest gap in this repo has been closed. This converts a claimed capability into a proven one.
3. **Build the minimal, honestly-scoped Dashavidha Pariksha mode** — not the full clinical framework, but a real, structured set of questions for the core categories (Prakriti, Agni, Koshtha at minimum), clearly labeled as a starting scaffold pending domain review, exactly like `seed_guidelines.json`'s `STARTER_SEED` pattern. Seek an actual AYUSH-side reviewer if at all possible before the finale — this is worth more effort than any other single item on this list.

   **Progress, 11 Sep 2026:** the ten-parameter reference data (`data/ayush/dashavidha_pariksha.json`) is no longer a single non-expert author's paraphrase — every gloss is now corroborated against real, cited literature (Zenodo, AyurVAID, JAIMS, CCRAS), and each parameter carries a real, load-bearing `acquisition_mode`: whether a self-service kiosk can actually ask the patient directly (`patient_self_report`/`mixed`), or whether it requires the physician's own physical examination and must stay a "not yet assessed" field on the summary (`physician_assessment_required` — Sara, Samhanana, Pramana specifically, since all three are traditionally assessed by inspection/palpation, the same Darshana/Sparshana methods behind Ashtavidha Pariksha, not by patient self-report). `app/agents/ayush_mode.py`'s new `kiosk_askable_parameters()`/`physician_only_parameters()` functions encode that split as real, tested code (`tests/test_ayush_mode.py`) — seven parameters go to a future kiosk interview, three go to the physician-facing summary as pending fields. This is precisely the difference this strategy calls out in Section C between "a slide bullet copy-pasted from the PS text" and something that survives a follow-up question from an AIIA-affiliated judge: *why doesn't your kiosk ask about Sara?* now has a real, correct, sourced answer instead of an awkward pause. Domain review by an actual AYUSH/BAMS-trained person is still the single largest open gap — this closes the "did the team even understand the difference between patient-reportable and physician-examined parameters" half of the risk, not the "is our clinical content actually correct" half.
4. **Register for the ABDM sandbox now and get one real M1/ABHA call working** — before the finale, not during it. Present it as a real, bounded proof of integration understanding, with the rest of the pipeline shown as an honest architecture diagram, not a false claim.
5. **Extend OCR from text extraction to structured extraction** (diagnoses, medications+dosages, lab values, chronological ordering) — `app/models/ocr.py` already does step one; step two is a real, scoped engineering task, not a rewrite.

   **Progress, 12 Sep 2026:** the last unwired piece of step two is done — `POST /case-intake/document` now accepts one or more uploaded documents (`documents: list[UploadFile]`, was a single `document` before) and runs them through `app/models/ocr.py`'s already-tested `build_document_timeline` before building `prior_investigations_summary`, so multiple prescriptions/lab reports/discharge summaries land chronologically organized (dated documents first, undated after, per that function's own stable-partition ordering — a best-effort ordering aid, not real date-sorting, exactly as its docstring states) rather than the previous one-document-per-case limit. Each document's summary section is labeled by filename once there's more than one, so a physician can tell which finding came from which upload; a single document (still the common case) is unaffected byte-for-byte. New regression test proves a document uploaded *second* but carrying a date gets reordered *first* in the resulting summary. The web UI (`web/app.js`) still only lets a patient pick one file at a time — sending it under the new plural field name works, but a real multi-file picker/preview is a separate, still-open UI task, not done here.
6. **Only after the above:** build the adaptive SOCRATES-style follow-up questioning in the dialogue manager. It's real differentiation but lower leverage than 1–4 because it's the sub-problem every competent team is most likely to attempt reasonably well on its own.

**What NOT to do:** don't build a fancier UI, don't add more LLM calls, don't chase "explainability" (SHAP/LIME) for this PS — that was a CarePilot-specific roadmap item for a different goal (GPREC placement prep) and has no judged relevance here. Resist scope creep in every direction Section A didn't name as judged.

---

## Section F — Staged plan matched to what's actually due when

- **Now → 30 Sept 2026 (idea/PPT stage, deadline extended — see Section D item 5):** the deliverable is the 6-slide AICTE-format PPT + demo video (per `docs/sih/README.md`'s process notes), not a finished product. Priorities: (1) the reframed output-contract pitch, (2) an honest demo of what's *actually* working today (red-flag intake, Bhashini orchestration — even if only tested against a fake backend, say so), (3) a credible, specific plan slide for Dashavidha Pariksha and ABDM that shows real research (the numbers in Section D), not hand-waving. This is where "understanding the real need better than 200 other teams" (Section A) is won or lost, and it costs zero deployment risk.
- **If shortlisted → pre-finale prep window:** this is when items 2–4 in Section E actually need to exist for real — live Bhashini test, ABDM sandbox M1 call, AYUSH-mode domain review. Not during the 36 hours.
- **Grand Finale (36 hours, if reached):** per Section A's most-repeated judging finding, the goal is a **narrow, stable, live-demoable core loop** — likely: voice/text intake → red-flag + adaptive history → structured summary → (mocked or sandbox-real) ABDM push — rather than attempting all four modules at full depth live. A judge rewards a smaller thing that works flawlessly over a bigger thing that breaks on stage, and that preference is documented, not assumed.

---

## Section G — Stress-test: would this survive a real follow-up question?

Applying this repo's own established bar (`docs/DAILY_PROTOCOL.md`'s fourth check: "would this survive a TCS Prime or SAP Labs interviewer's follow-up question, or does it only sound good until someone asks 'why'?") to the plan above, extended to an SIH judging panel and a technical hiring panel specifically:

- *"Is your ABDM integration real?"* → With Section E item 4 done: "Here's the real sandbox M1 call, here's the client ID, here's what we haven't built yet and why (Section D's 6–12 week timeline for full HIU integration is longer than a hackathon)." Survives. Without it: a slide claim collapses on the first follow-up.
- *"How do you know your Dashavidha Pariksha questions are clinically meaningful and not just vocabulary?"* → With Section E item 3 done honestly (labeled as a scaffold, ideally reviewed): "Here's what's domain-reviewed, here's what's still a starting point." Survives, because it doesn't overclaim. Decorative-only: collapses immediately in front of an AIIA-affiliated judge.
- *"What happens if Bhashini's API is down during the demo?"* → CarePilot's own existing engineering pattern (the graceful-503 discipline already in `app/main.py`, and the Day 6 fix already in this repo) is a real, provable answer, not a hypothetical one.
- *"Why should this beat the other 40 teams who also read this same PS?"* → The honest answer, if Section E is executed: *not* "we used AI" (everyone did), but "we did the two hard, unglamorous things — real AYUSH domain grounding and real ABDM sandbox integration — that most teams skipped because they're inconvenient, not because they're impossible."

---

## Honesty Ledger

- **Verified by this session directly:** PS26047's full text (`docs/sih/SIH26047_Patient_Case_Taking_Software.md`, sourced from a dated third-party scrape since `sih.gov.in` is unreachable here — see that doc's own provenance section); CarePilot's current code state (all claims about what exists today are grounded in files actually read this session).
- **Sourced from cited web search this session, treated as credible synthesis but not a primary SIH document:** SIH judging criteria and scoring structure (Section A); the ABDM sandbox integration timeline figures (Section D, item 2) — both are consistent across multiple independent sources found, which is why they're treated as reliable, but neither was fetched from a primary AICTE/ABDM document (both were egress-blocked from this environment on direct fetch attempts).
- **This project's own reasoning/judgment, explicitly not fact:** the entire competitive-differentiation thesis (Sections B, C, E, G) is analysis, not a guarantee — it's the strongest bet this reasoning process could construct from the verified inputs above, not a promise of a specific outcome.
- **Not done, and named as a real gap:** no actual AYUSH/Ayurveda domain expert has reviewed anything in this document or in CarePilot's code. That is the single largest unverified assumption this whole strategy leans on, and it's flagged here rather than smoothed over, matching every other honesty note in this project.
