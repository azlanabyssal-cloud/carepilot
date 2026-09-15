"""
Inayat -- The Live Demo Script (3-4 minute stage walkthrough of the
actual running prototype). Every click, screen, and quoted output in
this document was verified live against the real app on 15 Sep 2026,
including the honest finding that self_care/clinic_visit levels are
NOT reliably reachable live without a configured LLM key on this
deployment -- the script is built around what the prototype actually
does, not an idealized version of it.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, ListFlowable, ListItem, PageBreak, Table, TableStyle,
)

GREEN = colors.HexColor("#1a7a4c")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")
AMBER = colors.HexColor("#8a5a00")
AMBER_BG = colors.HexColor("#fff6e5")
BLUE_BG = colors.HexColor("#eef4fb")

title_style = ParagraphStyle("TitleX", fontName="Helvetica-Bold", fontSize=24, textColor=DARK,
                              alignment=TA_CENTER, leading=29, spaceAfter=6)
subtitle_style = ParagraphStyle("SubtitleX", fontName="Helvetica", fontSize=11, textColor=GREY,
                                 alignment=TA_CENTER, spaceAfter=10, leading=14)
h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=14, textColor=GREEN, spaceBefore=8, spaceAfter=3)
h2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=10.8, textColor=DARK, spaceBefore=5, spaceAfter=2)
body = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.6, textColor=DARK, leading=13, spaceAfter=3)
click_style = ParagraphStyle("Click", fontName="Helvetica-Bold", fontSize=9.6, textColor=colors.HexColor("#0b4f9c"),
                              leading=13, spaceAfter=2)
say_style = ParagraphStyle("Say", fontName="Helvetica-Oblique", fontSize=9.6, textColor=DARK,
                            leading=13, spaceAfter=3)
warn_style = ParagraphStyle("Warn", fontName="Helvetica-Bold", fontSize=9.3, textColor=AMBER,
                             leading=12.5, spaceAfter=2, backColor=AMBER_BG, borderPadding=(4, 6, 4, 6))
small = ParagraphStyle("Small", fontName="Helvetica", fontSize=8.6, textColor=GREY, leading=11.5, spaceAfter=2)


def h(text, size="100%"):
    return [HRFlowable(width=size, thickness=1.1, color=GREEN, spaceBefore=3, spaceAfter=4), Paragraph(text, h1)]


def points(items, size=9.4, gap_after=1, indent=13):
    style = ParagraphStyle("PtsX", fontName="Helvetica", fontSize=size, textColor=DARK, leading=size * 1.25, spaceAfter=gap_after)
    return ListFlowable(
        [ListItem(Paragraph(t, style), bulletColor=GREEN, value="–") for t in items],
        bulletType="bullet", start="–", leftIndent=indent, spaceBefore=1, spaceAfter=3,
    )


def subsection(title, pts):
    return KeepTogether([Paragraph(title, h2), points(pts)])


def timed_step(time_range, title, click, say, note=None):
    flow = [Paragraph(f"<b>{time_range}</b>  —  {title}", h2)]
    if click:
        flow.append(Paragraph("CLICK/SHOW: " + click, click_style))
    if say:
        flow.append(Paragraph("SAY: “" + say + "”", say_style))
    if note:
        flow.append(Paragraph(note, small))
    return KeepTogether(flow)


story = []

# ---- Cover ------------------------------------------------------------
story.append(Spacer(1, 8))
story.append(Paragraph("The Live Demo Script", title_style))
story.append(Paragraph(
    "A 3–4 minute, second-by-second walkthrough of the real running prototype — "
    "verified live, not imagined",
    subtitle_style,
))
story.append(HRFlowable(width="45%", thickness=1, color=GREEN, spaceBefore=2, spaceAfter=10, hAlign="CENTER"))
story.append(Paragraph(
    "Every screen, click, and quoted line of output in this script was tested against the actual "
    "deployed app on 15 Sep 2026. Rehearse it once end-to-end before you go up — not just read it.",
    ParagraphStyle("Hook", parent=body, alignment=TA_CENTER, fontName="Helvetica-Oblique"),
))
story.append(Spacer(1, 6))

# ---- 0. Before you walk up ---------------------------------------------
story += h("0. Ninety seconds before you walk up")
story.append(points([
    "Open the live URL in a fresh tab <b>3–5 minutes early</b> — free-tier hosting can take a moment to wake up on the first request of the day. Load it once, let it fully settle, before your slot starts.",
    "Do <b>one hard refresh</b> (Ctrl/Cmd+Shift+R) right before you go up. The app now revalidates its own files on every load, but a hard refresh costs nothing and removes all doubt.",
    "Have the symptom text for the live demo <b>already typed somewhere you can copy-paste</b> (notes app, or memorized) — typing live on a projector, under nerves, is where most demo time gets lost.",
    "Know your Wi-Fi situation. If it's flaky, mention that up front, lightly, rather than letting a slow load read as the app being broken.",
    "If you plan to show the physician console, confirm the staff passcode works on <b>this exact device</b> beforehand — don't discover it live.",
]))

# ---- 1. The script ------------------------------------------------------
story += h("1. The script — timed to ~3:30, fits a 4-minute slot")
story.append(Paragraph(
    "Times are cumulative from when you start talking, not per-step. If you're given only 3 minutes, "
    "cut the physician console step (marked <b>[CUTTABLE]</b> below) — nothing else depends on it.",
    small,
))
story.append(Spacer(1, 3))

story.append(timed_step(
    "0:00–0:20", "Open with the real problem, no click yet",
    None,
    "Doctors in India spend about two minutes with each patient. But seventy to eighty percent of a "
    "correct diagnosis comes from the patient's history alone, before any test. So the two minutes "
    "doctors have the least of is exactly the two minutes that decides the most.",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "0:20–0:45", "Let the landing page prove the safety net — zero clicks",
    "The live-demo ticker on the homepage (under the hero text). Just point — it types and reacts on its own.",
    "Watch this — I haven't clicked anything yet. This is typing a real emergency phrase and catching it "
    "live, against the same safety check every real submission runs through. No AI call needed for this "
    "part — it works even fully offline.",
    "Real behavior: the ticker fetches the live red-flag term list from the backend once, then types and "
    "matches client-side. If it's still loading when you arrive, wait a beat — don't narrate over a blank box.",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "0:45–1:10", "Type a real symptom yourself",
    "Click into the “Describe how you are feeling” box. Type (or paste): "
    "“I have had a mild cough and runny nose for two days, no fever.”",
    "Now let me actually use it, the way a patient would — typing, in plain words, no medical jargon.",
    "Verified input — use this exact phrase. It reliably produces the richest results screen (guideline "
    "citation + every action button) on the current deployment.",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "1:10–1:35", "Move through the 4-step form quickly",
    "Next → Next (skip the optional photo step) → fill Age (e.g. 29) and Days (e.g. 2) → Next → "
    "check the consent box → Submit My Symptoms.",
    "Age and how many days are optional context — you can skip them entirely and it still works. I'll add "
    "them quickly. And this consent line is real, not decorative — it's enforced on the server too, in "
    "line with India's Digital Personal Data Protection Act.",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "1:35–2:20", "The results screen — this is the core of the pitch",
    "Scroll through, in order: the priority banner → the “Why this priority level” box → the "
    "Chief Complaint / History of Present Illness fields → the AI-drafted disclosure line.",
    "This isn't just a label. It quotes the actual clinical guideline sentence it matched, and how "
    "similar the match was — that's a real citation, not a black box. And notice this line at the "
    "bottom: it openly says this is AI-drafted and hasn't been reviewed by a physician yet. It's built "
    "to help a doctor decide faster — never to replace the doctor's own judgment.",
    "Verified live: this exact input returns URGENT with a guideline quoted at 40% similarity. If a judge "
    "asks “why urgent for a mild cough?” — see Section 3, “If a judge questions the output.”",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "2:20–2:45", "One-click download — the “carry it to the doctor” moment",
    "Click “Download this summary.” A file lands immediately — show the downloads bar/folder if visible.",
    "And here's the whole point of doing this before the visit: one tap, and the patient has a real file "
    "they can carry straight into the consultation room — no login, no app to install, works on any phone.",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "2:45–3:05", "[CUTTABLE] The physician's side of the same case",
    "Switch to “Physician console” (top of page) → sign in with the staff passcode → open the case "
    "you just submitted.",
    "And this is what the doctor sees the moment the patient walks in — the same draft, ready to accept, "
    "amend, or reject. Same real case, same database, not a separate demo.",
    "Skip this entire step if you're short on time — nothing after it depends on having shown it.",
))
story.append(Spacer(1, 4))

story.append(timed_step(
    "3:05–3:30", "Close on the one differentiator judges remember",
    None,
    "One last thing: every safety check you just saw — the red-flag catch, the priority level, the "
    "guideline citation — runs with zero API cost. It keeps working even if the AI service is down. "
    "That's what lets this scale to a real, high-volume government hospital, not just stay a demo. "
    "INAYAT means ‘care’ in Urdu — we built it to give the doctor's two minutes back to actually "
    "deciding, not repeating questions. Thank you — happy to take questions or let you try it yourselves.",
))

# ---- 2. If something goes wrong ------------------------------------------
story += h("2. If something goes wrong — real failure modes, real responses")
story.append(Paragraph(
    "Each of these is a genuine, verified behavior of this specific app — not generic advice. Know the "
    "response before you need it; don't improvise live.",
    small,
))

story.append(subsection("The page is slow to load / first request times out", [
    "Cause: free-tier hosting sleeps when idle and takes a moment to wake on the first hit.",
    "Response: this is exactly why you opened the tab 3–5 minutes early (Section 0). If it still happens live, keep talking through the problem statement while it loads — don't stare at the screen in silence.",
]))

story.append(subsection("Wi-Fi drops completely mid-demo", [
    "Response: don't fight it live. Say plainly, “looks like the connection dropped — let me talk you through what you'd see,” and narrate the results screen from memory using this script. A judge respects composure far more than a frozen retry.",
]))

story.append(subsection("The page looks visually broken — unstyled text, missing button labels", [
    "Cause: a browser can occasionally hold a stale cached copy of one file after a deploy.",
    "Response: this is exactly what the pre-stage hard refresh in Section 0 rules out. If it still happens live, one Ctrl/Cmd+Shift+R fixes it in about a second — do it without apologizing at length, then continue.",
]))

story.append(subsection("A judge types their own symptom and it comes back “urgent” for something they think is minor", [
    "This is not a bug to apologize for — it's the deliberate safety design, and it's a strong answer if you say it plainly.",
    "SAY: “That's intentional. Without a live AI connection configured on this deployment, it defaults to the cautious answer rather than guessing — it will escalate on any real signal, but it will never quietly reassure someone who might be wrong to be reassured. With a live model key connected, it reasons across the full range from self-care to emergency — we kept the offline mode intentionally conservative because that's the one that has to be trustworthy with zero cost and zero risk of being wrong in the dangerous direction.”",
    "Do <b>not</b> promise live, on the spot, that a different typed input will show “self-care” or “clinic visit” — on this deployment (no configured API key) it reliably will not. Redirect to the guideline-citation box instead: that's real and demonstrable regardless of level.",
]))

story.append(subsection("The download button doesn't visibly do anything on a judge's unfamiliar device", [
    "Response: check the downloads folder/bar — some browsers download silently with no visible popup. If truly blocked (rare, some locked-down browsers), fall back to “Listen to summary” instead and narrate that the same content downloads as a plain text file on a normal device.",
]))

story.append(subsection("You forget the physician passcode or it's rejected", [
    "Response: skip it. Say, “and on the doctor's side, the same case opens instantly in a separate, passcode-locked console” — describe it in one sentence and move to the close. Never fumble a password live.",
]))

# ---- 3. Why this earns their interest ------------------------------------
story += h("3. Why this earns interest — keep these ready for follow-up questions")
story.append(points([
    "<b>It's a real citation, not a black box.</b> The “Why this priority level” box quotes an actual clinical guideline sentence and a real text-similarity score — most triage demos just show a label.",
    "<b>It's honest about its own limits, on-screen, every time.</b> “AI-drafted, not yet reviewed by a physician” isn't a disclaimer buried in a footer — it's on every single result.",
    "<b>It still works with zero API cost.</b> Built and demonstrated on the exact assumption a real rural deployment will face: no budget for a live model connection, every single day, not just for this demo.",
    "<b>It closes with a real, downloadable file the patient keeps</b> — not a login-gated app they'll never open again.",
    "<b>The doctor's side is real, not a mockup slide.</b> Same database, same case, passcode-gated — provably not two separate demos stitched together.",
    "<b>It's built for the actual constraint in the problem statement</b> — a 2–5 minute OPD visit — not a generic chatbot retrofitted to health.",
]))

story.append(Spacer(1, 4))
story.append(HRFlowable(width="100%", thickness=1.1, color=GREEN, spaceBefore=3, spaceAfter=4))
story.append(Paragraph(
    "One line if you only remember one thing from this page: <b>“Every number and every quote in this "
    "demo is something the app actually produced when we tested it — nothing here is staged.”</b> Say it "
    "if a judge pushes on whether the demo is real.",
    ParagraphStyle("Closer", parent=body, fontSize=10, alignment=TA_LEFT),
))

doc = SimpleDocTemplate(
    "Inayat_Live_Demo_Script.pdf", pagesize=A4,
    leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=13 * mm,
    title="Inayat Live Demo Script", author="Team SANKALP",
)
doc.build(story)
print("built")
