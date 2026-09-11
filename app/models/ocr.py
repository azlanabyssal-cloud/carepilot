"""
Prescription / lab-report OCR.

Deliberately not a trained model - see docs/INTERVIEW_NOTES.md for why
training custom OCR is the wrong call here. Tesseract reads the image
into raw text; that text is handed to the same NLP path the typed
symptom-text intake already uses (app/agents/intake.py), so this module
has exactly one job: image bytes in, clean text out.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

import pytesseract
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class OcrError(RuntimeError):
    """Raised when the image can't be decoded or Tesseract isn't available."""


def _preprocess(image: Image.Image) -> Image.Image:
    """
    Grayscale + mild sharpening + autocontrast. This is standard OCR
    preprocessing advice - but tested empirically against a low-contrast
    synthetic image in this repo, it actually produced a WORSE result
    than raw Tesseract: "AMOXICILLIN" was misread as "ANTONICILLIN"
    after sharpening, a wrong-drug-name failure that matters a lot for
    a health-triage tool specifically. See docs/INTERVIEW_NOTES.md for
    the real numbers - kept in the pipeline as a normalization step
    (grayscale input is a fair Tesseract requirement either way), but
    NOT presented as a proven accuracy improvement, because it isn't
    proven, and it may occasionally hurt. Revisit with a config flag to
    disable sharpening once real prescription-photo samples are available
    to test against, rather than a synthetic low-contrast approximation.
    """
    grayscale = ImageOps.grayscale(image)
    sharpened = grayscale.filter(ImageFilter.SHARPEN)
    return ImageOps.autocontrast(sharpened)


def extract_text(image_bytes: bytes) -> str:
    """
    Raises OcrError on anything that isn't a real, decodable image -
    never returns an empty string silently for a bad upload, since a
    silently empty extraction would look identical to "the prescription
    genuinely had no text," which is a meaningfully different case for
    whatever calls this.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()  # force decode now, not lazily on first use
    except Exception as exc:  # noqa: BLE001 - Pillow raises several distinct types for bad input
        raise OcrError(f"Could not decode image: {exc}") from exc

    processed = _preprocess(image)

    try:
        text = pytesseract.image_to_string(processed, lang="eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError("Tesseract is not installed or not on PATH.") from exc

    cleaned = text.strip()
    if not cleaned:
        logger.warning("OCR produced no text - image may be blank, illegible, or non-text content.")
    return cleaned


# ---------------------------------------------------------------------------
# Structured extraction over OCR'd text (SIH26047 Module B).
#
# Everything below this line is regex/heuristic pattern-matching over plain
# text, not medical NLP and not a trained model. It is deliberately scoped
# that way: a from-scratch clinical NER model is out of reach for the time
# available on this project, and a heuristic that is honestly labeled as
# such is more useful than an ML-flavored black box that quietly gets
# dosages wrong. Treat every function here as a "candidates for a human to
# glance at" tool, not a source of truth a triage decision should be based
# on unattended.
# ---------------------------------------------------------------------------

_DOSAGE_UNIT = r"(?:mg|ml|mcg|iu|tablets?|tabs?|caps?|capsules?)"
_FREQUENCY_ABBR = r"(?:OD|BD|TID|QID|HS|SOS|PRN)"

# A "medication mention" = a capitalized word (the probable drug name,
# possibly preceded by a form prefix like "Tab." which itself is
# capitalized and gets skipped over since it isn't followed by a dosage)
# immediately followed by a number + dosage unit, optionally followed by
# one of the standard frequency abbreviations. The dosage unit is matched
# case-insensitively (OCR output case is unreliable); the frequency
# abbreviation is matched case-sensitively on purpose, since lowercase
# "od"/"hs"/"sos" collide with ordinary English words and would produce
# far more false positives than they're worth.
_MEDICATION_RE = re.compile(
    r"\b[A-Z][A-Za-z]{2,}\b"          # capitalized word - probable drug name
    r"\.?\s+"                          # optional trailing dot ("Tab.") then whitespace
    r"\d{1,4}\s?"                      # dosage number
    rf"(?i:{_DOSAGE_UNIT})\b"          # dosage unit, case-insensitive
    rf"(?:\s*{_FREQUENCY_ABBR}\b)?"    # optional frequency abbreviation
)


def extract_medication_mentions(text: str) -> list[str]:
    """
    Finds medication-like substrings in OCR'd text using regex heuristics:
    a capitalized word followed by a number + dosage unit (mg, ml, mcg, IU,
    tablet(s), tab, cap, capsule(s)), optionally followed by a frequency
    abbreviation (OD, BD, TID, QID, HS, SOS, PRN) - e.g. "Paracetamol 500mg
    BD" out of "Tab. Paracetamol 500mg BD x 5 days".

    This is heuristic pattern-matching, NOT medical NLP. It has no notion
    of what a real drug name is - it will match any capitalized word that
    happens to sit next to a dosage-shaped number, so it will both:
      - miss real medications written in formats it doesn't anticipate
        (all-lowercase names, dosages on a separate line from the name,
        brand names split across an OCR line-wrap, unusual units), and
      - false-positive on non-drug capitalized words that happen to be
        followed by a number-plus-unit pattern (e.g. a clinic name next
        to an unrelated "500ml" elsewhere in the line).
    Downstream code must treat the result as candidates for a human (or a
    later, real pass) to confirm, not as a verified medication list.

    Returns the matched substrings, deduplicated by exact text, in the
    order they first appear in `text`.
    """
    seen: dict[str, None] = {}
    for match in _MEDICATION_RE.finditer(text):
        mention = match.group(0)
        seen.setdefault(mention, None)
    return list(seen)


_MONTHS_FULL = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MONTHS_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
    "Aug", "Sep", "Sept", "Oct", "Nov", "Dec",
]
# Longer names first so the alternation prefers the fuller match when both
# would otherwise apply; Python's re backtracks through alternatives anyway,
# so this is a readability/perf choice, not a correctness requirement.
_MONTH_NAME = "(?:" + "|".join(sorted(set(_MONTHS_FULL + _MONTHS_ABBR), key=len, reverse=True)) + r")\.?"

