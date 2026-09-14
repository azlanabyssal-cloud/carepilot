"""
Inayat — Team Viva Confidence Sheet
Short, plain-language, for the team itself (not judges) - so anyone on
the team can answer a "sir/madam" question about the problem or the
prototype without freezing, without jargon, and without guessing.
Every fact here is grounded in the same verified numbers/code used in
this project's other SIH documents this session - simplified in
language, not in truth.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
    KeepTogether, PageBreak, ListFlowable, ListItem,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")
LIGHTGREEN = colors.HexColor("#eaf5ee")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("TitleX", fontName="Helvetica-Bold", fontSize=26, textColor=DARK,
                              alignment=TA_CENTER, leading=31, spaceAfter=8)
subtitle_style = ParagraphStyle("SubtitleX", fontName="Helvetica", fontSize=12, textColor=GREY,
                                 alignment=TA_CENTER, spaceAfter=14, leading=16)
hook_style = ParagraphStyle("HookX", fontName="Helvetica-Oblique", fontSize=11.5, textColor=DARK,
                             alignment=TA_CENTER, spaceAfter=4, leading=16)

h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=14.5, textColor=GREEN,
                     spaceBefore=14, spaceAfter=6)
body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.3, textColor=DARK,
                       leading=15, spaceAfter=7)
bullet_body = ParagraphStyle("BulletBody", parent=body, spaceAfter=4)
q_style = ParagraphStyle("QX", fontName="Helvetica-Bold", fontSize=10.5, textColor=DARK,
                          spaceBefore=9, spaceAfter=2, leading=14)
a_style = ParagraphStyle("AX", fontName="Helvetica", fontSize=10.3, textColor=DARK,
                          leading=14.5, spaceAfter=2)
note_style = ParagraphStyle("NoteX", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY,
                             leading=13, spaceAfter=6)
step_num_style = ParagraphStyle("StepNum", fontName="Helvetica-Bold", fontSize=13, textColor=GREEN,
                                 alignment=TA_CENTER)
step_body_style = ParagraphStyle("StepBody", fontName="Helvetica", fontSize=9.8, textColor=DARK, leading=13.5)


def bullets(items, style=bullet_body):
    return ListFlowable(
        [ListItem(Paragraph(t, style), bulletColor=GREEN, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=14, spaceBefore=2, spaceAfter=8,
    )


def qa(q, a):
    return KeepTogether([Paragraph(f"Q: {q}", q_style), Paragraph(f"A: {a}", a_style)])


def h(text):
    return [HRFlowable(width="100%", thickness=1.2, color=GREEN, spaceBefore=4, spaceAfter=5),
            Paragraph(text, h1)]


story = []

# ---- Cover / opening --------------------------------------------------
story.append(Spacer(1, 20))
story.append(Paragraph("Before You Go On Stage", title_style))
story.append(Paragraph("Inayat &mdash; what to actually say when a sir or madam asks you anything", subtitle_style))
story.append(HRFlowable(width="45%", thickness=1, color=GREEN, spaceBefore=2, spaceAfter=14, hAlign="CENTER"))
story.append(Paragraph(
    "You don't need to memorize this page. You need to actually understand five things. "
    "Once you understand them, any question a judge or teacher asks is just a different way "
    "of asking about one of these five &mdash; and you'll already know the answer.",
    hook_style,
))
story.append(Spacer(1, 10))

# ---- Section: the one-line pitch ---------------------------------------
story += h("1. Say this first, always")
story.append(Paragraph(
    "“<b>Inayat listens to a patient before the doctor sees them, and turns what they say "
    "into a clean, organized note for the doctor &mdash; so the doctor doesn't waste their "
    "few minutes asking the same questions again.</b>”",
    ParagraphStyle("Pitch", fontName="Helvetica-Bold", fontSize=11.5, textColor=DARK,
                   leading=17, spaceAfter=8, leftIndent=10, rightIndent=10),
))
story.append(Paragraph(
    "Say this line, slowly, before anything else. It answers “what is your project” "
    "completely. Everything else in this document is just backup for when they ask more.",
    note_style,
))

# ---- Section: the real problem -----------------------------------------
story += h("2. Why this matters (real numbers, not opinions)")
story.append(Paragraph("Say these three facts if anyone asks “why does this matter” or “what's the real problem here”:", body))
story.append(bullets([
    "In a normal government hospital in India, a doctor spends about <b>2 minutes</b> with each patient. That's one of the shortest consultation times in the world &mdash; a real study looked at 67 countries and found this.",
    "About two-thirds of India's people live in villages, but only around <b>27% of doctors</b> work there. Villages have far fewer doctors than they have people.",
    "Doctors have said for years that just <b>listening carefully</b> to a patient solves most of the puzzle &mdash; real studies say a good history alone leads to the right diagnosis <b>most of the time</b>, before any test is even done.",
]))
story.append(Paragraph(
    "Put together: doctors don't have time to listen properly, but listening properly is the "
    "single most important thing they could do. That gap is exactly what Inayat fills.",
    body,
))

# ---- Section: how it works ----------------------------------------------
story += h("3. How it actually works &mdash; 4 simple steps")
steps = [
    ("1", "The patient talks", "They type, speak in their own language, or show a photo of an old prescription. No forms to fill."),
    ("2", "We check for danger first", "Before anything clever happens, we check their words against a list of dangerous symptoms (like “chest pain” or “can't breathe”). This check needs no AI at all &mdash; it always works, even with zero internet."),
    ("3", "We organize what they said", "If it's not an emergency, the system asks a few smart follow-up questions (different questions for a cough than for a rash), then writes it all into a proper doctor-style note."),
    ("4", "The doctor decides", "The doctor opens it, reads it, changes anything they want, and only then is it final. The AI never diagnoses. It never prescribes."),
]
step_rows = []
for num, title, desc in steps:
    step_rows.append([
        Paragraph(num, step_num_style),
        Paragraph(f"<b>{title}</b><br/>{desc}", step_body_style),
    ])
step_table = Table(step_rows, colWidths=[28, 440])
step_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#dddddd")),
]))
story.append(step_table)

# ---- Section: what makes us different ------------------------------------
story += h("4. “Why not just use ChatGPT?”")
story.append(Paragraph("This question WILL come. Here is the real answer, in three parts:", body))
story.append(bullets([
    "<b>It double-checks itself.</b> Before trusting the AI's answer, we run a second, separate check against real medical guidelines. If that second check disagrees and thinks it should be MORE serious, it overrides the AI. It can never make things look less serious &mdash; only more careful.",
    "<b>It still works with no internet and no AI at all.</b> If the AI service is down, the system doesn't crash or refuse &mdash; it falls back to a safe, honest “please have a doctor check this” answer instead of guessing.",
    "<b>It remembers.</b> ChatGPT forgets everything after the chat ends. We save the patient's case so the doctor can open it again at the actual appointment.",
]))

# ---- Section: rapid-fire Q&A --------------------------------------------
story += h("5. Quick-fire questions &mdash; read this twice before you go up")
story.append(qa(
    "Is this an AI diagnosis app?",
    "No. It never tells the patient what disease they have, and never suggests medicine. It only writes a summary. The doctor decides everything.",
))
story.append(qa(
    "What if the AI misses something dangerous?",
    "It can't, easily &mdash; the dangerous-word check runs first and needs no AI. Only after that check clears does the AI even get involved.",
))
story.append(qa(
    "What if there's no internet during the demo?",
    "The system is built to keep working anyway &mdash; with a safe, honest fallback for every AI-dependent step, not a crash.",
))
story.append(qa(
    "Did you actually test this, or is it just a nice idea?",
    "We wrote 358 automated tests that run our own code and check the results &mdash; every one currently passes. We also ran it against 11 real example patient cases.",
))
story.append(qa(
    "Is patient data safe?",
    "The doctor's screen is behind a real login &mdash; no login, no data, enforced by the server itself, not just hidden by a button.",
))
story.append(qa(
    "What's NOT finished yet? (Say this honestly &mdash; it makes you MORE believable, not less.)",
    "Our medical reference list is a starting version we wrote ourselves, not yet officially certified. We haven't tested our voice/health-ID features against the real government servers, only against their public documentation. Old handwritten prescriptions are harder for the system to read than a clean typed one.",
))
story.append(qa(
    "What tech did you actually use?",
    "Python for the backend, plain HTML/JavaScript for the app (so it works on cheap phones), a small database to save cases, and Claude (an AI model) for the language understanding part &mdash; with a working backup for when it isn't available.",
))
story.append(qa(
    "Who is this actually for?",
    "A patient in a busy government hospital or village clinic, and the doctor who has only a few minutes to help them.",
))

story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"), spaceBefore=10, spaceAfter=10))

# ---- Section: the golden rule --------------------------------------------
story.append(Paragraph("6. The one rule that saves you every single time", h1))
story.append(Paragraph(
    "If someone asks something you genuinely don't know the answer to: <b>do not guess, and do "
    "not panic.</b> Say exactly this &mdash; calmly:",
    body,
))
story.append(Paragraph(
    "“That's a fair question &mdash; I don't want to guess and give you wrong information. "
    "Let me note it down and we'll get back to you with the exact answer.”",
    ParagraphStyle("Golden", fontName="Helvetica-BoldOblique", fontSize=11, textColor=GREEN,
                   leading=16, spaceAfter=8, leftIndent=10, rightIndent=10, backColor=LIGHTGREEN,
                   borderPadding=8),
))
story.append(Paragraph(
    "This is genuinely what real engineers say. Nobody expects any one person to know everything "
    "about a project this size. What they ARE checking is whether you understand what you built "
    "&mdash; and everything on this page already proves that you do.",
    body,
))
story.append(Spacer(1, 14))
story.append(Paragraph(
    "You already know this project better than anyone in that room who hasn't read this page. "
    "Say the line in Section 1, breathe, and go.",
    ParagraphStyle("Closing", fontName="Helvetica-BoldOblique", fontSize=11.5, textColor=DARK,
                   alignment=TA_CENTER, leading=17, spaceBefore=6),
))

doc = SimpleDocTemplate(
    "/tmp/claude-0/report/Inayat_Team_Confidence_Sheet.pdf",
    pagesize=A4,
    topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    title="Inayat — Team Viva Confidence Sheet",
)


def footer(canvas, doc_):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Inayat — Team Confidence Sheet · {doc_.page}")
    canvas.restoreState()


doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("Team sheet built.")
