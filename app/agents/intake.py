"""
Intake Agent.

Job: turn raw patient input into a CaseSummary the downstream agents can
reason over. Two things happen here, deliberately kept separate:

1. Normalization - nothing clever, just shaping the data.
2. A deterministic, rule-based red-flag scan - this runs BEFORE any LLM
   or ML model touches the case. See docs/INTERVIEW_NOTES.md, entry 1,
   for why this exists and isn't redundant with the later
   Guideline-Verification agent.
"""

import re
import unicodedata
from difflib import SequenceMatcher

from app.schemas import CaseSummary, PatientInput

# Deliberately small and easy to audit. Sourced from common emergency
# red-flag terms in public primary-care triage guidance (ICMR/WHO-style
# first-contact protocols) - not invented, and each one should be
# traceable back to a real guideline document before this ships.
RED_FLAG_TERMS = [
    "chest pain",
    "difficulty breathing",
    "shortness of breath",
    "unconscious",
    "unresponsive",
    "severe bleeding",
    "seizure",
    "sudden weakness",
    "slurred speech",
    "high fever with stiff neck",
    "not breathing",
]


_WHITESPACE_RUN = re.compile(r"\s+")
_WORD_TOKEN = re.compile(r"[a-z0-9]+")

# Calibrated empirically against ~30 realistic positive (typo/ASR-error)
# and negative (ordinary unrelated sentences, including ones containing
# common short words like "pain"/"fever"/"neck" in isolation) test
# sentences before being set - see docs/DAILY_LOG.md, 12 Sep 2026 entry,
# for the reasoning and the false-positive traps a looser threshold or a
# per-word-only check (no sequence requirement) walked straight into.
_FUZZY_RATIO_THRESHOLD = 0.75
_FUZZY_MIN_WORD_LENGTH = 4  # below this, real short words collide too easily (e.g. "main"/"pain"/"rain" all differ by one letter) - exact match only
_FUZZY_MAX_GAP = 2  # words allowed between consecutive term-words, for code-switched input ("chest mein bahut pain hai")


def _word_fuzzy_matches(term_word: str, candidate: str) -> bool:
    if term_word == candidate:
        return True
    if len(term_word) < _FUZZY_MIN_WORD_LENGTH:
        return False
    return SequenceMatcher(None, term_word, candidate).ratio() >= _FUZZY_RATIO_THRESHOLD


def _term_matches_from(term_words: list[str], tokens: list[str], start: int) -> bool:
    position = start
    for term_word in term_words:
        matched_at = None
        for offset in range(_FUZZY_MAX_GAP + 1):
            index = position + offset
            if index < len(tokens) and _word_fuzzy_matches(term_word, tokens[index]):
                matched_at = index
                break
        if matched_at is None:
            return False
        position = matched_at + 1
    return True


def _scan_fuzzy(lowered: str) -> list[str]:
    """
    Tokenizes the already-whitespace/Cf-normalized text into words and,
    for each RED_FLAG_TERMS entry, slides through the token list looking
    for that term's words in order - each individual word either exact
    or a close spelling variant (_word_fuzzy_matches), with up to
    _FUZZY_MAX_GAP unrelated tokens allowed between consecutive term-
    words so a code-switched filler word ("chest MEIN pain", "chest
    BAHUT JYADA pain") doesn't break the match.

    Deliberately NOT a per-word check run independently of position -
    that was tried first and rejected: "pain" alone at this same fuzzy
    threshold also matches "main", "rain", "gain", and "pair", all
    ordinary words with no connection to a chest complaint. Requiring
    the term's OTHER word(s) to also match nearby, in order, is what
    keeps the false-positive rate at zero across every adversarial
    sentence tested (see the calibration note above) while still
    catching real single-character typos and transpositions.
    """
    tokens = _WORD_TOKEN.findall(lowered)
    matched = []
    for term in RED_FLAG_TERMS:
        term_words = term.split()
        if any(_term_matches_from(term_words, tokens, start) for start in range(len(tokens))):
            matched.append(term)
    return matched


