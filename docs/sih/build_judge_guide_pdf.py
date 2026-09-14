"""
Builds docs/sih/Inayat_Judge_Interview_Guide.pdf - a short, plain-language
sheet for explaining the prototype to SIH judges and in interviews.

Not part of the app - a one-off document generator, run manually and
re-run whenever the content needs updating. Kept as a script (not a
one-shot throwaway) so the PDF can be regenerated after edits.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

OUTPUT_PATH = "docs/sih/Inayat_Judge_Interview_Guide.pdf"

INK = HexColor("#1a1a1a")
MUTED = HexColor("#555555")
ACCENT = HexColor("#0b5d3b")
RULE = HexColor("#dddddd")

title_style = ParagraphStyle(
    "Title", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=4,
)
subtitle_style = ParagraphStyle(
    "Subtitle", fontName="Helvetica", fontSize=11, leading=14, textColor=MUTED, spaceAfter=14,
)
section_style = ParagraphStyle(
    "Section", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=ACCENT,
    spaceBefore=16, spaceAfter=6,
)
body_style = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=6,
)
question_style = ParagraphStyle(
    "Question", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=10, spaceAfter=2,
)
answer_style = ParagraphStyle(
    "Answer", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=2, leftIndent=10,
)
note_style = ParagraphStyle(
    "Note", fontName="Helvetica-Oblique", fontSize=9.5, leading=13, textColor=MUTED, spaceAfter=4, leftIndent=10,
)


def build():
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    story = []

    story.append(Paragraph("Inayat", title_style))
    story.append(Paragraph("Judge &amp; Interview Guide — SIH26047, Patient Case-Taking Software", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=10))

    # ---- What it is ----
    story.append(Paragraph("What it is", section_style))
    story.append(Paragraph(
        "Inayat listens to a patient's symptoms, in their own language, before they see the "
        "doctor. It turns what the patient says into a clean, written summary. The doctor reads "
        "the summary, checks it, and makes every decision. Inayat never diagnoses and never "
        "prescribes.", body_style,
    ))

    # ---- The problem ----
    story.append(Paragraph("The problem", section_style))
    story.append(Paragraph(
        "In many government hospitals, a doctor sees each patient for only 2 to 5 minutes. That "
        "is not enough time to ask proper questions, or to read a patient's old prescriptions and "
        "reports. Ayurvedic doctors need even more time, because their own method of check-up "
        "(called Dashavidha Pariksha) asks about ten different things, not just symptoms. "
        "Inayat does the time-consuming part before the doctor walks in.", body_style,
    ))

    # ---- How it works ----
    story.append(Paragraph("How it works — four simple steps", section_style))
    steps = [
        ["1", "Patient agrees, then talks or types", "A real consent step first — required, not optional — then their own language, no forms to fill."],
        ["2", "Inayat asks the right follow-up questions", "Different questions for a rash, a cough, a fever, or pain — not one script stretched over everything."],
        ["3", "Old documents are read", "Old prescriptions and reports are scanned and turned into text, with abnormal lab values flagged."],
        ["4", "The doctor reviews it on their own screen", "Reads the draft, edits any field, and confirms — logged in, not open to anyone nearby."],
    ]
    steps = [[row[0], Paragraph(f"<b>{row[1]}</b>", body_style), Paragraph(row[2], body_style)] for row in steps]
    table = Table(steps, colWidths=[1 * cm, 5.3 * cm, 8.7 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (1, 0), (1, -1), 12),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, RULE),
    ]))
    story.append(table)

    # ---- What's real vs planned ----
    story.append(Paragraph("What is built today, and what is still planned", section_style))
    story.append(Paragraph(
        "Said plainly, because judges notice when a team pretends something works. Built and "
        "tested today: the safety word-scan, the Ayurvedic (Dashavidha Pariksha) question set — "
        "with the seven questions a kiosk can actually ask a patient kept separate from the three "
        "only a physician's own exam can answer — reading old documents with abnormal lab values "
        "flagged, patient consent required before anything is recorded, a doctor's own review "
        "screen behind a real sign-in, and a real measured accuracy number from running our own "
        "test cases end to end. The full ABDM connection is a real, working first step (the OTP "
        "enrollment call, against ABDM's actual sandbox API shape) — the full hospital-record "
        "exchange on top of it is a named next step, not finished yet, and we are not claiming it "
        "is.", body_style,
    ))

    # ---- What makes it different ----
    story.append(Paragraph("What makes this different from other teams", section_style))
    story.append(Paragraph(
        "Everyone at this hackathon will show working code — that alone will not stand out. What "
        "usually breaks a team in front of judges is the follow-up question: click into the doctor "
        "view with no login and it breaks trust instantly; ask 'what's your actual accuracy' and a "
        "slide number with no real test behind it breaks trust just as fast. Every hard question "
        "below has a real answer behind it, not a rehearsed line — a login gate on patient data, a "
        "measured accuracy number from an actual test run, follow-up questions that change for a "
        "rash versus a cough versus chest pain, and a consent step that was missing until we found "
        "it ourselves and fixed it, not something a judge caught first.",
        body_style,
    ))

    story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceBefore=10, spaceAfter=6))

    # ---- Judge Q&A ----
    story.append(Paragraph("Judge questions — short, honest answers", section_style))

    qa = [
        ("Is this an AI diagnosis tool?",
         "No. It never diagnoses and never prescribes. It only writes a draft. The doctor reviews it "
         "on their own screen, can edit any field, and decides everything."),
        ("What if the AI misses an emergency?",
         "We check twice. First, a simple word-search looks for danger words like “chest pain” or "
         "“unconscious” — this runs with no AI call at all, so it works even if the AI is down. "
         "Second, the AI is told to be extra careful on anything the word-search doesn't catch. Both "
         "checks would have to fail at once to miss a real emergency."),
        ("How is this different from a chatbot?",
         "A chatbot just replies. Inayat follows a fixed medical structure — complaint, history, "
         "past illness, allergies, and so on — and asks different follow-up questions depending on "
         "what the patient actually said: a rash gets asked about spread and new exposures, a cough "
         "gets asked about phlegm and triggers, chest pain gets the standard SOCRATES pain "
         "questions doctors are trained on. One script does not fit every complaint, and ours "
         "doesn't pretend it does."),
        ("Is patient data safe? Who can see it?",
         "The doctor's review screen sits behind a real sign-in — without the correct passcode, "
         "every request for patient data is rejected by the server itself, not just hidden by the "
         "interface. We're honest about its current scope: one shared staff passcode today, not "
         "individual logins per doctor yet — a named next step, not hidden. Raw voice recordings are "
         "never kept after the summary is made, only the resulting text."),
        ("Do you have patient consent?",
         "Yes — required, not optional. The patient must explicitly agree before any of the three "
         "ways to submit (typing, a photo, or recording) will go through; the server itself refuses "
         "to save a case without it, so this isn't just a checkbox we could forget to check."),
        ("What languages does it support?",
         "The patient's own language, using Bhashini, India's government speech-translation service, "
         "with the interface itself in English, Hindi, and Telugu — not English only."),
        ("Is this connected to India's health record system?",
         "We are using ABDM's official test system (called a sandbox) to build a real connection — "
         "the actual OTP enrollment call, encrypted the way ABDM's real API requires. It is a "
         "genuine, working first step, not a finished claim, and we say so honestly rather than "
         "faking the rest on a slide."),
        ("What's your actual accuracy? How do you know it works?",
         "We ran our own test cases through the real pipeline and measured it, rather than asserting "
         "a number: 100% of the emergency cases our safety net could evaluate were caught correctly. "
         "We say plainly which cases needed a live AI connection we don't have credentials for in "
         "this demo, instead of hiding that gap in the denominator."),
        ("What is not finished yet?",
         "The full hospital-record data exchange on top of our real ABDM sandbox connection, and "
         "wider handwriting-OCR accuracy. Both are named honestly as next steps, not hidden."),
        ("How did you build this?",
         "I designed the system and understand every decision in it. I used AI coding tools to help "
         "write and test the code faster — the same way many real companies build software today."),
        ("What would you do next if shortlisted?",
         "Move from one shared staff passcode to individual doctor logins, complete the full ABDM "
         "data exchange, and test the Ayurvedic question set with a real BAMS-trained reviewer."),
    ]
    for question, answer in qa:
        story.append(Paragraph(f"Q: {question}", question_style))
        story.append(Paragraph(f"A: {answer}", answer_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=6))
    story.append(Paragraph(
        "One rule to remember above all: Inayat is a scribe, never the decision-maker. "
        "Every honest answer above comes back to that one line.", note_style,
    ))

    doc.build(story)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
