"""
AYUSH Mode - Dashavidha Pariksha scaffold.

STARTER SCAFFOLD, not a finished clinical module - see
data/ayush/dashavidha_pariksha.json's own honesty note for the full
disclosure. This file only does two honest things right now:

1. Loads the ten parameter definitions from the reference data file.
2. Builds an empty, all-fields-optional AyushAssessment shell a
   physician or future interview module can fill in.

Deliberately does NOT include an AI-drafting agent yet (the way
app/agents/history_intake.py drafts ClinicalHistorySummary) - writing
one before any AYUSH-trained reviewer has checked the parameter
glosses would mean an LLM confidently filling in fields nobody has
verified are even asked correctly. That's a real, named gap (see
docs/sih/SIH26047_STRATEGY.md, Section D item 3), not an oversight.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.schemas import AyushAssessment

DEFAULT_PARAMETERS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "ayush" / "dashavidha_pariksha.json"
)


@dataclass(frozen=True)
class DashavidhaParameter:
    name: str
    gloss: str


def load_dashavidha_parameters(path: Path = DEFAULT_PARAMETERS_PATH) -> list[DashavidhaParameter]:
    """
    Raises FileNotFoundError / json.JSONDecodeError on a missing or
    malformed reference file - never silently returns an empty list,
    since a caller getting zero parameters back should know the
    reference data failed to load, not assume AYUSH mode is simply
    inapplicable to the current case.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [DashavidhaParameter(name=entry["name"], gloss=entry["gloss"]) for entry in raw["parameters"]]


def blank_ayush_assessment() -> AyushAssessment:
    """
    An all-fields-empty AyushAssessment, ready for a physician or a
    future interview module to fill in one parameter at a time.
    Every field defaults to None already (see app/schemas.py) - this
    function exists so callers have one obvious, named entry point
    rather than each having to know AyushAssessment() with no
    arguments is the right way to start one.
    """
    return AyushAssessment()