def scan_red_flags(text: str) -> list[str]:
    """Case-insensitive substring match against the red-flag term list.

    Substring match, not an ML classifier, is the point: it is slow to
    extend and it will miss paraphrases ("can't catch my breath" won't
    match "difficulty breathing"). What it will never do is silently
    fail on a term that IS in the list - that's the trade this project
    makes on purpose. The Triage-Reasoning agent (next session) covers
    paraphrase and nuance; this layer exists only to guarantee that a
    known emergency term is never missed because a model had a bad day.

    Real bug, found by simulating realistic input irregularity rather
    than assuming clean single-space text: every multi-word term in
    RED_FLAG_TERMS ("chest pain", "difficulty breathing", "severe
    bleeding", "sudden weakness", "slurred speech", "high fever with
    stiff neck", "not breathing") was originally matched with a plain
    `term in lowered` substring check, which only matches the exact
    single-space spelling. A double space from a mobile keyboard, a
    newline from copy-pasted or line-wrapped text, or a tab from an
    OCR/voice-transcription artifact all break that match silently -
    "chest  pain" (two spaces) is not a substring of "chest pain" - so
    the case fell through to the Triage-Reasoning Agent instead of
    short-circuiting to EMERGENCY, defeating the whole point of Entry
    1's "two independent mechanisms" defense in depth. Fixed by
    collapsing any run of whitespace (spaces, tabs, newlines) to a
    single space before matching - single-word terms are unaffected,
    and an unrelated phrase with irregular whitespace still correctly
    produces no match (test_scan_red_flags_still_misses_unrelated_text_after_whitespace_normalization).

    Second real bug, found one layer further by combining two lessons
    this project had already learned separately (docs/INTERVIEW_NOTES.md,
    Day 14's whitespace fix above, and Days 8-10's Unicode-Cf-format-
    character findings in app/schemas.py) but had never applied together:
    the whitespace-collapse fix above only touches characters where
    str.isspace() is True (Unicode category "Zs" and friends). Unicode
    *format* characters (category "Cf" - ZERO WIDTH SPACE U+200B, ZERO
    WIDTH NON-JOINER U+200C, ZERO WIDTH JOINER U+200D, the BOM/ZERO WIDTH
    NO-BREAK SPACE U+FEFF, WORD JOINER U+2060, etc.) are not whitespace
    and pass straight through _WHITESPACE_RUN untouched. These are a
    real, unremarkable artifact of predictive-text/autocorrect
    keyboards, IMEs, and text copy-pasted from formatted documents or
    chat apps (commonly inserted right at word-wrap points, i.e. exactly
    where a real space already is) - the same realistic-input-shape
    standard Day 14's own fix was held to. A zero-width character sitting
    next to or in place of the space inside a multi-word term - "chest​
    pain", "chest ​pain", or "chest​pain" with no visible space at
    all - silently defeated the match exactly the way Day 14's untreated
    double-space case did, for the same reason: the collapsed string
    still isn't the exact spelling `term in lowered` requires. Fixed by
    treating any Unicode category "Cf" character as whitespace-equivalent
    before collapsing, not just true whitespace - reusing the same "Cf is
    not real content" judgment app/schemas.py's `_visible_length` already
    encodes, applied here to matching instead of length-checking.

    Third real gap, found 12 Sep 2026 by testing against realistic
    MISSPELLED and code-switched input rather than just realistic
    whitespace - a fundamentally different failure class from the two
    above, and arguably more consequential: "cheast pain", "difficulty
    breething", "unconcious", "sever bleeding", and "chest mein bahut
    pain hai" (Hindi-English code-switched, PS26047's own named target
    population) all defeated the plain-substring check completely, with
    zero warning - exactly the class of input SIH26047's Module A names
    explicitly ("multi-accent voice capture," "elderly, low-literacy"
    patients) and exactly what a live judge poking at this system with
    a real typo or a real accent would try. Fixed additively: the exact
    substring check above is completely unchanged and still runs first
    (nothing about the two whitespace/Cf fixes above was touched), and
    _scan_fuzzy() now ALSO runs over the same normalized text as a
    second, independent pass, catching single-character typos,
    transpositions, and up to two intervening code-switched words
    between a term's own words. Its own docstring covers the real
    false-positive trap a naive version of this fix walked into first
    (fuzzy-matching "pain" in isolation also matches "main"/"rain"/
    "gain"/"pair") and how requiring in-order, nearby multi-word
    sequences avoids it. Results are merged and de-duplicated, RED_FLAG_TERMS
    order preserved, so callers see no difference in shape from before -
    only recall improves.
    """
    normalized = "".join(
        " " if ch.isspace() or unicodedata.category(ch) == "Cf" else ch for ch in text.lower()
    )
    lowered = _WHITESPACE_RUN.sub(" ", normalized)
    exact_matches = {term for term in RED_FLAG_TERMS if term in lowered}
    fuzzy_matches = set(_scan_fuzzy(lowered))
    all_matches = exact_matches | fuzzy_matches
    return [term for term in RED_FLAG_TERMS if term in all_matches]


def run_intake(patient_input: PatientInput) -> CaseSummary:
    red_flags = scan_red_flags(patient_input.symptom_text)

    return CaseSummary(
        symptom_text=patient_input.symptom_text.strip(),
        age=patient_input.age,
        duration_days=patient_input.duration_days,
        has_image=patient_input.has_image,
        red_flag_terms=red_flags,
    )
