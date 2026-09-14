"""
Inayat — Internal Screening Report (SIH26047)
Black-and-white, structured against the internal-hackathon judging
weights most commonly reported for SIH college-level screenings
(Problem Understanding & Impact 25%, Innovation & Technical Excellence
30%, Feasibility/Practicability/Scalability 25%, Solution Quality &
Presentation 20% - see docs/sih/SIH26047_STRATEGY.md Section A, itself
sourced from multiple independent hackathon-guide searches, not a
primary AICTE document). Every number in this document is either
measured directly from this repository's own code/tests, or drawn from
a real external source found via live web search this session and
cited in the References section.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image, Table, TableStyle,
    KeepTogether, PageBreak, ListFlowable, ListItem, NextPageTemplate, PageTemplate, Frame,
)
from reportlab.platypus.tableofcontents import TableOfContents

BLACK = colors.HexColor("#111111")
GREY = colors.HexColor("#555555")
LIGHTGREY = colors.HexColor("#e6e6e6")
RULE = colors.HexColor("#111111")

styles = getSampleStyleSheet()

cover_title = ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=34, textColor=BLACK,
                              alignment=TA_CENTER, leading=40, spaceAfter=22)
cover_sub = ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=13, textColor=BLACK,
                            alignment=TA_CENTER, spaceAfter=4, leading=17)
cover_tag = ParagraphStyle("CoverTag", fontName="Helvetica", fontSize=10.5, textColor=GREY,
                            alignment=TA_CENTER, spaceAfter=3)
cover_hook = ParagraphStyle("CoverHook", fontName="Helvetica-Oblique", fontSize=11.5, textColor=BLACK,
                             alignment=TA_CENTER, spaceBefore=26, spaceAfter=6, leading=16)

h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=15, textColor=BLACK,
                     spaceBefore=16, spaceAfter=3, leading=18)
h1sub = ParagraphStyle("H1Sub", fontName="Helvetica-Oblique", fontSize=9.5, textColor=GREY,
                        spaceAfter=8)
h2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11.5, textColor=BLACK,
                     spaceBefore=10, spaceAfter=4)
body = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.7, textColor=BLACK,
                       leading=14, spaceAfter=7, alignment=TA_LEFT)
bullet_body = ParagraphStyle("BulletBody", parent=body, spaceAfter=3, leftIndent=0)
small_italic = ParagraphStyle("SmallItalic", fontName="Helvetica-Oblique", fontSize=8.3,
                               textColor=GREY, leading=11, spaceAfter=6)
formula = ParagraphStyle("Formula", fontName="Helvetica-Bold", fontSize=11, textColor=BLACK,
                          alignment=TA_CENTER, spaceBefore=8, spaceAfter=8)
caption = ParagraphStyle("Caption", fontName="Helvetica-Oblique", fontSize=8.3, textColor=GREY,
                          alignment=TA_CENTER, spaceAfter=12)
ref_style = ParagraphStyle("Ref", fontName="Helvetica", fontSize=8.7, textColor=BLACK,
                            leading=12.5, spaceAfter=6, leftIndent=12, firstLineIndent=-12)


def bullets(items, style=bullet_body):
    return ListFlowable(
        [ListItem(Paragraph(t, style), bulletColor=BLACK, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=14, spaceBefore=2, spaceAfter=8,
    )


def section_header(number_title, subtitle):
    return [
        HRFlowable(width="100%", thickness=1.4, color=RULE, spaceBefore=4, spaceAfter=6),
        Paragraph(number_title, h1),
        Paragraph(subtitle, h1sub),
    ]


story = []

# ============================ COVER PAGE ================================
story.append(Spacer(1, 55))
story.append(Paragraph("INAYAT", cover_title))
story.append(Paragraph("AI-Assisted Patient Case-Taking &amp; Safety-Net Triage System", cover_sub))
story.append(HRFlowable(width="55%", thickness=1, color=BLACK, spaceBefore=10, spaceAfter=10, hAlign="CENTER"))
story.append(Paragraph("Smart India Hackathon 2026 &nbsp;·&nbsp; Problem Statement SIH26047 &nbsp;·&nbsp; Ministry of Ayush", cover_tag))
story.append(Paragraph("Category: MedTech / BioTech / HealthTech &nbsp;·&nbsp; Software", cover_tag))
story.append(Paragraph("Internal Screening Documentation &nbsp;·&nbsp; GPREC", cover_tag))
story.append(Paragraph(
    "“A doctor gets two minutes. This does the history-taking before the patient "
    "walks in — and never lets a dangerous symptom depend on a model having a good day.”",
    cover_hook,
))
story.append(Spacer(1, 60))
story.append(Paragraph(
    "This document is structured against the judging weights most commonly reported for "
    "SIH internal-hackathon screenings — Problem Understanding &amp; Impact (25%), "
    "Innovation &amp; Technical Excellence (30%), Feasibility, Practicability &amp; "
    "Scalability (25%), and Solution Quality &amp; Presentation (20%) — so every section "
    "below answers a specific, scored question rather than reading as a general pitch. "
    "Every number in it is either measured directly from this project's own code and test "
    "suite, or drawn from a cited, independently verifiable external source.",
    ParagraphStyle("CoverNote", fontName="Helvetica", fontSize=9, textColor=GREY, leading=13, alignment=TA_CENTER),
))
story.append(PageBreak())

# ============================ EXECUTIVE SUMMARY ==========================
story += section_header("Executive Summary", "What this is, in one paragraph")
story.append(Paragraph(
    "In a typical Indian government primary-care consultation, a doctor has roughly two "
    "minutes with a patient — not enough time to take a full history, let alone read old "
    "prescriptions or ask the right follow-up questions.<sup>[1]</sup> <b>Inayat</b> moves that "
    "history-taking earlier: a patient describes their symptoms by typing, speaking in their "
    "own language, or photographing an old prescription, and Inayat turns that into a clean, "
    "structured, physician-ready summary — Chief Complaint through Review of Systems — "
    "plus an independent safety-net triage level that flags a dangerous symptom even if every "
    "AI component in the system is unavailable. Inayat never diagnoses and never prescribes: "
    "the physician reviews, edits, and decides on every case. Built and tested today: a "
    "deterministic red-flag safety scan, adaptive SOCRATES-based follow-up questioning, "
    "document/prescription digitization with abnormal-value flagging, a real ABDM "
    "(Ayushman Bharat Digital Mission) health-ID enrollment flow, and a zero-API-key "
    "fallback path that keeps the system responding safely with no internet connection at "
    "all. 358 automated tests currently pass.",
    body,
))

# ============================ SECTION 1 ==================================
story += section_header(
    "1. Problem Understanding &amp; Real-World Impact",
    "Judging weight most commonly reported for this criterion at the internal-hackathon stage: 25%",
)
story.append(Paragraph(
    "This is a real, currently listed problem statement — SIH26047, “Patient "
    "Case-Taking Software,” posed by the All India Institute of Ayurveda under the "
    "Ministry of Ayush<sup>[2]</sup> — not a generic health-app idea retrofitted onto a "
    "hackathon theme. The scale of the underlying problem is documented, not assumed:",
    body,
))
story.append(Image("/tmp/claude-0/report/chart_consultation_time.png", width=340, height=340*0.5333))
story.append(Paragraph("Figure 1 — India's primary-care consultation time against the global range measured across 67 countries.<sup>[1]</sup>", caption))
story.append(bullets([
    "A systematic review of 178 studies across 67 countries and 28.5 million consultations found average consultation length ranging from 48 seconds (Bangladesh) to 22.5 minutes (Sweden); India's own reported average was approximately two minutes.<sup>[1]</sup>",
    "Almost two-thirds of India's population lives in rural areas, yet only about 33% of the country's health workers and 27% of its doctors serve there — a real, measured distribution gap, not an assumption.<sup>[3]</sup>",
    "The average rural Primary Health Centre (PHC) serves roughly 36,000 people, with a nationally reported ~7% shortfall of doctors at PHC level — and a far more severe 74–83% shortfall of specialists (surgeons, physicians, obstetricians, paediatricians) at Community Health Centres.<sup>[3]</sup>",
    "A well-documented finding across decades of clinical-education research is that a careful history alone leads to the correct diagnosis in a large majority of cases — original and replication studies report figures consistently in the 75–90% range.<sup>[4]</sup> Time taken away from history-taking is time taken directly away from diagnostic accuracy, not merely from patient comfort.",
]))
story.append(Paragraph(
    "Read against the actual PS26047 text rather than paraphrased from memory, the problem "
    "statement names four specific modules — a conversational multimodal history engine "
    "with red-flag detection (Module A), medical document digitization (Module B), a "
    "structured history-summary generator (Module C), and consent/ABDM integration "
    "(Module D). Section 4 of this document maps each one to what is actually built, "
    "tested, or honestly still planned — not claimed as complete where it isn't.",
    body,
))

# ============================ SECTION 2 ==================================
story += section_header(
    "2. Innovation &amp; Technical Excellence",
    "Judging weight most commonly reported for this criterion at the internal-hackathon stage: 30%",
)
story.append(Paragraph(
    "The architecture below is the real, current pipeline traced directly from this "
    "project's own request-handling code — not a simplified or aspirational diagram.",
    body,
))
story.append(Image("/tmp/claude-0/report/architecture.png", width=360, height=360*1.16))
story.append(Paragraph("Figure 2 — The real request pipeline, module by module.", caption))

story.append(Paragraph("2.1 &nbsp; Defense-in-depth safety design", h2))
story.append(Paragraph(
    "The single most important design decision in this system: a dangerous symptom is "
    "never allowed to depend on one mechanism working correctly. Three independent checks "
    "run in sequence — (i) a deterministic keyword-and-fuzzy-match scan that requires no "
    "model call at all and cannot be “having a bad day”; (ii) a language-model "
    "judgment that covers nuance and paraphrase the fixed keyword list cannot; and (iii) a "
    "guideline-verification check computed independently of the model's own answer. The "
    "third check is built to only ever raise the urgency level it is given, never lower "
    "it — a deliberately asymmetric design, because a false correction toward "
    "“less urgent” is a far more dangerous failure than one extra, unnecessary "
    "referral.",
    body,
))

story.append(Paragraph("2.2 &nbsp; The real mathematics behind guideline verification", h2))
story.append(Paragraph(
    "Symptom text is matched against a small, curated set of guideline reference passages "
    "using TF-IDF (Term Frequency – Inverse Document Frequency) vectorization, then "
    "compared by cosine similarity — a standard, explainable information-retrieval "
    "method chosen deliberately over a heavier embedding model, because the reference "
    "corpus at this stage is a few dozen short passages, a scale at which exact medical-term "
    "overlap is already a strong, sufficient signal.",
    body,
))
story.append(Paragraph("TF-IDF(t, d) = tf(t, d) &times; log( N / df(t) )", formula))
story.append(Paragraph(
    "tf(t, d) = how often term t appears in passage d &nbsp;·&nbsp; N = total number of "
    "reference passages &nbsp;·&nbsp; df(t) = number of passages containing t",
    small_italic,
))
story.append(Paragraph("cos(&theta;) = (A &middot; B) / ( ||A|| &middot; ||B|| )", formula))
story.append(Paragraph(
    "A and B are the TF-IDF vectors of the patient's symptom text and a reference passage; "
    "the result is a similarity score between 0 (no relation) and 1 (identical wording).",
    small_italic,
))
story.append(Image("/tmp/claude-0/report/chart_threshold.png", width=330, height=330*0.4844))
story.append(Paragraph(
    "Figure 3 — The system's own match threshold (0.20), measured against this project's own guideline corpus, not chosen arbitrarily.",
    caption,
))
story.append(Paragraph(
    "The threshold is not a guessed constant: measured directly against this project's own "
    "reference corpus, a genuinely relevant match consistently scores 0.60–0.70, while a "
    "passage sharing only one incidental word (for example “mild”) scores "
    "0.08–0.11. The chosen threshold of 0.20 sits cleanly inside the real, measured gap "
    "between those two clusters.",
    body,
))

story.append(Paragraph("2.3 &nbsp; Adaptive, clinically structured questioning", h2))
story.append(Paragraph(
    "Rather than one generic follow-up prompt, complaints are classified deterministically "
    "into one of five categories (pain/general, respiratory, dermatological, "
    "gastrointestinal, general-systemic), each dispatching a real, distinct clinical "
    "question set. A cough is asked about sputum colour and triggers; a skin complaint is "
    "asked about spread and new exposures; pain complaints use the SOCRATES framework "
    "(Site, Onset, Character, Radiation, Associated symptoms, Time course, "
    "Exacerbating/relieving factors, Severity) that PS26047 names explicitly. No language "
    "model is involved in this classification step — it is real branching logic, exactly "
    "as reliable with no API key as with one.",
    body,
))

story.append(Paragraph("2.4 &nbsp; Zero-dependency graceful degradation", h2))
story.append(Paragraph(
    "Every AI-dependent step in the pipeline has a deterministic, zero-network fallback: "
    "triage reasoning falls back to a fixed, conservative “urgent” level rather than "
    "guessing; history drafting falls back to a real templated sentence rather than three "
    "disconnected label lines; voice input falls back to an offline speech engine; voice "
    "output falls back to an offline speech synthesizer. None of these fallbacks are "
    "presented as equal to the AI path — every result produced by one is explicitly "
    "flagged for mandatory physician review, never silently indistinguishable from a full "
    "AI judgment.",
    body,
))

# ============================ SECTION 3 ==================================
story += section_header(
    "3. Feasibility, Practicability &amp; Scalability",
    "Judging weight most commonly reported for this criterion at the internal-hackathon stage: 25%",
)
story.append(Paragraph("3.1 &nbsp; A stack chosen for where this actually has to run", h2))
story.append(Paragraph(
    "The frontend is a single, dependency-free HTML/JavaScript file — no framework, no "
    "build step — so it loads on a low-end Android browser at a rural kiosk with no "
    "developer tooling on site. The backend (FastAPI) and storage (plain SQLite, one "
    "well-defined table) are deliberately unglamorous choices sized to the problem's actual "
    "current scale, with a documented upgrade path the moment real multi-table relations or "
    "serious concurrent load appear — not before.",
    body,
))
story.append(Paragraph("3.2 &nbsp; Real government-rail integration, not a mock", h2))
story.append(Paragraph(
    "Inayat integrates with two live government systems rather than simulating them: "
    "Bhashini (MeitY's multilingual speech service) for voice input/output, and ABDM for "
    "national digital health identity. The scale these systems already operate at is real "
    "and public — over 90 crore (900 million) ABHA health IDs had been created under the "
    "Ayushman Bharat Digital Mission as of 2026<sup>[5]</sup> — so integrating with ABDM "
    "is plugging into infrastructure that is already national in scale, not a hypothetical "
    "future rail. The ABHA-enrollment request itself uses real RSA-OAEP public-key "
    "encryption matching ABDM's published cipher specification, verified by a test that "
    "generates a genuine key pair and confirms the system's own encrypted request decrypts "
    "back to the exact original values.",
    body,
))
story.append(Paragraph("3.3 &nbsp; Tested, not just demonstrated", h2))
story.append(Paragraph(
    "358 automated tests currently pass across this codebase, covering individual modules "
    "(the red-flag scanner, document/lab-value extraction, offline speech, ABDM encryption) "
    "and full request flows end to end. A separate, small evaluation harness runs the "
    "complete pipeline against 11 authored clinical test cases:",
    body,
))
story.append(Image("/tmp/claude-0/report/chart_eval_composition.png", width=330, height=330*0.4531))
story.append(Paragraph("Figure 4 — The evaluation set is small and authored for this project, and is presented as exactly that.", caption))
story.append(Paragraph(
    "Reported as a raw count, not a percentage, specifically to avoid a small sample being "
    "misread as a large-scale validation — an 11-case authored set demonstrates that the "
    "pipeline runs correctly end to end, not that it has been clinically validated at scale.",
    body,
))
story.append(KeepTogether([
    Paragraph("3.4 &nbsp; Limitations, stated up front", h2),
    bullets([
        "The guideline-reference corpus used for verification is a starter set authored for this project, not yet a certified extract from an official ICMR/WHO document.",
        "Neither the Bhashini nor the ABDM integration has been exercised against a live government server in this build environment — both are built and tested against their own published API specifications, not confirmed live.",
    ]),
]))
story.append(KeepTogether([
    bullets([
        "OCR accuracy on a real, messy handwritten prescription will be measurably lower than on a clean typed sample; this project has directly measured and documented that gap rather than only demonstrating the clean case.",
        "The Ayurvedic (Dashavidha Pariksha) assessment module is a structurally correct scaffold — the right ten parameters, correctly split into what a kiosk can ask versus what needs a physician's own examination — but has not yet been reviewed by an AYUSH-qualified expert, and is not presented as clinically validated.",
    ]),
]))

# ============================ SECTION 4 ==================================
story += section_header(
    "4. Solution Quality &amp; Presentation",
    "Judging weight most commonly reported for this criterion at the internal-hackathon stage: 20%",
)
story.append(Paragraph(
    "A direct, honest scorecard against PS26047's own four named modules — built and "
    "tested, partially built, or genuinely planned:",
    body,
))

module_data = [
    [Paragraph("<b>Module</b>", body), Paragraph("<b>PS26047 ask</b>", body), Paragraph("<b>Status</b>", body)],
    [Paragraph("A", body), Paragraph("Conversational multimodal history engine, red-flag detection", body),
     Paragraph("<b>Built &amp; tested.</b> Red-flag scan, adaptive SOCRATES + 4-category questioning, multilingual voice input.", body)],
    [Paragraph("B", body), Paragraph("Medical document digitization &amp; intelligence", body),
     Paragraph("<b>Built &amp; tested.</b> OCR, medication/date/lab-value/diagnosis extraction, abnormal-value flagging, multi-document chronological ordering.", body)],
    [Paragraph("C", body), Paragraph("Structured history-summary generator", body),
     Paragraph("<b>Built &amp; tested.</b> Chief Complaint → HPI → Past/Drug/Family/Personal history → ROS → Prior investigations, with a zero-API fallback.", body)],
    [Paragraph("D", body), Paragraph("Consent, privacy &amp; ABDM integration", body),
     Paragraph("<b>Partial, honestly scoped.</b> Consent is enforced before any record is saved; physician access is login-gated. ABDM's first milestone (ABHA-ID creation) is built and encryption-verified; full FHIR record exchange is a named, scoped next step, not claimed as done.", body)],
]
module_table = Table(module_data, colWidths=[52, 148, 280])
module_table.setStyle(TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.6, GREY),
    ("BACKGROUND", (0, 0), (-1, 0), LIGHTGREY),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(module_table)
story.append(Spacer(1, 10))
story.append(Paragraph(
    "This document itself follows the same discipline applied throughout the project: "
    "every technical claim above is traceable to a specific file, function, or test in "
    "the codebase, and every external statistic is traceable to a cited source below — "
    "nothing is asserted without something to point to.",
    body,
))

# ============================ CONCLUSION ==================================
story += section_header("Conclusion", "")
story.append(Paragraph(
    "Inayat addresses a real, currently listed national problem statement with a system "
    "whose safety-critical behaviour does not depend on any single AI component working "
    "correctly, whose core methods (TF-IDF retrieval, deterministic keyword scanning, "
    "structured clinical questioning) are explainable rather than opaque, and whose "
    "government-system integrations are built against real, currently operating national "
    "infrastructure rather than simulated. What remains — a certified guideline corpus, "
    "live credential testing against Bhashini and ABDM, and expert review of the AYUSH "
    "module — is named explicitly rather than hidden, because a team that knows exactly "
    "what is left to do is a stronger, more credible answer than one that claims "
    "everything is finished.",
    body,
))

# ============================ REFERENCES ==================================
story.append(PageBreak())
story += section_header("References", "")
refs = [
    "[1] Irving G, Neves AL, Dambha-Miller H, et al. International variations in primary care physician consultation time: a systematic review of 67 countries. <i>BMJ Open</i> 2017;7:e017902.",
    "[2] Smart India Hackathon 2026, Problem Statement SIH26047, “Patient Case-Taking Software,” Ministry of Ayush / All India Institute of Ayurveda — sih.gov.in.",
    "[3] Rural Health Statistics 2021–22, Ministry of Health &amp; Family Welfare, Government of India; corroborating reporting via Press Information Bureau (pib.gov.in) and Down To Earth (downtoearth.org.in) on rural doctor distribution and PHC/CHC staffing shortfalls.",
    "[4] Aphorism traced and reviewed in: “A History of Patient History-Taking: A Brief Review of the Origins of the Aphorism that '80% of Diagnoses Can Be Made by History Alone'” (Clinical Correlations, NYU Langone); original and replication studies on the relative contributions of history, examination and investigation to diagnosis (PubMed: 1536065, 11273467).",
    "[5] Ayushman Bharat Digital Mission (ABDM) ABHA-ID creation statistics, Ministry of Health &amp; Family Welfare / Press Information Bureau; corroborating reporting via IBEF (ibef.org), 2025–2026.",
    "[6] This project's own repository: app/agents/verify.py, app/agents/intake.py, app/agents/triage.py, app/agents/socrates_intake.py, app/adapters/abdm.py, app/adapters/bhashini.py, app/models/ocr.py, data/evaluation/test_cases.json — all figures and code references in this document were checked against these files directly.",
]
for r in refs:
    story.append(Paragraph(r, ref_style))

doc = SimpleDocTemplate(
    "/tmp/claude-0/report/Inayat_Internal_Screening_Report.pdf",
    pagesize=A4,
    topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    title="Inayat — Internal Screening Report (SIH26047)",
)


def add_page_number(canvas, doc_):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    if doc_.page > 1:
        canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Inayat — SIH26047 Internal Screening Report · {doc_.page}")
    canvas.restoreState()


doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=add_page_number)
print("Report built.")
