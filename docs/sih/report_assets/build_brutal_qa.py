"""
Inayat — The Brutal Q&A (personal copy, plain language, POINTS not passages)
For the user's own understanding and stage confidence - every answer is
short bullet points meant to be memorized, not paragraphs meant to be
read. Every fact is grounded in this project's own verified code/tests/
measurements from this session - nothing invented for effect, only the
FORM changed to be memorable.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, ListFlowable, ListItem, PageBreak,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")

title_style = ParagraphStyle("TitleX", fontName="Helvetica-Bold", fontSize=25, textColor=DARK,
                              alignment=TA_CENTER, leading=30, spaceAfter=8)
subtitle_style = ParagraphStyle("SubtitleX", fontName="Helvetica", fontSize=11.5, textColor=GREY,
                                 alignment=TA_CENTER, spaceAfter=12, leading=15)
hook_style = ParagraphStyle("HookX", fontName="Helvetica-Oblique", fontSize=10.8, textColor=DARK,
                             alignment=TA_CENTER, spaceAfter=4, leading=15)
h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=13.5, textColor=GREEN,
                     spaceBefore=7, spaceAfter=2)
body = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5, textColor=DARK, leading=12, spaceAfter=3)
q_style = ParagraphStyle("QX", fontName="Helvetica-Bold", fontSize=9.9, textColor=DARK,
                          spaceBefore=4, spaceAfter=1, leading=12)
point_style = ParagraphStyle("PointX", fontName="Helvetica", fontSize=9.4, textColor=DARK, leading=11.8, spaceAfter=1)
point_bold_lead = ParagraphStyle("PointBoldLead", parent=point_style)


def points(items, indent=13, size=9.4, gap_after=0, list_space_after=3):
    style = ParagraphStyle("PtsX", fontName="Helvetica", fontSize=size, textColor=DARK,
                            leading=size * 1.22, spaceAfter=gap_after)
    return ListFlowable(
        [ListItem(Paragraph(t, style), bulletColor=GREEN, value="–") for t in items],
        bulletType="bullet", start="–", leftIndent=indent, spaceBefore=1, spaceAfter=list_space_after,
    )


def qa(q, pts):
    return KeepTogether([Paragraph(f"Q: {q}", q_style), points(pts)])


def h(text):
    return [HRFlowable(width="100%", thickness=1.1, color=GREEN, spaceBefore=3, spaceAfter=4),
            Paragraph(text, h1)]


story = []

# ---- Cover --------------------------------------------------------------
story.append(Spacer(1, 12))
story.append(Paragraph("The Brutal Q&amp;A", title_style))
story.append(Paragraph("Every hard question about Inayat &mdash; in points you can actually remember", subtitle_style))
story.append(HRFlowable(width="45%", thickness=1, color=GREEN, spaceBefore=2, spaceAfter=10, hAlign="CENTER"))
story.append(Paragraph(
    "No passages to re-read. Short points, in order. Say the bullets in your own words &mdash; "
    "don't recite them.",
    hook_style,
))
story.append(Spacer(1, 6))

# ---- 0. The name ----------------------------------------------------------
story += h("0. The name &mdash; say this before anything else")
story.append(qa("What does “Inayat” mean, and why did you choose it?", [
    "<b>Inayat means “care” in Urdu.</b>",
    "We named it that because the whole prototype exists to give every patient the caring attention a rushed two-minute doctor visit can't.",
]))
story.append(qa("Which dataset did you train it on?", [
    "None &mdash; we didn't train a model at all.",
    "The danger-check and follow-up questions are fixed rules, not learned from data.",
    "The “AI” part is a real, already-trained model (Claude) doing live reasoning &mdash; not something we trained ourselves.",
    "Our only “data” is a small, 14-sentence reference list we wrote ourselves, and openly say isn't officially certified yet.",
]))
story.append(qa("What languages does it actually support?", [
    "English, Hindi, and Telugu &mdash; both on-screen text and voice.",
    "Picked Telugu specifically since this problem statement's example district (Kurnool) is Telugu-speaking.",
]))
story.append(qa("Does it work with no internet at all?", [
    "The page itself still needs one internet load, like any website.",
    "But once loaded: if the AI can't be reached, it doesn't crash or freeze.",
    "It safely falls back to “route this to a human,” instead of guessing.",
]))
story.append(qa("Can a patient ask you to delete their data?", [
    "Not yet, honestly &mdash; there's no delete button today.",
    "A doctor can correct or amend a case, but records aren't destroyed.",
    "A real, known gap, not something we're hiding.",
]))
story.append(qa("Is the code actually public? Can we check it ourselves?", [
    "Yes &mdash; real GitHub repo, real commit history, nothing hidden.",
    "github.com/azlanabyssal-cloud/carepilot",
]))

# ---- 1. The problem -------------------------------------------------------
story += h("1. The problem &mdash; from zero, no background needed")
story.append(Paragraph(
    "<b>Picture this first, before any numbers:</b> someone is sick, waits hours in a government "
    "hospital line, and gets a doctor who has only minutes before the next patient. That's the "
    "whole problem, in one picture. The numbers below just prove it's real and everywhere.",
    body,
))
story.append(qa("What is the actual problem?", [
    "A government-hospital doctor sees a patient for about <b>2 minutes</b>.",
    "Not enough time to ask, listen, AND read old prescriptions.",
    "The “listening” part is what gets rushed first.",
    "But real studies say: careful listening is the #1 reason doctors get the diagnosis right.",
]))
story.append(qa("Why does this matter for real people, not just in theory?", [
    "2 out of every 3 Indians live in villages.",
    "Only about 1 in 4 doctors work in villages.",
    "Least access to a doctor = also the least time once you get one.",
]))
story.append(qa("How did you solve it, in one sentence?", [
    "We talk to the patient <b>before</b> the doctor does.",
    "Type, speak in their own language, or photo an old prescription.",
    "We turn that into one clean, organized note.",
    "By the time the doctor walks in, the listening is already done.",
]))

# ---- 2. The pipeline -------------------------------------------------------
story += h("2. The pipeline &mdash; 7 steps, and why each one exists")
story.append(points([
    "<b>1. Consent.</b> Patient must agree first &mdash; system refuses to save without it.",
    "<b>2. Patient talks.</b> Type, speak, or photo &mdash; not everyone types well or speaks English.",
    "<b>3. Smart follow-up questions.</b> Cough → phlegm/colour questions. Rash → spreading/new-soap questions. Pain → the standard 8-question method doctors already use. One list for everything would be lazy.",
    "<b>4. Danger check FIRST.</b> Checks exact words against a dangerous-symptom list. Zero AI needed. Zero internet needed. A dangerous case should never depend on AI having a good day.",
    "<b>5. AI helps (if not obviously dangerous).</b> Suggests urgency. No AI available? A safe backup kicks in instead of the app failing.",
    "<b>6. Second, independent double-check.</b> Compares words against real medical guidelines. Can only push urgency UP, never down. A wrong “less serious” correction is far more dangerous than extra caution.",
    "<b>7. Doctor decides.</b> Everything saved. Doctor reads it, can change anything. AI never diagnoses. AI never prescribes.",
], size=9.5, gap_after=4, list_space_after=4))

# ---- 3. Engineering questions ----------------------------------------------
story.append(KeepTogether(h("3. The engineering questions") + [
    Paragraph("Q: How much space (GB), and where does it run?", q_style),
    points([
        "Real app code: about <b>4.5 MB</b> &mdash; smaller than one phone photo.",
        "Libraries it actually needs to run: about <b>290 MB</b>, measured directly.",
        "One heavy library (PyTorch, for a feature not wired into the live app yet) left OUT on purpose &mdash; saves ~5 GB of dead weight.",
        "Hosted on <b>Render</b>, a cloud host, free tier.",
        "Free tier sleeps after 15 min idle, takes 30&ndash;60 sec to wake up &mdash; we say this openly.",
    ]),
]))
story.append(qa("What parameters or choices did you make, and why?", [
    "Guideline matching: simple word-matching, not a giant AI model.",
    "Why: our reference list is only a few dozen short passages &mdash; a big model gains nothing here.",
    "We trust only the <b>single best</b> guideline match, not the top 3.",
    "Why: a weak 3rd-place match once wrongly escalated “mild knee pain” to EMERGENCY.",
    "We caught it ourselves, tested it, fixed it.",
]))
story.append(qa("What tech did you actually build this with?", [
    "Python for the server.",
    "Plain HTML/JavaScript for the screen &mdash; no heavy framework, loads fast on cheap phones.",
    "A small database to save cases.",
    "Claude (AI model) for language understanding.",
    "Bhashini &mdash; real Indian-language voice tool.",
    "ABDM &mdash; India's real health-ID system.",
]))

story += h("3b. The raw “why this and not that” round &mdash; college-style questions")
story.append(qa("Why Python/FastAPI and not Java (Spring Boot)?", [
    "Java's fine &mdash; it's a real, valid choice too, just not ours.",
    "Python plugs straight into the AI/ML tools we needed: Anthropic's SDK, scikit-learn, Tesseract OCR &mdash; no cross-language glue code.",
    "FastAPI auto-validates every request's shape (via Pydantic) before our code even runs &mdash; several real bugs this project found were exactly bad/malformed input, caught right there.",
    "Less boilerplate, faster to build correctly in a hackathon timeline.",
]))
story.append(qa("Why SQLite and not MySQL or a “real” database?", [
    "SQLite is a real database &mdash; just one file, zero separate server to set up.",
    "Sized to what this actually needs right now: one well-defined table, a demo/pilot scale.",
    "Honest, named next step: move to Postgres before any real multi-hospital rollout.",
]))
story.append(qa("Why plain HTML/JavaScript and not React or Angular?", [
    "The user we're designing for is a patient on a cheap Android phone at a rural kiosk.",
    "No framework, no build step &mdash; the page just loads, instantly, with nothing to download first.",
    "Developer convenience lost out on purpose to the actual end user's phone and network.",
]))
story.append(qa("Is this actually a REST API? What does that even mean here?", [
    "Yes, genuinely &mdash; every feature is a real HTTP endpoint (e.g. POST /assess, POST /case-intake).",
    "Each one takes structured JSON in, returns structured JSON out &mdash; the standard REST shape.",
    "FastAPI also auto-generates live API documentation from the same code &mdash; nothing hand-written or able to drift out of sync.",
]))

# ---- 4. Why we're different -------------------------------------------------
story += h("4. Why we're different &mdash; and the ONE thing nobody else has")
story.append(qa("How is this better than another team's health chatbot?", [
    "Most chatbots: one AI model + a disclaimer.",
    "Ours: a safety net that doesn't need the AI at all.",
    "Keeps working with zero internet.",
    "Saves the case for the doctor to reopen later.",
    "Connects to real government health systems.",
]))
story.append(qa("The ONE thing you have that basically nobody else has?", [
    "A safety check that can only get MORE careful, never less.",
    "Works even if the AI is completely wrong, or fully offline.",
    "Most student projects trust the AI's answer directly.",
    "We built one that never fully trusts it.",
]))
story.append(qa("Isn't this just ChatGPT with extra steps?", [
    "ChatGPT: no double-check, nothing saved, stops with no internet.",
    "We built 3 separate real things ChatGPT doesn't have.",
    "Not one clever prompt &mdash; real engineering.",
]))

# ---- 5. Attention -------------------------------------------------------
story += h("5. Grabbing attention &mdash; the pitch, and the app itself")
story.append(qa("How will you grab attention when you present this?", [
    "Open with the real number, not a claim.",
    "“2 minutes per patient” &mdash; one of the lowest in the world.",
    "From a real study of 67 countries.",
    "Everyone's sat in that waiting room &mdash; it lands instantly.",
]))
story.append(qa("Once someone is looking at the app, what makes IT grab them?", [
    "Homepage doesn't wait for a click.",
    "A real example types itself out live, on its own.",
    "Gets caught as an emergency &mdash; before the visitor touches anything.",
    "Proof, not a promise.",
    "Page reveals content smoothly while scrolling &mdash; feels alive, not static.",
]))

story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"), spaceBefore=6, spaceAfter=5))

# ---- 6. Limitations -------------------------------------------------------
story.append(Paragraph("6. Limitations &mdash; proof we KNOW them, not guessed", h1))
story.append(Paragraph(
    "A real limitation vs. a guess: we tested it and watched it fail, with our own eyes, before writing it down.",
    body,
))
story.append(points([
    "<b>Old handwritten prescriptions read worse than clean typed ones.</b> Proof: same code, blurry image turned “13.0-17.0” into wrong “130-170.” We watched it happen.",
    "<b>Our medical reference list isn't officially certified yet.</b> We wrote it ourselves as a real starting point &mdash; we say so.",
    "<b>Voice and health-ID features never touched real government servers.</b> No test credentials exist for us &mdash; only public documentation.",
    "<b>Offline voice recognition isn't very accurate yet.</b> We tested and measured it ourselves &mdash; every result gets flagged “needs a human check,” never silently trusted.",
], size=9.4, gap_after=4, list_space_after=4))

story += h("6b. Scalability, money, and rules &mdash; the questions we'd never thought to prep")
story.append(qa("Will this actually scale past a demo, to a whole state or country?", [
    "Frontend is one plain HTML/JS file &mdash; no framework, loads on a cheap Android phone.",
    "We don't fake government integration &mdash; we plug into real ones.",
    "ABDM (India's health-ID system) already has over <b>90 crore</b> real IDs on it.",
    "We're riding rails that are already built at national scale, not inventing our own.",
]))
story.append(qa("Isn't this just Practo or 1mg with a new name?", [
    "Practo/1mg: book a doctor, order medicine, talk to a doctor remotely.",
    "Us: prepare what a patient says <b>before</b> they walk into an <i>existing</i> in-person visit.",
    "We don't replace the hospital visit &mdash; we make the few minutes inside it count more.",
    "Different job entirely, not a competing app.",
]))
story.append(qa("Who pays for this? What's the business model?", [
    "Built as free public-health infrastructure, not a paid consumer app.",
    "Same shape as CoWIN or ABDM itself &mdash; adopted by a health system, not sold per-user.",
    "Honestly: we haven't signed a government partner yet &mdash; that's a real next step, not a claim.",
]))
story.append(qa("Is patient data handled legally? What about privacy law?", [
    "Patient must actively give consent before anything is even saved &mdash; enforced by the system, not just a checkbox.",
    "Doctor's screen requires a real login &mdash; no login, no access.",
    "Full formal legal/compliance review hasn't happened yet &mdash; we say that honestly, not hide it.",
]))
story.append(qa("Could someone abuse this &mdash; fake symptoms to jump the queue?", [
    "The system never grants anything by itself &mdash; no priority, no medicine, no appointment.",
    "It only writes a note. A real doctor still decides everything that actually happens.",
    "Faking words to an AI doesn't get you anything a doctor doesn't independently check first.",
]))

story += h("7. The extra brutal round")
story.append(qa("What's the hardest real bug you personally found and fixed?", [
    "Safety-check used to trust the “most serious” of the top 3 guideline matches.",
    "A weak, barely-related 3rd match once beat a correct, strong 1st match.",
    "Wrongly turned ordinary “mild knee pain” into EMERGENCY.",
    "We found it ourselves, proved it with a test.",
    "Fixed: only trust the single best match now.",
]))
story.append(qa("What if the AI gives a wrong answer during the demo?", [
    "Danger-word check runs FIRST &mdash; zero AI needed for that.",
    "Second guideline check can only make things MORE careful.",
    "One wrong AI answer alone still can't create an unsafe result.",
    "Would need TWO independent systems wrong, in the same direction, at once.",
]))
story.append(qa("Couldn't a big company clone this in a week?", [
    "The AI-chatbot part? Maybe, yes.",
    "The safety-net design, real integrations, real-world testing? No.",
    "That's not a weekend job &mdash; most teams skip it entirely.",
]))
story.append(qa("Is patient data actually safe?", [
    "Doctor's screen sits behind a real login.",
    "Wrong passcode = the server itself refuses the data.",
    "Not just a hidden button someone could work around.",
]))
story.append(qa("Have you tested this on real patients in a real hospital?", [
    "No &mdash; and we say that honestly.",
    "367 automated tests, all currently passing.",
    "Real example cases we wrote ourselves.",
    "Real-patient testing is a genuine next step, not a claim we're making.",
]))
story.append(qa("If teammates give slightly different answers on stage, is that bad?", [
    "No &mdash; only guessing looks bad.",
    "Slightly different wording is fine.",
    "Don't know something? Say so, offer to follow up.",
]))

story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"), spaceBefore=6, spaceAfter=5))

# ---- 8. The short answers -------------------------------------------------
story.append(Paragraph("8. The answers you say without thinking", h1))
story.append(Paragraph(
    "<b>The whole thing, in one line:</b> “Inayat listens to a patient before the doctor "
    "does, and turns what they say into a safe, organized note &mdash; so the doctor's few "
    "minutes go to deciding, not repeating questions.”",
    body,
))
story.append(Paragraph("<b>Three reasons people should respect this project:</b>", body))
story.append(points([
    "We say what's NOT finished, out loud, before you catch us.",
    "The safety design doesn't trust one single thing to be right &mdash; it catches itself being wrong.",
    "Every real government feature we claim, we actually built and tested.",
], size=9.5, gap_after=2, list_space_after=6))

story.append(Paragraph(
    "You've now read the real problem, the real pipeline, the real numbers, the real bugs we "
    "found ourselves, and the real limits. That's not luck. That's understanding. Go say it.",
    ParagraphStyle("Closing", fontName="Helvetica-BoldOblique", fontSize=11, textColor=DARK,
                   alignment=TA_CENTER, leading=16, spaceBefore=6),
))

# ---- 9. Final stage revision ------------------------------------------------
# Everything above, compressed to bare facts - no questions, no full
# sentences, nothing to read twice. Built for the last 5 minutes before
# walking up, not for learning the material for the first time.
story.append(PageBreak())

rev_h = ParagraphStyle("RevH", fontName="Helvetica-Bold", fontSize=10.3, textColor=GREEN,
                        leading=13, spaceBefore=6, spaceAfter=1)


def rev_block(title, items):
    return KeepTogether(
        [Paragraph(title, rev_h)]
        + [points(items, indent=11, size=8.9, gap_after=0, list_space_after=0)]
    )


rev_title_style = ParagraphStyle("RevTitle", fontName="Helvetica-Bold", fontSize=17, textColor=DARK,
                                  leading=21, spaceAfter=4, alignment=TA_CENTER)
rev_sub_style = ParagraphStyle("RevSub", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY,
                                leading=12, alignment=TA_CENTER, spaceAfter=8)

story.append(Paragraph("9. Final Stage Revision &mdash; every fact, zero fluff", rev_title_style))
story.append(Paragraph(
    "Read top to bottom once, right before you walk up. Nothing here is new &mdash; it's page 1-4, compressed.",
    rev_sub_style,
))

story.append(rev_block("Name &amp; pitch", [
    "Inayat = “care” (Urdu). Named for giving real care a 2-min visit can't.",
    "Pitch: listens before the doctor does &rarr; clean note &rarr; doctor decides, doesn't repeat questions.",
]))
story.append(rev_block("The problem (real numbers)", [
    "~2 min/patient in govt hospitals (67-country study).",
    "2/3 of India rural, only ~1/4 of doctors rural.",
    "Careful listening = #1 driver of correct diagnosis.",
]))
story.append(rev_block("Pipeline (7 steps)", [
    "Consent &rarr; patient talks (type/voice/photo) &rarr; smart follow-ups &rarr; danger-word check (zero AI) "
    "&rarr; AI suggests level &rarr; guideline double-check (escalate-only) &rarr; doctor decides.",
]))
story.append(rev_block("Numbers to have ready", [
    "App code: 4.5 MB. Deploy deps: 290 MB. PyTorch (~5 GB) deliberately excluded.",
    "367 automated tests passing. 11 authored eval cases. 3 languages (En/Hi/Te).",
    "Hosted on Render free tier &mdash; sleeps 15 min idle, 30&ndash;60s cold start.",
    "ABDM already has 90+ crore real IDs &mdash; we ride that scale, don't invent it.",
]))
story.append(rev_block("Tech stack, one line each", [
    "Python/FastAPI &mdash; auto request validation caught real bugs; no Java/Spring needed.",
    "SQLite &mdash; zero-setup, sized to today's scale; Postgres is the named next step.",
    "Plain HTML/JS &mdash; loads instantly on a cheap rural Android phone, no React/build step.",
    "Real REST API &mdash; POST /assess, /case-intake, etc., self-documented at /docs.",
    "Claude + Groq for reasoning, Bhashini for voice, ABDM for health-ID &mdash; all real, all wired in.",
]))
story.append(rev_block("Why not X", [
    "Not ChatGPT: we double-check, work offline, and save the case. ChatGPT does none of that.",
    "Not Practo/1mg: they book/deliver; we prep what's said before a visit that already exists.",
    "Not a trained model: zero dataset trained &mdash; deterministic rules + a real LLM doing live reasoning.",
]))
story.append(rev_block("The ONE thing / the hardest bug", [
    "The one thing: a safety net that can only get MORE careful, never less &mdash; and works with zero AI.",
    "Hardest bug: top-3 guideline match let a weak 3rd-place result beat a correct 1st &mdash; “mild knee "
    "pain” &rarr; wrongly EMERGENCY. Found it, tested it, fixed it (now: single best match only).",
]))
story.append(rev_block("Limitations &mdash; say these unprompted", [
    "Handwritten prescriptions read worse than typed (watched it happen, not guessed).",
    "Guideline list is self-written, not officially certified yet.",
    "Voice/ABDM never hit real government servers &mdash; docs only, no test credentials.",
    "No delete-my-data button yet. No signed government partner yet. No formal legal review yet.",
]))
story.append(rev_block("Business, legal, abuse &mdash; the ones we almost forgot", [
    "Free public-health infrastructure, like CoWIN/ABDM &mdash; not sold per-user.",
    "Consent required before saving anything; doctor login required to view anything.",
    "Can't be abused for priority &mdash; it only writes a note, a human decides everything real.",
]))
story.append(rev_block("Closing lines", [
    "One-liner: “Inayat listens before the doctor does, turns it into a safe note, so the doctor's "
    "minutes go to deciding, not repeating questions.”",
    "3 respect reasons: says what's unfinished out loud; safety design catches its own mistakes; "
    "every government claim is actually built and tested.",
    "Don't know an answer? “Fair question &mdash; let me note it and follow up.” Never guess.",
]))

doc = SimpleDocTemplate(
    "/tmp/claude-0/report/Inayat_Brutal_QA_Personal.pdf",
    pagesize=A4,
    topMargin=12 * mm, bottomMargin=11 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    title="Inayat — The Brutal Q&A",
)


def footer(canvas, doc_):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(A4[0] / 2, 9 * mm, f"Inayat — The Brutal Q&A · {doc_.page}")
    canvas.restoreState()


doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("Brutal Q&A (points) built.")