# Four date shapes, as literally listed in the Module B ask:
#   DD/MM/YYYY, DD-MM-YYYY, "D Month YYYY", "Month D, YYYY"
# Deliberately not merged into anything smarter (no attempt to also catch
# YYYY-MM-DD, two-digit years, ordinals like "5th", etc.) - this extracts
# candidate substrings for the formats asked for, nothing more.
_DATE_RE = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"                # DD/MM/YYYY or DD-MM-YYYY
    rf"|\b\d{{1,2}}\s+{_MONTH_NAME}\s+\d{{4}}\b"          # D Month YYYY
    rf"|\b{_MONTH_NAME}\s+\d{{1,2}},?\s+\d{{4}}\b",       # Month D, YYYY
    re.IGNORECASE,
)


def extract_dates(text: str) -> list[str]:
    """
    Finds date-like substrings in OCR'd text, covering at least:
    DD/MM/YYYY, DD-MM-YYYY, "D Month YYYY" (e.g. "5 January 2025"), and
    "Month D, YYYY" (e.g. "January 5, 2025").

    Returns the RAW matched substrings, as found, in the order they appear
    in `text` - it does not parse them into datetime objects. Reliably
    normalizing arbitrary, possibly OCR-mangled date formats (ambiguous
    DD/MM vs MM/DD, two-digit years, misread digits, unsupported formats
    entirely) into a single comparable representation is a real, separate,
    hard problem - this function does not attempt it. It only tells you
    "here is text that looks like a date," not "here is what date this is."
    Callers that need comparable dates must parse these candidates
    themselves, with whatever locale/format assumptions their context
    justifies.
    """
    return [match.group(0) for match in _DATE_RE.finditer(text)]


@dataclass(frozen=True)
class LabValue:
    """
    One extracted investigation result: a test name, its reported value
    and unit, and the reference range the report itself stated - never
    a range this project supplies from an external "normal values"
    table, since a report's own stated range is the one the physician
    who ordered it is actually comparing against (different labs use
    different reference ranges for the same test).
    """

    test_name: str
    value: float
    unit: str
    range_low: float
    range_high: float
    raw_text: str

    @property
    def is_abnormal(self) -> bool:
        """True if the reported value falls outside the report's own stated range."""
        return self.value < self.range_low or self.value > self.range_high


# A lab-report line has a much more varied "test name" shape than a
# medication line (multi-word names, occasional parenthetical qualifiers
# like "Blood Glucose (Fasting)") - too varied to anchor on the name the
# way _MEDICATION_RE anchors on a single capitalized word. Anchored
# instead on the one highly distinctive, low-false-positive suffix a lab
# line has that ordinary prose doesn't: a numeric value immediately
# followed by a parenthesized reference range ("(13.0-17.0)",
# "(4000 to 11000)", "(Normal: 0.6-1.2)"). This deliberately does NOT
# match a report line with only a single-sided bound ("< 200", "> 40") -
# a real, named scope limit, not an oversight, the same honesty standard
# extract_medication_mentions already documents for its own blind spots.
_LAB_VALUE_RE = re.compile(
    r"(?P<name>[A-Z][A-Za-z()/ .]{1,40}?)"
    r"\s*[:\-]?\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[A-Za-z/%µ.]{0,10})?\s*"
    r"\(\s*(?:Normal\s*[:\-]?\s*)?"
    r"(?P<low>\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<high>\d+(?:\.\d+)?)\s*\)"
)


