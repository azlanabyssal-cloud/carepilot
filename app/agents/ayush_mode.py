"""
AYUSH Mode - Dashavidha Pariksha scaffold.

STARTER SCAFFOLD, not a finished clinical module - see
data/ayush/dashavidha_pariksha.json's own honesty note for the full
disclosure. This file does three honest things right now:

1. Loads the ten parameter definitions from the reference data file,
   including each one's acquisition_mode (added 11 Sep 2026 after
   cross-checking the reference data against real Ayurvedic-diagnostics
   literature - see the JSON file's own _update_2026_09_11 note).
2. Splits those ten into what a self-service kiosk can actually ask the
   patient directly, versus what requires a physician's own physical
   examination (Darshana/Sparshana - inspection/palpation, the same
   methods Ashtavidha Pariksha names) and therefore cannot be a patient
   form field no matter how the question is worded.
3. Builds an empty, all-fields-optional AyushAssessment shell a
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
from typing import Literal

from app.schemas import AyushAssessment

DEFAULT_PARAMETERS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "ayush" / "dashavidha_pariksha.json"
)

AcquisitionMode = Literal["patient_self_report", "mixed", "physician_assessment_required"]


@dataclass(frozen=True)
class DashavidhaParameter:
    name: str
    gloss: str
    acquisition_mode: AcquisitionMode
    acquisition_rationale: str

    @property
    def kiosk_askable(self) -> bool:
        """
        True for anything a self-service kiosk can put in front of a
        patient at all - "patient_self_report" outright, and "mixed"
        because the self-reportable half of a mixed parameter (e.g.
        Vikriti's current symptoms, distinct from its clinical
        determination) is still worth asking. Only
        "physician_assessment_required" parameters (Sara, Samhanana,
        Pramana - all three requiring physical examination per
        data/ayush/dashavidha_pariksha.json's own sourced rationale)
        are excluded.
        """
        return self.acquisition_mode != "physician_assessment_required"


def load_dashavidha_parameters(path: Path = DEFAULT_PARAMETERS_PATH) -> list[DashavidhaParameter]:
    """
    Raises FileNotFoundError / json.JSONDecodeError on a missing or
    malformed reference file - never silently returns an empty list,
    since a caller getting zero parameters back should know the
    reference data failed to load, not assume AYUSH mode is simply
    inapplicable to the current case. Also raises KeyError if a
    parameter entry is missing acquisition_mode/acquisition_rationale -
    every entry in the reference file is expected to carry both since
    the 11 Sep 2026 update, so a missing one means the data file itself
    regressed, not that the field is genuinely optional.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        DashavidhaParameter(
            name=entry["name"],
            gloss=entry["gloss"],
            acquisition_mode=entry["acquisition_mode"],
            acquisition_rationale=entry["acquisition_rationale"],
        )
        for entry in raw["parameters"]
    ]


def kiosk_askable_parameters(path: Path = DEFAULT_PARAMETERS_PATH) -> list[DashavidhaParameter]:
    """
    The real, load-bearing point of tracking acquisition_mode at all:
    a future patient-facing AYUSH interview module should build its
    question set from this function's output, never from
    load_dashavidha_parameters() directly - asking a patient to
    self-rate Sara/Samhanana/Pramana would be exactly the "decorative
    Sanskrit vocabulary, not real clinical understanding" failure mode
    docs/sih/SIH26047_STRATEGY.md (Section D, item 3) warns is worse
    than not building AYUSH mode at all.
    """
    return [p for p in load_dashavidha_parameters(path) if p.kiosk_askable]


def physician_only_parameters(path: Path = DEFAULT_PARAMETERS_PATH) -> list[DashavidhaParameter]:
    """
    The complement of kiosk_askable_parameters() - parameters that
    belong in the physician-facing summary as "not yet assessed" fields
    for the consulting physician to fill in during the in-person exam,
    never as patient form fields, no matter how the question is worded.
    """
    return [p for p in load_dashavidha_parameters(path) if not p.kiosk_askable]


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
