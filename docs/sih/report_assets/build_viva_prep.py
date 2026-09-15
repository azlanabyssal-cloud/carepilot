"""
Inayat -- Viva / Q&A Prep Sheet: every fact worth remembering about the
prototype, the problem, and the solution, in one place. Every claim
here is grounded in this project's own verified code, tests, or
measurements from this session -- nothing invented for effect.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, ListFlowable, ListItem,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")

title_style = ParagraphStyle("TitleX", fontName="Helvetica-Bold", fontSize=23, textColor=DARK,
                              alignment=TA_CENTER, leading=28, spaceAfter=6)
subtitle_style = ParagraphStyle("SubtitleX", fontName="Helvetica", fontSize=11, textColor=GREY,
                                 alignment=TA_CENTER, spaceAfter=10, leading=14)
h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=13.5, textColor=GREEN, spaceBefore=7, spaceAfter=3)
q_style = ParagraphStyle("QX", fontName="Helvetica-Bold", fontSize=9.8, textColor=DARK, spaceBefore=4, spaceAfter=1, leading=12)
body = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5, textColor=DARK, leading=13, spaceAfter=3)


def h(text):
    return [HRFlowable(width="100%", thickness=1.1, color=GREEN, spaceBefore=3, spaceAfter=4), Paragraph(text, h1)]


def points(items, size=9.3, gap_after=1, indent=13):
    style = ParagraphStyle("PtsX", fontName="Helvetica", fontSize=size, textColor=DARK, leading=size * 1.25, spaceAfter=gap_after)
    return ListFlowable(
        [ListItem(Paragraph(t, style), bulletColor=GREEN, value="–") for t in items],
        bulletType="bullet", start="–", leftIndent=indent, spaceBefore=1, spaceAfter=3,
    )


def qa(q, pts):
    return KeepTogether([Paragraph("Q: " + q, q_style), points(pts)])


story = []

# ---- Cover ------------------------------------------------------------
story.append(Spacer(1, 6))
story.append(Paragraph("Viva Prep — Everything to Remember", title_style))
story.append(Paragraph("The prototype, the problem, and the solution — one page per topic, plain language", subtitle_style))
story.append(HRFlowable(width="45%", thickness=1, color=GREEN, spaceBefore=2, spaceAfter=10, hAlign="CENTER"))

# ---- 1. The basics ---------------------------------------------------
story += h("1. The basics — say these without hesitating")
story.append(points([
    "<b>Team:</b> SANKALP.",
    "<b>Prototype:</b> INAYAT — means “care” in Urdu. Named that on purpose: it exists to give every patient the caring attention a rushed visit can't.",
    "<b>Problem Statement:</b> SIH26-CC-0032 — Patient Case-Taking Software.",
    "<b>What it is, in one line:</b> a tool that turns what a patient says (typed, spoken, or an old prescription photo) into a clean, structured history the doctor reads before walking in — with safety checks that run before anything else.",
]))

# ---- 2. The problem ---------------------------------------------------
story += h("2. The problem — in plain words")
story.append(points([
    "A doctor in an Indian OPD gets about <b>two minutes</b> with each patient.",
    "But <b>70–80%</b> of a correct diagnosis comes from the patient's history alone — before any test.",
    "So the two minutes doctors have least of is exactly the two minutes that matters most.",
    "Patients bring torn, unstructured old prescriptions no one has time to read properly.",
    "Elderly, rural, and low-literacy patients get left out of most digital health tools.",
    "Doctors end up asking the same basic questions over and over, wasting the little time they have.",
]))

# ---- 3. The solution ---------------------------------------------------
story += h("3. The solution — five things that make it real")
story.append(points([
    "<b>Multilingual voice</b> — English, Hindi, Telugu, both text and speech, so language is never a barrier.",
    "<b>Adaptive questioning</b> — a real follow-up question engine (SOCRATES framework): a cough gets asked about phlegm, a rash gets asked about spread. One question at a time, always skippable.",
    "<b>Safety-first triage</b> — a red-flag scanner runs before anything else, catching genuine emergencies (chest pain, unconsciousness, severe bleeding) instantly, with zero AI call needed.",
    "<b>Smart document reading</b> — OCR reads old prescriptions and lab reports, pulls out medicines, dates, diagnoses, and flags abnormal lab values against the report's own stated range.",
    "<b>AYUSH-aware history</b> — real Dashavidha Pariksha (the ten-fold Ayurvedic examination) questions for Ayurvedic consultations, not just “Ayurveda” relabeled onto a generic form.",
]))

# ---- 4. How it's built ---------------------------------------------------
story += h("4. How it's built — the real stack")
story.append(points([
    "<b>Frontend:</b> plain HTML/CSS/JavaScript, no framework, no build step — loads fast on a cheap phone with a weak connection.",
    "<b>Backend:</b> Python, FastAPI, SQLite.",
    "<b>Reasoning:</b> Claude (Anthropic) or Groq for live language reasoning, backed by our own TF-IDF clinical-guideline safety check that runs independently of either.",
    "<b>OCR:</b> Tesseract, reading prescriptions/lab reports into plain text, then regex-based extraction (medications, dates, diagnoses, lab values).",
    "<b>Voice:</b> Bhashini (India's government ASR/TTS service) live, with a fully offline fallback (PocketSphinx + espeak-ng) when Bhashini isn't reachable.",
    "<b>Health ID:</b> ABDM (Ayushman Bharat Health Account) — real OTP-based linking against India's actual government health-ID API, not a mock.",
    "<b>The agent pipeline (real module names, not a diagram invented for slides):</b> intake.py (red-flag scan) → socrates_intake.py (follow-up questions) → history_intake.py (structures the narrative) → triage.py (proposes a priority level) → verify.py (guideline-evidence check, can escalate) → referral.py (decides if a doctor must manually review).",
]))

# ---- 5. The numbers ---------------------------------------------------
story += h("5. Numbers to have ready")
story.append(points([
    "<b>70–80%</b> — share of a correct diagnosis that comes from history alone (classical clinical teaching).",
    "<b>~2 minutes</b> — average Indian primary-care consultation length (BMJ Open, 2017, 67-country study).",
    "<b>3 languages</b> — English, Hindi, Telugu (Telugu chosen since the example district, Kurnool, is Telugu-speaking).",
    "<b>388 automated tests</b>, all passing, zero known regressions as of today.",
    "<b>Zero</b> — the API cost of every safety-critical check (red-flag scan, guideline evidence, priority escalation).",
    "<b>10</b> — the Dashavidha Pariksha, the real ten-fold Ayurvedic examination framework the AYUSH questions are checked against.",
]))

story.append(qa("What's the real differentiator, if you only get one line?", [
    "“Every safety check — the emergency catch, the priority level, the guideline citation — runs with zero API cost and keeps working even if the AI service is down. That's what lets this scale to a real, high-volume government hospital, not just stay a demo.”",
]))

# ---- 6. Tough questions ---------------------------------------------------
story += h("6. Tough questions, short honest answers")
story.append(qa("Why not just let the patient write it on paper?", [
    "Paper doesn't catch danger — nothing happens until a doctor reads it. This checks the moment it's typed or spoken.",
    "Not everyone can write it well — elderly, low-literacy, or non-native-language patients. This lets them just speak or show a photo instead.",
    "Paper is raw notes — the doctor still has to organize it themselves, in the two minutes they don't have. This hands it over already organized the way a doctor thinks.",
]))
story.append(qa("What dataset did you train it on?", [
    "None — no model was trained. The red-flag scan and follow-up questions are fixed rules, not learned from data.",
    "The reasoning is a real, already-trained model (Claude/Groq) doing live reasoning — not something built from scratch.",
    "The only “data” is a small clinical-guideline reference set written and checked by the team — openly not clinically certified yet.",
]))
story.append(qa("Does it work fully offline?", [
    "The page itself needs one internet load, like any website.",
    "Once loaded: if the AI can't be reached, it doesn't crash — it safely falls back to a conservative, evidence-gated priority level instead of guessing.",
    "Voice has a real offline fallback (PocketSphinx/espeak-ng) if the live government ASR service is unreachable.",
]))
story.append(qa("Can a patient delete their data?", [
    "Not yet, honestly — there's no delete button today. A doctor can correct or amend a case, but records aren't destroyed.",
    "A real, known gap — not hidden.",
]))
story.append(qa("Is the code public? Can we check it?", [
    "Yes — real GitHub repo, real commit history: github.com/azlanabyssal-cloud/carepilot",
]))
story.append(qa("Why does a mild symptom show a serious-sounding priority?", [
    "It only raises the level when it finds real evidence (a matched clinical guideline, shown on screen with its similarity score) — with no match, it stays cautious rather than guessing, and never quietly lowers a level on a weak match.",
    "That's a deliberate safety design, not a confidence score.",
]))
story.append(qa("Isn't this just Practo or 1mg?", [
    "No — those book appointments and sell medicine. This is a pre-visit history-taking and safety-triage tool that hands a doctor a ready summary before the patient even walks in — a different problem entirely.",
]))
story.append(qa("Who pays for this? What's the business model?", [
    "Built for government/public-hospital OPD deployment first — the zero-API-cost fallback exists specifically so it works without a recurring per-query AI bill, the real constraint a public hospital faces.",
]))
story.append(qa("What about the Digital Personal Data Protection Act, 2023?", [
    "Consent is real and enforced — checked client-side for a clear message, and again server-side (the request is rejected without it), not just a UI checkbox.",
]))

# ---- 7. Honest gaps ---------------------------------------------------
story += h("7. Honest gaps — say these plainly if asked, don't dodge")
story.append(points([
    "Every result is labeled “AI-drafted, not yet reviewed by a physician” — by design, a doctor always makes the final call, this never replaces that.",
    "No delete-my-data button yet — a real, known gap, not hidden.",
    "A separate CV image-triage model exists in the codebase (tested against synthetic images) but isn't wired into the live endpoints yet — named honestly as a build-roadmap item, not claimed as shipped.",
    "OCR'd document findings (medications, abnormal labs) are shown to the doctor but don't yet change the priority_level automatically — the physician remains the backstop for that judgment either way.",
    "The clinical-guideline reference set is small and team-written, openly not a certified medical database.",
]))

story.append(Spacer(1, 4))
story.append(HRFlowable(width="100%", thickness=1.1, color=GREEN, spaceBefore=3, spaceAfter=4))
story.append(Paragraph("8. If you forget everything else — the ten lines", h1))
story.append(points([
    "Team SANKALP. Prototype INAYAT — “care” in Urdu. PS SIH26-CC-0032, Patient Case-Taking Software.",
    "A doctor gets two minutes; history gives 70–80% of the diagnosis. That's the real problem.",
    "Three ways in: type, speak (EN/HI/TE), or photograph an old prescription.",
    "Adaptive follow-up questions, a real safety-first red-flag scanner, OCR with abnormal-lab flagging, AYUSH-aware history — not just a chatbot.",
    "Every priority level is evidence-gated: a matching guideline can raise it, a weak match never lowers it.",
    "Zero API cost for every safety-critical check — keeps working even if the AI service is down.",
    "Real ABDM health-ID linking, real OTP, real government API — not a mock.",
    "388 automated tests passing. Code is public on GitHub.",
    "Every AI-drafted summary says so on screen — helps the doctor decide, never replaces the doctor.",
    "Known gaps said out loud: no data-deletion yet, CV model not wired in yet, OCR doesn't drive priority yet.",
], size=9.6, gap_after=2))

doc = SimpleDocTemplate(
    "Inayat_Viva_Prep.pdf", pagesize=A4,
    leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=13 * mm,
    title="Inayat Viva Prep", author="Team SANKALP",
)
doc.build(story)
print("built")