def extract_lab_values(text: str) -> list[LabValue]:
    """
    Finds investigation-result lines in OCR'd text: a test name, a
    numeric value, an optional unit, and a parenthesized reference
    range - e.g. "Hemoglobin: 9.2 g/dL (13.0-17.0)" out of a lab report.

    Heuristic pattern-matching, NOT medical NLP, the same discipline
    extract_medication_mentions() already documents: it has no notion of
    what a real lab test is, so it will match any name-shaped text
    immediately followed by a value-then-range pattern, and it will miss
    real results written in formats it doesn't anticipate (a range on a
    separate line, a single-sided bound, a range expressed as "<200"
    rather than "(x-y)"). Downstream code must treat the result as
    candidates for a human to confirm, never as a verified lab report.

    Returns one LabValue per match, in the order they appear in `text`.
    A malformed numeric match (which the regex's own \\d+(?:\\.\\d+)?
    groups should never actually produce) would raise ValueError from
    float() rather than silently skip the line - a report claiming a
    number it then can't parse as one is a bug worth surfacing, not
    hiding.

    Real, measured accuracy note, tested against two actual Tesseract
    OCR runs (not asserted from reading the regex) - same honesty
    standard as Day 2's OCR-preprocessing finding. Against a rendered
    lab-report image using a real scalable font at a reasonable
    resolution (DejaVu Sans Mono, 28pt, 1400x500px), extraction was
    exact: correct values, correct ranges, correct abnormal-flagging.
    Against the same text rendered small with PIL's tiny built-in
    bitmap font (500x120px, the same low-effort rendering
    tests/test_ocr.py's own _render_text_image() helper uses for its
    other tests), Tesseract corrupted several digits - "9.2" read as
    "8.2", "13.0-17.0" read as "130-170", "150000-410000" read as
    "16000-41000" - and the structured extraction faithfully reported
    those wrong numbers, including a wrong abnormal-flag verdict on the
    corrupted Hemoglobin value (still correctly flagged as abnormal by
    coincidence, since 8.2 is also below 130-170, but that's luck, not
    correctness). The regex itself did not fail in either case - it
    extracted exactly what Tesseract handed it - so the real, unresolved
    risk here is OCR accuracy on the numbers themselves, not the
    extraction logic. This is exactly Module B's own named risk (see
    docs/sih/SIH26047_STRATEGY.md, Section D item 4: "OCR on real
    handwritten prescriptions will underperform whatever the demo shows
    on a clean sample") - stated plainly here rather than only
    demonstrated on the flattering high-resolution case.
    """
    results = []
    for match in _LAB_VALUE_RE.finditer(text):
        results.append(
            LabValue(
                test_name=match.group("name").strip(),
                value=float(match.group("value")),
                unit=(match.group("unit") or "").strip(),
                range_low=float(match.group("low")),
                range_high=float(match.group("high")),
                raw_text=match.group(0),
            )
        )
    return results


def flag_abnormal_lab_values(lab_values: list[LabValue]) -> list[LabValue]:
    """
    Filters to only the results outside their own report's stated
    range - Module B's "abnormal-value highlighting" requirement.
    Deliberately a plain filter over LabValue.is_abnormal rather than a
    second, possibly-drifting definition of "abnormal" - one rule, used
    in both places it's checked.
    """
    return [lv for lv in lab_values if lv.is_abnormal]


def build_document_timeline(documents: list[tuple[str, str]]) -> list[dict]:
    """
    Takes a list of (document_label, ocr_text) pairs and returns a list of
    {"label": ..., "text": ..., "dates_found": [...]} dicts, where
    "dates_found" is the output of extract_dates() on that document's text.

    The list is ordered so that documents where extract_dates() found at
    least one date candidate come before documents where it found none,
    using a stable partition - relative order is preserved within each of
    the two groups.

    This is a best-effort ORDERING AID, not automated chronological
    sorting. Because extract_dates() intentionally returns raw matched
    strings rather than parsed datetime objects (see its docstring), there
    is nothing here to compare two dates against each other, so documents
    are not actually sorted by when they occurred - only grouped into
    "has a date candidate on it" vs. "doesn't." A human still has to look
    at dates_found and decide the real chronological order; this just
    saves them from having to first sift out the documents with no date
    on them at all.
    """
    dated = [
        {"label": label, "text": text, "dates_found": extract_dates(text)}
        for label, text in documents
    ]
    with_dates = [entry for entry in dated if entry["dates_found"]]
    without_dates = [entry for entry in dated if not entry["dates_found"]]
    return with_dates + without_dates
