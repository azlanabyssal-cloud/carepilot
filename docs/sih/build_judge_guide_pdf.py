"""
Builds docs/sih/MediKiosk_Judge_Interview_Guide.pdf - a short, plain-language
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

OUTPUT_PATH = "docs/sih/MediKiosk_Judge_Interview_Guide.pdf"

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

    story.append(Paragraph("MediKiosk", title_style))
    story.append(Paragraph("Judge &amp; Interview Guide — SIH26047, Patient Case-Taking Software", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=10))

    # ---- What it is ----
    story.append(Paragraph("What it is", section_style))
    story.append(Paragraph(
        "MediKiosk listens to a patient's symptoms, in their own language, before they see the "
        "doctor. It turns what the patient says into a clean, written summary. The doctor reads "
        "the summary, checks it, and makes every decision. MediKiosk never diagnoses and never "
        "prescribes.", body_style,
    ))

    # ---- The problem ----
    story.append(Paragraph("The problem", section_style))
    story.append(Paragraph(
        "In many government hospitals, a doctor sees each patient for only 2 to 5 minutes. That "
        "is not enough time to ask proper questions, or to read a patient's old prescriptions and "
        "reports. Ayurvedic doctors need even more time, because their own method of check-up "
        "(called Dashavidha Pariksha) asks about ten different things, not just symptoms. "
        "MediKiosk does the time-consuming part before the doctor walks in.", body_style,
    ))

    # ---- How it works ----
    story.append(Paragraph("How it works — four simple steps", section_style))
    steps = [
        ["1", "Patient talks or types", "In their own language. No forms to fill."],
        ["2", "MediKiosk asks follow-up questions", "The way a doctor would — where does it hurt, since when, how bad."],
        ["3", "Old documents are read", "Old prescriptions and reports are scanned and turned into text."],
        ["4", "A summary is written for the doctor", "The doctor reads it, edits if needed, and decides."],
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
        "Said plainly, because judges notice when a team pretends something works: the symptom "
        "check and the safety word-scan are built and tested today. Reading old documents is "
        "built and tested. The Ayurvedic question set and the link to India's health record "
        "system (ABDM) are real, planned next steps — not finished yet, and we are not claiming "
        "they are.", body_style,
    ))

    # ---- What makes it different ----
    story.append(Paragraph("What makes this different from other teams", section_style))
    story.append(Paragraph(
        "Most teams building this will connect an AI chatbot to a voice tool and stop there. "
        "We are doing the two harder parts most teams skip: real, honest work on the Ayurvedic "
        "question set (not just decoration), and a real, tested connection to India's ABDM "
        "health record system — using its official test system, not a fake claim on a slide.",
        body_style,
    ))

    story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceBefore=10, spaceAfter=6))

    # ---- Judge Q&A ----
    story.append(Paragraph("Judge questions — short, honest answers", section_style))

    qa = [
        ("Is this an AI diagnosis tool?",
         "No. It never diagnoses and never prescribes. It only writes a draft. The doctor decides everything."),
        ("What if the AI misses an emergency?",
         "We check twice. First, a simple word-search looks for danger words like “chest pain” or "
         "“unconscious.” Second, the AI is told to be extra careful. Both checks would have to "
         "fail at once to miss a real emergency."),
        ("How is this different from a chatbot?",
         "A chatbot just replies. MediKiosk follows a fixed medical structure — complaint, history, "
         "past illness, allergies, and so on — and has a hard safety rule built into the code itself, "
         "not just a polite request to the AI."),
        ("Is patient data safe?",
         "Yes. We do not keep the voice recording or raw data after the summary is made. The patient "
         "gives clear consent before we start."),
        ("What languages does it support?",
         "The patient's own language, using Bhashini, India's government speech-translation service — "
         "not English only."),
        ("Is this connected to India's health record system?",
         "We are using ABDM's official test system (called a sandbox) to build a real connection. "
         "It is a genuine, working first step, not a finished claim."),
        ("What is not finished yet?",
         "The full Ayurvedic question set and the full ABDM connection. Both are named honestly as "
         "next steps, not hidden."),
        ("How did you build this?",
         "I designed the system and understand every decision in it. I used AI coding tools to help "
         "write and test the code faster — the same way many real companies build software today."),
        ("What would you do next if shortlisted?",
         "Finish the Ayurvedic question set with real review, complete the ABDM connection, and test "
         "with real hospital staff."),
    ]
    for question, answer in qa:
        story.append(Paragraph(f"Q: {question}", question_style))
        story.append(Paragraph(f"A: {answer}", answer_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=6))
    story.append(Paragraph(
        "One rule to remember above all: MediKiosk is a scribe, never the decision-maker. "
        "Every honest answer above comes back to that one line.", note_style,
    ))

    doc.build(story)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
