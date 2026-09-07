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
    """
    lowered = _WHITESPACE_RUN.sub(" ", text.lower())
    return [term for term in RED_FLAG_TERMS if term in lowered]


def run_intake(patient_input: PatientInput) -> CaseSummary:
    red_flags = scan_red_flags(patient_input.symptom_text)

    return CaseSummary(
        symptom_text=patient_input.symptom_text.strip(),
        age=patient_input.age,
        duration_days=patient_input.duration_days,
        has_image=patient_input.has_image,
        red_flag_terms=red_flags,
    )
