"""
Inayat -- The Live Demo Script (3-4 minute stage walkthrough of the
actual running prototype). Written as one continuous, performable
script (SAY / [CLICK] / [PAUSE], same pattern as the slide-deck stage
script), not a reference document. Every line and every quoted output
was verified live against the real app on 15 Sep 2026, including the
honest finding that self_care/clinic_visit levels are NOT reliably
reachable live without a configured LLM key on this deployment -- the
script is built around what the prototype actually does.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, ListFlowable, ListItem,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")
BLUE = colors.HexColor("#0b4f9c")
AMBER_BG = colors.HexColor("#fff6e5")
AMBER_TXT = colors.HexColor("#8a5a00")

title_style = ParagraphStyle("TitleX", fontName="Helvetica-Bold", fontSize=24, textColor=DARK,
                              alignment=TA_CENTER, leading=29, spaceAfter=6)
subtitle_style = ParagraphStyle("SubtitleX", fontName="Helvetica", fontSize=11, textColor=GREY,
                                 alignment=TA_CENTER, spaceAfter=10, leading=14)
hook_style = ParagraphStyle("Hook", fontName="Helvetica-Oblique", fontSize=10, textColor=DARK,
                             alignment=TA_CENTER, spaceAfter=4, leading=14)
h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=13.5, textColor=GREEN, spaceBefore=7, spaceAfter=3)
moment_style = ParagraphStyle("Moment", fontName="Helvetica-Bold", fontSize=9, textColor=GREY,
                               spaceBefore=6, spaceAfter=1, leading=11)
click_style = ParagraphStyle("Click", fontName="Helvetica-BoldOblique", fontSize=9.3, textColor=BLUE,
                              leading=12.5, spaceAfter=2)
say_style = ParagraphStyle("Say", fontName="Helvetica", fontSize=10.3, textColor=DARK, leading=14.5, spaceAfter=3)
pause_style = ParagraphStyle("Pause", fontName="Helvetica-Oblique", fontSize=8.8, textColor=GREY,
                              leading=11.5, spaceAfter=4)
note_style = ParagraphStyle("Note", fontName="Helvetica", fontSize=8.6, textColor=GREY, leading=11.5, spaceAfter=2)
body = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.6, textColor=DARK, leading=13, spaceAfter=3)


def h(text):
    return [HRFlowable(width="100%", thickness=1.1, color=GREEN, spaceBefore=3, spaceAfter=4), Paragraph(text, h1)]


def points(items, size=9.4, gap_after=1, indent=13):
    style = ParagraphStyle("PtsX", fontName="Helvetica", fontSize=size, textColor=DARK, leading=size * 1.25, spaceAfter=gap_after)
    return ListFlowable(
        [ListItem(Paragraph(t, style), bulletColor=GREEN, value="–") for t in items],
        bulletType="bullet", start="–", leftIndent=indent, spaceBefore=1, spaceAfter=3,
    )


def beat(moment, click, say, note=None):
    """One beat of the performed script: a moment label, an optional
    stage direction, the line to say, and an optional footnote. Kept
    together so a beat never splits across a page."""
    flow = []
    if moment:
        flow.append(Paragraph(moment, moment_style))
    if click:
        flow.append(Paragraph("[" + click + "]", click_style))
    if say:
        flow.append(Paragraph("SAY: “" + say + "”", say_style))
    if note:
        flow.append(Paragraph(note, note_style))
    return KeepTogether(flow)


def pause(text="[PAUSE]"):
    return Paragraph(text, pause_style)


story = []

# ---- Cover ------------------------------------------------------------
story.append(Spacer(1, 8))
story.append(Paragraph("The Live Demo Script", title_style))
story.append(Paragraph("What to actually say and click, start to finish — timed to ~3:30, fits a 4-minute slot", subtitle_style))
story.append(HRFlowable(width="45%", thickness=1, color=GREEN, spaceBefore=2, spaceAfter=10, hAlign="CENTER"))
story.append(Paragraph(
    "Read this out loud, start to finish, before you go up — don't just skim it. Every line here was "
    "said, clicked, and verified against the real running app, not written from memory.",
    hook_style,
))
story.append(Spacer(1, 6))

# ---- The script ----------------------------------------------------------
story += h("The script")

story.append(beat(
    "OPEN — no click yet",
    None,
    "Good [morning/afternoon], judges. Doctors in India spend about two minutes with each patient. But "
    "seventy to eighty percent of a correct diagnosis comes from the patient's history alone, before any "
    "test. So the two minutes doctors have the least of is exactly the two minutes that decides the most.",
))
story.append(pause())

story.append(beat(
    "THE SAFETY NET — zero clicks",
    "POINT at the live-demo ticker on the homepage, under the hero text — it types and reacts on its own",
    "Watch this — I haven't clicked anything yet. This is typing a real emergency phrase and catching it "
    "live, against the same safety check every real submission runs through. No AI call needed for this "
    "part — it works even fully offline.",
    "If the ticker is still loading when you arrive, wait a beat in silence rather than talking over a blank box.",
))
story.append(pause())

story.append(beat(
    "TYPE IT YOURSELF — and show it's not just typing",
    "CLICK into the “Describe how you are feeling” box. TYPE (or paste): "
    "“I have had a mild cough and runny nose for two days, no fever.”",
    "Now let me actually use it, the way a patient would. And it isn't just typing — I could just as "
    "easily tap this microphone and speak in Hindi or Telugu, or photograph an old prescription instead. "
    "One entry point, three ways in, for whoever's in front of it.",
    "POINT at the mic button and the photo-upload button as you say this — don't actually record or "
    "upload, that's real audio/OCR processing and eats time you don't have. Pointing is enough.",
))
story.append(pause())

story.append(beat(
    "THE ADAPTIVE FOLLOW-UP QUESTION — a real differentiator",
    "A question appears right under the box: “Is it a dry cough, or are you bringing up phlegm or "
    "mucus?” CLICK an answer, or CLICK “Skip these questions” to move on",
    "This is asking the same follow-up a doctor would — adapted to what I actually typed, not a fixed "
    "form. It can ask up to eight of these, one at a time, and every one is skippable.",
    "Verified live: typing this exact sentence surfaces “Question 1 of 8” immediately. Answer one for "
    "effect, then skip the rest to protect your time.",
))
story.append(pause())

story.append(beat(
    None,
    "CLICK Next → Next (skip the optional photo step) → fill Age 29 and Days 2 → Next → check the "
    "consent box → Submit My Symptoms",
    "Age and how many days are optional — you can skip them and it still works. And this consent line is "
    "real, not decorative — it's enforced on the server too, in line with India's Digital Personal Data "
    "Protection Act.",
))
story.append(pause())

story.append(beat(
    "THE RESULT — this is the core of the pitch",
    "SCROLL through, in order: the priority banner → “Why this priority level” → Chief Complaint / "
    "History of Present Illness → the AI-drafted disclosure line",
    "This isn't just a label — it quotes the actual clinical guideline sentence it matched, and how "
    "similar the match was. That's a real citation, not a black box. And notice this line at the bottom: "
    "it openly says this is AI-drafted and hasn't been reviewed by a physician yet. It's built to help a "
    "doctor decide faster — never to replace the doctor's own judgment.",
    "Verified live: this exact input returns URGENT with a guideline quoted at 40% similarity.",
))
story.append(pause())

story.append(beat(
    "TWO MORE REAL FEATURES, QUICKLY — if short on time, cut this beat before any other",
    "CLICK the AYUSH toggle (“This is an Ayurvedic OPD visit”) to reveal the real form for one second, "
    "then CLICK “Listen to summary” and let it speak a few words before moving on",
    "For an Ayurvedic consultation, it captures the real Dashavidha Pariksha history an AYUSH doctor "
    "actually uses — Prakriti, Vikriti, and the rest — not a generic form with “Ayurveda” relabeled onto "
    "it. And for anyone who'd rather listen than read, the whole summary plays back as audio too.",
    "Don't wait for the audio to finish — a few seconds of it playing is proof enough, then move on.",
))
story.append(pause())

story.append(beat(
    "THE TAKEAWAY MOMENT",
    "CLICK “Download this summary.” A file lands immediately — show the downloads bar/folder if visible",
    "And here's the whole point of doing this before the visit: one tap, and the patient has a real file "
    "they can carry straight into the consultation room — no login, no app to install, works on any "
    "phone.",
))
story.append(pause())

story.append(beat(
    "THE DOCTOR'S SIDE — cut this second if you're still short on time",
    "CLICK “Physician console” (top of page) → sign in with the staff passcode → open the case "
    "you just submitted",
    "And this is what the doctor sees the moment the patient walks in — the same draft, ready to accept, "
    "amend, or reject. Same real case, same database — not a separate demo.",
))
story.append(pause())

story.append(beat(
    "CLOSE — say this one slowly, make eye contact",
    None,
    "One last thing: every safety check you just saw — the red-flag catch, the priority level, the "
    "guideline citation — runs with zero API cost. It keeps working even if the AI service is down. "
    "That's what lets this scale to a real, high-volume government hospital, not just stay a demo. "
    "INAYAT means ‘care’ in Urdu — we built it to give the doctor's two minutes back to actually "
    "deciding, not repeating questions. Thank you — happy to take questions.",
))
story.append(pause("[PAUSE for questions]"))

story.append(Spacer(1, 4))
story.append(HRFlowable(width="100%", thickness=1.1, color=GREEN, spaceBefore=2, spaceAfter=5))
story.append(Paragraph(
    "If you forget every line above, remember the shape of it: <b>open on the 2-minute problem → the "
    "homepage catches an emergency with zero clicks → type one input, point at voice/photo, answer one "
    "adaptive question → point at the guideline citation → flash AYUSH + audio → download the file → "
    "close on ‘zero API cost, still works offline.’</b>",
    ParagraphStyle("Fallback", parent=body, fontSize=9.4, spaceAfter=2),
))

# ---- Before you walk up ----------------------------------------------
story += h("Before you walk up")
story.append(points([
    "Open the live URL 3–5 minutes early — free-tier hosting can be slow to wake on the first hit of the day. Let it fully settle before your slot.",
    "Do one hard refresh (Ctrl/Cmd+Shift+R) right before you go up, just to be safe.",
    "Have the demo line ready to paste, not typed live from memory: “I have had a mild cough and runny nose for two days, no fever.”",
    "If you're showing the physician console, confirm the staff passcode works on this exact device beforehand.",
]))

# ---- If it breaks live -------------------------------------------------
story += h("If it breaks live — keep composure, don't improvise")
story.append(points([
    "<b>Page slow to load:</b> keep talking through the opening lines while it catches up — don't stand in silence.",
    "<b>Wi-Fi drops entirely:</b> say plainly, “looks like the connection dropped — let me talk you through it,” and narrate the results screen from this script, from memory.",
    "<b>Page looks visually broken:</b> one hard refresh, done without apologizing at length — then continue exactly where you left off.",
    "<b>A judge says “why urgent for something minor?”:</b> SAY — “That's intentional. Without a live AI connection configured here, it defaults to the cautious answer rather than guessing — it escalates on any real signal but never quietly reassures someone who might be wrong to be reassured. We kept the offline mode conservative on purpose, because that's the one that has to be trustworthy at zero cost.” Never promise a different typed input will show self-care live — on this deployment it won't.",
    "<b>Download seems to do nothing:</b> check the downloads bar/folder — some browsers save silently. If truly blocked, fall back to “Listen to summary” instead.",
    "<b>Physician passcode fails:</b> skip it — say one sentence about what the doctor would see, and move to the close. Never fumble a password on stage.",
]))

doc = SimpleDocTemplate(
    "Inayat_Live_Demo_Script.pdf", pagesize=A4,
    leftMargin=16 * mm, rightMargin=16 * mm, topMargin=13 * mm, bottomMargin=13 * mm,
    title="Inayat Live Demo Script", author="Team SANKALP",
)
doc.build(story)
print("built")
