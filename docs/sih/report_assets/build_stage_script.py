"""
Inayat -- Stage Script (presenter script, one section per real slide)
Grounded directly in the team's actual uploaded PPTX content (extracted
verbatim from the slide XML). Nothing invented -- only formatted for a
clean, readable, printable page with clear SAY / PAUSE / LOUD cues.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, ListFlowable, ListItem, PageBreak,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")
LOUD_BG = colors.HexColor("#eaf6ef")

title_style = ParagraphStyle("TitleX", fontName="Helvetica-Bold", fontSize=25, textColor=DARK,
                              alignment=TA_CENTER, leading=30, spaceAfter=8)
subtitle_style = ParagraphStyle("SubtitleX", fontName="Helvetica", fontSize=11.5, textColor=GREY,
                                 alignment=TA_CENTER, spaceAfter=12, leading=15)
hook_style = ParagraphStyle("HookX", fontName="Helvetica-Oblique", fontSize=10.8, textColor=DARK,
                             alignment=TA_CENTER, spaceAfter=4, leading=15)
slide_h = ParagraphStyle("SlideH", fontName="Helvetica-Bold", fontSize=14, textColor=GREEN,
                          spaceBefore=8, spaceAfter=3)
say_style = ParagraphStyle("Say", fontName="Helvetica", fontSize=10.3, textColor=DARK,
                            leading=14.5, spaceAfter=5, alignment=TA_LEFT)
loud_style = ParagraphStyle("Loud", fontName="Helvetica-Bold", fontSize=11, textColor=GREEN,
                             leading=15, spaceAfter=5, spaceBefore=2, alignment=TA_LEFT,
                             backColor=LOUD_BG, borderPadding=(4, 6, 4, 6))
pause_style = ParagraphStyle("Pause", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY,
                              leading=12, spaceAfter=5, spaceBefore=1)
cue_style = ParagraphStyle("Cue", fontName="Helvetica-BoldOblique", fontSize=9.3, textColor=colors.HexColor("#8a5a00"),
                            leading=12, spaceAfter=4, spaceBefore=1)
fallback_h = ParagraphStyle("FallbackH", fontName="Helvetica-Bold", fontSize=12, textColor=DARK,
                             spaceBefore=8, spaceAfter=3)
fallback_pt = ParagraphStyle("FallbackPt", fontName="Helvetica", fontSize=10.3, textColor=DARK,
                              leading=14, spaceAfter=2)


def h(width="100%"):
    return HRFlowable(width=width, thickness=1.1, color=GREEN, spaceBefore=2, spaceAfter=5)


def slide_block(number, title, blocks):
    flow = [Paragraph(f"SLIDE {number} &mdash; {title}", slide_h), h()]
    for kind, text in blocks:
        if kind == "say":
            flow.append(Paragraph(text, say_style))
        elif kind == "loud":
            flow.append(Paragraph(text, loud_style))
        elif kind == "pause":
            flow.append(Paragraph(text, pause_style))
        elif kind == "cue":
            flow.append(Paragraph(text, cue_style))
    return flow


story = []

# ---- Cover ----------------------------------------------------------------
story.append(Spacer(1, 10))
story.append(Paragraph("Inayat &mdash; Stage Script", title_style))
story.append(Paragraph("What to actually say, slide by slide &mdash; read once out loud before you go up", subtitle_style))
story.append(h("45%"))
story.append(Paragraph(
    "Six slides, about five minutes. Don't read bullets off the slide &mdash; say these in your own words. "
    "Green boxes = say it loud and slow. Italic lines = pause.",
    hook_style,
))
story.append(Spacer(1, 8))

# ---- Slide 1 ----------------------------------------------------------------
story.append(KeepTogether(slide_block(1, "Title", [
    ("say", "“Good [morning/afternoon], judges. We are Team SANKALP, presenting our solution for "
             "Problem Statement SIH26-CC-0032 &mdash; Patient Case-Taking Software.”"),
    ("pause", "[PAUSE &mdash; let the slide sit for 2 seconds before talking]"),
])))

# ---- Slide 2 ----------------------------------------------------------------
story.append(KeepTogether(slide_block(2, "Problem Statement &amp; Idea", [
    ("say", "“Let's start with one number."),
    ("cue", "(SAY THIS SLOWLY, LOUD, PAUSE AFTER)"),
    ("loud", "“In an Indian OPD, a doctor spends about two minutes with each patient.”"),
    ("pause", "[PAUSE 1 second &mdash; let it land]"),
    ("say", "“Two minutes to listen, examine, and decide. But research shows 70 to 80 percent of a "
             "correct diagnosis comes from the history alone &mdash; before any test. So the two minutes "
             "doctors have the least of is exactly the two minutes that matters most."),
    ("say", "Patients bring torn, unstructured old prescriptions. Elderly, rural, and low-literacy patients "
             "get left out of most digital tools. Doctors end up repeating the same basic questions every "
             "single time."),
    ("say", "That's the real problem. Our idea:"),
    ("cue", "(SAY THIS LOUD AND CLEAR)"),
    ("loud", "“INAYAT lets a patient describe their problem &mdash; by typing, by speaking in their own "
              "language, or by photographing an old prescription &mdash; and turns it into a clean, "
              "physician-ready history. Before the doctor even walks in.”"),
    ("pause", "[PAUSE, then move to next slide]"),
])))

# ---- Slide 3 ----------------------------------------------------------------
story.append(KeepTogether(slide_block(3, "Proposed Solution", [
    ("say", "“INAYAT means 'care' in Urdu. We named it that on purpose &mdash; the whole prototype "
             "exists to give every patient the caring attention a two-minute visit can't.”"),
    ("pause", "[PAUSE 1 second]"),
    ("say", "“Five things make this real, not just a chatbot:"),
    ("say", "Multilingual voice, so language is never a barrier. Adaptive questioning &mdash; a cough gets "
             "different follow-ups than a rash. Safety-first triage that runs before anything else. Smart "
             "document reading from old prescriptions. And AYUSH-aware history, for Ayurvedic consultations too."),
    ("cue", "(POINT AT THE SCREEN / QR CODE HERE)"),
    ("say", "“This is a live, working prototype &mdash; not a mockup. The link is right there if you "
             "want to open it yourself.”"),
    ("say", "“We're not just a chatbot, and we're not just a form. We're the only one doing all four "
             "of these together.”"),
])))

# ---- Slide 4 ----------------------------------------------------------------
story.append(KeepTogether(slide_block(4, "Technical Feasibility", [
    ("say", "“Quickly on how it's built &mdash; real technology, not vapor."),
    ("say", "Frontend is plain HTML and JavaScript, on purpose, so it loads fast on a cheap phone with a "
             "weak connection. Backend is Python and FastAPI with SQLite. Claude does the language "
             "reasoning, backed by our own TF-IDF safety check. Tesseract reads old prescriptions. "
             "Bhashini and offline speech tools handle voice. And we connect to ABDM &mdash; India's real "
             "government health-ID system &mdash; with real OTP and encryption, not a mock.”"),
    ("pause", "[PAUSE &mdash; don't linger here, judges skim tech slides fast]"),
    ("say", "“Everything on this slide is running in the live prototype right now.”"),
])))

# ---- Slide 5 ----------------------------------------------------------------
story.append(KeepTogether(slide_block(5, "Impact and Benefits", [
    ("say", "“What does this actually change?"),
    ("say", "For patients &mdash; voice access in their own language, even elderly or low-literacy "
             "patients, and it still works with weak or no internet."),
    ("say", "For doctors &mdash; the history is ready before they walk in. Less repeating, more time to "
             "actually examine and think."),
    ("say", "And here's the one judges usually ask about:"),
    ("cue", "(SAY THIS CLEARLY)"),
    ("loud", "“Our safety-critical checks run with zero API cost &mdash; they work even if the AI "
              "service is down. That's what makes this scale to a real, high-volume government hospital, "
              "not just a demo.”"),
])))

# ---- Slide 6 ----------------------------------------------------------------
story.append(KeepTogether(slide_block(6, "Research and References", [
    ("say", "“Last thing &mdash; we didn't guess any of this. The two-minute consultation figure is "
             "from a real BMJ Open study across 67 countries. Our AYUSH questions are cross-checked against "
             "real Dashavidha Pariksha references. And our health-ID integration follows ABDM's actual "
             "published API and encryption spec.”"),
    ("pause", "[PAUSE]"),
    ("cue", "(CLOSING LINE &mdash; SAY SLOWLY, MAKE EYE CONTACT)"),
    ("loud", "“INAYAT listens to a patient before the doctor does, and turns that into a safe, "
              "organized note &mdash; so the doctor's two minutes go to deciding, not repeating questions. "
              "Thank you.”"),
    ("pause", "[PAUSE for questions]"),
])))

story.append(Spacer(1, 6))

# ---- Fallback -----------------------------------------------------------
story.append(KeepTogether([
    h("100%"),
    Paragraph("If you forget everything else, remember these 3 lines", fallback_h),
    ListFlowable(
        [
            ListItem(Paragraph("“A doctor gets two minutes. History gives 70&ndash;80% of the diagnosis.”", fallback_pt), bulletColor=GREEN, value=1),
            ListItem(Paragraph("“INAYAT means care &mdash; we built it to give that two minutes back.”", fallback_pt), bulletColor=GREEN, value=2),
            ListItem(Paragraph("“Zero-API-cost safety checks. Real government health-ID. Live, not a mockup.”", fallback_pt), bulletColor=GREEN, value=3),
        ],
        bulletType="1", leftIndent=14, spaceBefore=2, spaceAfter=4,
    ),
]))

doc = SimpleDocTemplate(
    "Inayat_Stage_Script.pdf", pagesize=A4,
    leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
    title="Inayat Stage Script", author="Team SANKALP",
)
doc.build(story)
print("built")
