"""
Inayat — Judge Q&A Technical Deep-Dive
Companion to docs/sih/Inayat_Judge_Interview_Guide.pdf (the lay-audience
version). This one is for the team, going one level deeper: real design
parameters, real differentiation claims, and real adversarial questions,
every answer traced to an actual file/function/number in this repo -
verified by reading the code fresh, not recycled from memory.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, PageBreak,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")
LIGHT_RULE = colors.HexColor("#dddddd")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=22, textColor=DARK, spaceAfter=2, alignment=0)
subtitle_style = ParagraphStyle("SubtitleX", parent=styles["Normal"], fontName="Helvetica",
                                 fontSize=11, textColor=GREY, spaceAfter=10)
section_style = ParagraphStyle("SectionX", parent=styles["Heading1"], fontName="Helvetica-Bold",
                                fontSize=13, textColor=GREEN, spaceBefore=14, spaceAfter=6)
section_note_style = ParagraphStyle("SectionNoteX", parent=styles["Normal"], fontName="Helvetica-Oblique",
                                     fontSize=9, textColor=GREY, spaceAfter=8)
q_style = ParagraphStyle("QX", parent=styles["Normal"], fontName="Helvetica-Bold",
                          fontSize=10.3, textColor=DARK, spaceBefore=8, spaceAfter=2, leading=13)
a_style = ParagraphStyle("AX", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=9.7, textColor=DARK, spaceAfter=2, leading=13)
cite_style = ParagraphStyle("CiteX", parent=styles["Normal"], fontName="Helvetica-Oblique",
                             fontSize=8.2, textColor=GREY, spaceAfter=3, leading=10)
intro_style = ParagraphStyle("IntroX", parent=styles["Normal"], fontName="Helvetica",
                              fontSize=9.7, textColor=DARK, spaceAfter=4, leading=13)


def qa(question, answer, cite=None):
    flow = [Paragraph(f"Q: {question}", q_style), Paragraph(f"A: {answer}", a_style)]
    if cite:
        flow.append(Paragraph(cite, cite_style))
    return KeepTogether(flow)


def section(title, note=None):
    flow = [HRFlowable(width="100%", thickness=1, color=LIGHT_RULE, spaceBefore=2, spaceAfter=4),
            Paragraph(title, section_style)]
    if note:
        flow.append(Paragraph(note, section_note_style))
    return flow


doc = SimpleDocTemplate(
    "/tmp/claude-0/judge_prep/Inayat_Judge_QA_Technical_Deepdive.pdf",
    pagesize=A4,
    topMargin=18 * mm, bottomMargin=16 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    title="Inayat — Judge Q&A Technical Deep-Dive",
)

story = []

# ---- Title page -------------------------------------------------------
story.append(Paragraph("Inayat", title_style))
story.append(Paragraph("Judge Q&amp;A — Technical Deep-Dive · SIH26047, Patient Case-Taking Software", subtitle_style))
story.append(HRFlowable(width="100%", thickness=1.2, color=GREEN, spaceAfter=10))
story.append(Paragraph(
    "For the team, not for the judges. The companion lay-audience guide "
    "(<i>Inayat_Judge_Interview_Guide.pdf</i>) covers the simple version of these "
    "same points. This one goes one level deeper: the actual design "
    "parameters we chose and why, what is genuinely different from another "
    "team's LLM wrapper, and the adversarial questions a technically sharp "
    "judge will actually ask once they've opened the code, not just watched "
    "the demo. Every answer below was checked against the real file it "
    "cites while this was written, not recalled from memory - if a claim "
    "here can't be pointed at a real line of code, it isn't in here.",
    intro_style,
))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "Read this once, then close it. If you're reading from it in front of a judge, "
    "that's already the wrong signal - every answer here should be something "
    "you can say in your own words, because you actually built it.",
    ParagraphStyle("WarnX", parent=intro_style, fontName="Helvetica-BoldOblique", textColor=GREEN),
))

# ---- Section 1: Basic / orientation -----------------------------------
story += section("1. Basic — what a judge asks before opening any code")

story.append(qa(
    "What does this actually do, in one sentence?",
    "Turns what a patient says, types, speaks, or photographs before their visit into a "
    "structured, physician-ready history - Chief Complaint through Prior Investigations - "
    "plus an independent safety-net triage level, and hands both to the doctor to review, "
    "never to decide.",
))
story.append(qa(
    "Who is this actually built for?",
    "A patient in a 2-5 minute Indian primary-care consult (BMJ Open, 2017, 67-country "
    "consultation-length study - cited on our own landing page, not invented) and the "
    "physician who has to make a real decision inside that same window.",
))
story.append(qa(
    "What's the stack, and why so plain?",
    "FastAPI + Pydantic backend, one hand-written JS file for the frontend (no React/Vue, "
    "no build step), plain sqlite3 for persistence, scikit-learn TF-IDF for guideline "
    "retrieval, Anthropic Claude when a key is configured, deterministic Python everywhere "
    "a model isn't. Every one of those is a named, deliberate choice, not a default - see "
    "section 2.",
))
story.append(qa(
    "Does it diagnose or prescribe?",
    "No, structurally, not just by disclaimer: every schema field this pipeline outputs is "
    "either a triage level (self_care / clinic_visit / urgent / emergency) or a narrative "
    "history field. There is no diagnosis field, no medication-recommendation field, "
    "anywhere in app/schemas.py to fill in even by mistake.",
))

# ---- Section 2: Design parameters --------------------------------------
story += section("2. Design parameters — every \"why\" a judge points at a specific choice")

story.append(qa(
    "Why TF-IDF for guideline matching, not embeddings or a vector DB?",
    "The corpus is a few dozen short, domain-specific chunks - at that scale, exact/near-"
    "exact medical-term overlap (\"chest pain\", \"slurred speech\") is already a strong "
    "signal, and a transformer embedding model adds real latency and a heavy dependency "
    "for a retrieval problem this small doesn't need. We say in the code exactly when this "
    "stops being the right call: hundreds of documents, or paraphrased non-overlapping "
    "wording.",
    "app/agents/verify.py, GuidelineIndex docstring",
))
story.append(qa(
    "Why min_similarity = 0.2 for a guideline match?",
    "Measured, not picked: a genuinely relevant chunk scores ~0.6-0.7 cosine similarity in "
    "our corpus; a chunk sharing only one incidental word (\"mild\") scores ~0.09-0.10. "
    "0.2 sits cleanly between those two clusters, and that specific claim has its own "
    "named regression test, not just a comment.",
    "app/agents/verify.py: top_matches(); test_top_matches_filters_out_weak_incidental_overlap",
))
story.append(qa(
    "Why does guideline verification only ever escalate, never de-escalate a level?",
    "An imperfect TF-IDF match downgrading a real emergency is a far worse failure than "
    "staying cautious. Asymmetric on purpose - proven, not just claimed, in a test named "
    "exactly for that property.",
    "app/agents/verify.py: verify_triage_decision(); test_verify_never_deescalates_even_with_a_mild_top_match",
))
story.append(qa(
    "Why best-match-only (k=1), not top-3?",
    "We shipped top-3-most-severe-wins first, and it broke in live testing: a weak top-1 "
    "match on ordinary knee pain let a barely-above-threshold EMERGENCY chest-pain chunk "
    "ranked second silently override the correct verdict. Found by testing the live "
    "pipeline against ordinary phrasing, not a unit test in isolation - fixed to best-"
    "match-only the same day.",
    "app/agents/verify.py, verify_triage_decision docstring, 12 Sep 2026 entry",
))
story.append(qa(
    "Why a keyword scan AND an LLM AND a guideline check - isn't that redundant?",
    "Three independently-failing mechanisms on purpose: the keyword scan runs before any "
    "model call and can't have \"a bad day\"; the LLM covers paraphrase and nuance the "
    "fixed term list can't; the guideline check is a third, separately-computed opinion "
    "with a number the physician can actually see. All three would have to fail at once "
    "to miss a real emergency.",
    "app/agents/intake.py: scan_red_flags(); app/agents/triage.py; app/agents/verify.py",
))
story.append(qa(
    "Why SOCRATES, and why four more question templates on top of it?",
    "The PS text names SOCRATES specifically for pain. But SOCRATES doesn't fit a rash "
    "(\"does it radiate?\"), a cough, or a fever - asking every complaint the same eight "
    "pain questions is exactly the one-size-fits-all shortcut a clinically literate judge "
    "notices. So: real deterministic keyword classification into five categories (pain/"
    "general, respiratory, dermatological, GI, general-systemic), each with its own real "
    "clinical question set - not a pain template with nouns swapped.",
    "app/agents/socrates_intake.py: classify_complaint_category(), generate_followup_questions()",
))
story.append(qa(
    "Why build deterministic fallbacks instead of just returning an error with no API key?",
    "A rural kiosk with a dead connection, or a demo with no key configured, cannot 503 a "
    "sick patient. The fallback always proposes a fixed URGENT with confidence=0.0 - never "
    "a guessed self_care, never a guessed emergency - and every field it touches is "
    "honestly flagged requires_manual_triage=True downstream, never silently "
    "indistinguishable from a real judgment.",
    "app/agents/triage.py: DeterministicFallbackReasoningBackend; app/schemas.py: ReferralResult.requires_manual_triage",
))
story.append(qa(
    "Why regex-based extraction for prescriptions/labs, not a trained NER model?",
    "An in-house clinical NER model is out of reach in the time available, and a heuristic "
    "honestly labeled \"candidates for a human to confirm\" is safer than an ML-flavored "
    "black box that confidently gets a drug name wrong. We measured this ourselves: our "
    "own image-preprocessing step once turned \"AMOXICILLIN\" into \"ANTONICILLIN\" on a "
    "synthetic test image - kept in the docs, not hidden.",
    "app/models/ocr.py: extract_medication_mentions(), _preprocess() docstring",
))
story.append(qa(
    "Why offline ASR/TTS at all, given how inaccurate they measurably are?",
    "Zero-network, zero-cost availability at a PHC with no data connection beats hard-"
    "refusing voice entirely. We don't hide the ceiling: every offline-ASR transcript is "
    "flagged requires_manual_triage=True, and the module states its own measured accuracy "
    "floor from a controlled test, not a marketing claim.",
    "app/adapters/offline_speech.py module docstring",
))
story.append(qa(
    "Why plain sqlite3, not an ORM or a hosted database?",
    "One table, a fixed already-known shape, queried by primary key or a simple ORDER BY - "
    "exactly the case an ORM buys nothing for, while adding a dependency this scope "
    "doesn't need. Revisit the moment real multi-table relations or serious concurrent-"
    "write throughput actually show up - neither is true yet.",
    "app/db.py module docstring",
))

story.append(PageBreak())

# ---- Section 3: Differentiation ----------------------------------------
story += section("3. What's actually different from another team's prototype")

story.append(qa(
    "What's different from \"a GPT wrapper that asks about symptoms\"?",
    "Six concrete, checkable things: (1) an escalate-only safety net structurally separate "
    "from the LLM's own answer; (2) a deterministic red-flag scan that runs before any "
    "model call and can't be prompted out of an emergency; (3) every triage decision "
    "carries a real, quantified guideline match (source + cosine-similarity score) a "
    "physician can audit, not a black-box verdict; (4) it keeps working with zero API key "
    "and zero internet - a pure LLM wrapper simply stops; (5) real government-scheme "
    "integration (ABDM ABHA creation, AYUSH Dashavidha Pariksha) that a generic chatbot "
    "has no reason to build; (6) a persisted case record a physician can actually reopen "
    "at consult time - a chat window is not a patient record.",
))
story.append(qa(
    "In the world of ChatGPT, why would anyone use this instead?",
    "Open ChatGPT and describe your symptoms: there is no independent check on its own "
    "answer, nothing persists for the physician to reopen, no quantified evidence trail, "
    "no offline fallback if the connection drops, no ABDM/AYUSH integration, and its "
    "safety behaviour can be prompt-engineered around because it's one model with no "
    "external check. We built one narrow job - safe triage-support before a 2-minute "
    "consult - several structurally independent ways, so a bad model day, a missing key, "
    "or a clever prompt doesn't silently produce a wrong triage level.",
))
story.append(qa(
    "Isn't \"AI is a scribe, never the decision-maker\" just a slide, not real?",
    "It's a field, not a slide: every summary defaults to is_reviewed_by_physician=False "
    "and there is a real accept/amend/reject endpoint behind a real login gate - a "
    "physician who never opens that screen leaves every case sitting as an unreviewed "
    "draft, visibly, not silently promoted to final.",
    "app/schemas.py: ClinicalHistorySummary.is_reviewed_by_physician; POST /cases/{id}/review",
))
story.append(qa(
    "What real government systems does this actually touch, not just name-drop?",
    "Bhashini (MeitY's own ASR/translation/TTS service) with the real two-step pipeline-"
    "config-then-inference request shape; ABDM's real V3 sandbox ABHA-enrollment flow with "
    "genuine RSA-OAEP encryption matching its published cipher spec (proven by a test that "
    "decrypts our own outgoing request with a real generated keypair). Both are honestly "
    "labeled: built and orchestration-tested, never confirmed against a live server, "
    "because neither service's live credentials exist in our build environment.",
    "app/adapters/bhashini.py; app/adapters/abdm.py",
))

# ---- Section 4: Brutal / adversarial ------------------------------------
story += section("4. Brutal — the questions a judge asks after reading the code, not the slide",
                  "Every answer here concedes the real limit first. That is the point: a rehearsed "
                  "deflection is what actually loses trust in the room.")

story.append(qa(
    "Your \"4/4 emergency recall, 4/4 accuracy\" - is that a real statistic?",
    "It's a real fraction, deliberately never shown as a percentage - we changed that "
    "ourselves after a live user pointed out a 4-case sample dressed up as \"100%\" was "
    "misleading. Our authored 11-case eval set has 5 true emergencies; without a live "
    "ANTHROPIC_API_KEY only the 4 red-flag-catchable ones are evaluable at all, and the "
    "UI says so rather than hiding the skip.",
    "data/evaluation/test_cases.json; web/app.js: computeSafetyMetricsCounts()",
))
story.append(qa(
    "Is your guideline corpus real ICMR/WHO content?",
    "No - stated in the module's own docstring: \"a starter set written for this repo, not "
    "a verified extract from an official ICMR/WHO document.\" The retrieval mechanism is "
    "real and tested; sourcing a vetted corpus behind it is the next real step, not "
    "something we're presenting as already done.",
    "app/agents/verify.py module docstring; data/guidelines/seed_guidelines.json",
))
story.append(qa(
    "TF-IDF isn't reasoning - is \"Guideline-Verification Agent\" overselling it?",
    "It's lexical similarity, not clinical reasoning, and we'll say that before you ask. "
    "What it buys is a genuinely independent, auditable second check with a real number "
    "attached - worth more at this corpus size than a bigger model that just agrees with "
    "itself.",
))
story.append(qa(
    "You mention a Groq backend - is multi-vendor failover actually live?",
    "No. It's built and tested behind the same interface as the Anthropic backend, but the "
    "live app's automatic fallback chain today is Anthropic to deterministic only - Groq "
    "is not wired into app/main.py. We're not claiming a failover path we haven't shipped.",
    "app/agents/groq_backends.py (tested, not called from app/main.py)",
))
story.append(qa(
    "Has your ABDM integration ever actually talked to a real ABDM server?",
    "No, and the code says so: no sandbox credentials exist in this environment, so the "
    "request/response shapes are transcribed from public documentation, not confirmed "
    "live. What IS verified without a live server: the RSA-OAEP encryption is "
    "cryptographically correct - a test generates a real keypair, serves the public half "
    "back to our adapter, and decrypts our adapter's actual outgoing ciphertext with the "
    "private half to recover the exact original plaintext.",
    "app/adapters/abdm.py module docstring; tests/test_abdm.py",
))
story.append(qa(
    "What actually happens on a real handwritten prescription, not your clean demo image?",
    "Measurably worse, and we tested it ourselves rather than assume: the identical "
    "extraction regex against a low-resolution rendering corrupted \"13.0-17.0\" into "
    "\"130-170\" - a wrong reference range, faithfully reported because the regex did "
    "exactly what it was asked. That's exactly why every extracted field is documented as "
    "a candidate for a human to confirm, never a source of truth on its own.",
    "app/models/ocr.py: extract_lab_values() docstring, real measured Tesseract comparison",
))
story.append(qa(
    "Physician login is one shared passcode - what about per-doctor accounts or audit logs?",
    "Real, named gap: one shared staff passcode, in-memory session tokens with no "
    "expiry, no per-physician identity. Correct scope for an MVP demo; the first thing "
    "that has to change before any real deployment, and we say that ourselves rather than "
    "wait for a judge to find it.",
    "app/main.py: _PHYSICIAN_SESSIONS, require_physician_session()",
))
story.append(qa(
    "Does the referral engine pick the actual nearest hospital?",
    "No - the first entry in a curated, static directory for that triage level, not real-"
    "time geolocation ranking. Stated in the referral agent's own docstring as an honest "
    "MVP scope, not implied as something smarter.",
    "app/agents/referral.py: run_referral()",
))
story.append(qa(
    "Is voice input/output actually good enough for a real patient?",
    "Input: real and working end-to-end, but PocketSphinx's accuracy on genuine speech is "
    "measurably modest - we flag every offline-ASR result requires_manual_triage=True "
    "rather than trust it silently. Output: intelligible but mechanical-sounding by "
    "construction - espeak-ng is a formant synthesizer, not neural TTS - and we checked "
    "for a better offline model before claiming otherwise: it exists (Piper), but its "
    "voice files live on huggingface.co, which is blocked in our build environment.",
    "app/adapters/offline_speech.py module docstring, VOICE-QUALITY CAVEAT",
))
story.append(qa(
    "If I feed deliberately broken input - invisible Unicode, double spaces, weird whitespace - does it break?",
    "We went looking for exactly that, repeatedly, across this build: six-plus real "
    "invisible-Unicode and whitespace bugs found and fixed across intake, triage parsing, "
    "and history drafting - each with a regression test proving it failed before the fix "
    "was written. Not a claim; it's in the commit history and the test suite.",
    "app/schemas.py: _visible_length(); app/agents/intake.py: scan_red_flags(); app/agents/triage.py: _strip_invisible()",
))
story.append(qa(
    "Bottom line - what would you tell a judge who says \"this is just another AI symptom checker\"?",
    "Open the code with them. A symptom checker has one model and a disclaimer. This has a "
    "deterministic safety net the model can't override, a quantified evidence trail, "
    "government-scheme integration, a persisted physician record, and it keeps working "
    "when the model doesn't - and every one of those claims is sitting in a file we can "
    "point to, not a slide.",
))

doc.build(story)
print("PDF built.")
