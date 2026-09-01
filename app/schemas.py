"""
Data contracts for the triage pipeline.

Every agent in app/agents/ reads and returns these shapes. Defining them
up front means each agent can be built, tested, and understood in
isolation - you don't need agent 2, 3, and 4 written before you can
run and reason about agent 1.
"""

import unicodedata
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TriageLevel(str, Enum):
    SELF_CARE = "self_care"
    CLINIC_VISIT = "clinic_visit"
    URGENT = "urgent"
    EMERGENCY = "emergency"


def _visible_length(value: str) -> int:
    """
    Shared by every free-text field in this file that carries a
    min_length safety floor (PatientInput.symptom_text,
    ClinicalHistorySummary.chief_complaint): counts characters that are
    neither Unicode whitespace (category "Zs" and friends, via
    str.isspace()) nor Unicode *format* characters (category "Cf" -
    zero-width space/joiner/non-joiner, the BOM, left/right-to-left
    marks, etc.). Plain Python length and str.strip() both count "Cf"
    characters as real content, so a string built only from them - "​​​"
    (three U+200B ZERO WIDTH SPACE) - satisfies any min_length check
    while rendering as completely blank to a human reading it. See
    PatientInput._reject_whitespace_only's docstring for how this was
    first found.
    """
    return sum(1 for ch in value if not ch.isspace() and unicodedata.category(ch) != "Cf")


class PatientInput(BaseModel):
    """Raw input as it arrives from the intake form/API call."""

    symptom_text: str = Field(..., min_length=3, description="Patient's own description, English or Telugu.")
    age: Optional[int] = Field(default=None, ge=0, le=120)
    duration_days: Optional[int] = Field(default=None, ge=0)
    has_image: bool = Field(default=False, description="True if a symptom/wound image was attached.")

    @field_validator("symptom_text")
    @classmethod
    def _reject_whitespace_only(cls, value: str) -> str:
        """
        Real bug, caught by actually sending whitespace-only input, not
        assumed away: min_length=3 counts spaces as real characters, so
        "   " (three spaces) passed validation and reached the AI backend
        as if it were real symptom text. Stripped length is what actually
        carries information - three spaces describe nothing a triage
        decision could be made from, so this is checked separately from
        (and in addition to) the raw min_length constraint above.

        Second real bug, same root cause, caught the same way (by sending
        the actual bytes against a live server, not assumed from reading
        str.strip()'s docs): "​​​" (three U+200B ZERO WIDTH
        SPACE characters - renders as completely blank) also passed both
        min_length=3 and the check above unchanged, because str.strip()
        only removes Unicode whitespace (category "Zs" and friends), not
        invisible Unicode *format* characters (category "Cf" - zero-width
        space/joiner/non-joiner, the BOM, left/right-to-left marks, etc.).
        A symptom_text made only of these characters is indistinguishable
        from empty input to any human reading it, but was reaching the AI
        backend as if it were real clinical content. Filtering out
        category "Cf" alongside whitespace before this length check closes
        that gap without touching what's actually stored - `value` itself
        is returned unmodified, exactly as surrounding real whitespace is
        preserved today.
        """
        if _visible_length(value) < 3:
            raise ValueError("symptom_text must contain at least 3 non-whitespace characters")
        return value


class CaseSummary(BaseModel):
    """Output of the Intake Agent: raw input normalized into a structured case."""

    symptom_text: str
    age: Optional[int]
    duration_days: Optional[int]
    has_image: bool
    red_flag_terms: list[str] = Field(
        default_factory=list,
        description="Emergency-indicator keywords found by the deterministic pre-filter, before any model runs.",
    )

    @property
    def has_red_flag(self) -> bool:
        return len(self.red_flag_terms) > 0


class TriageDecision(BaseModel):
    """Output of the Triage-Reasoning Agent: a proposed level, checked by the Guideline-Verification Agent."""

    level: TriageLevel
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class Facility(BaseModel):
    """A single entry from the curated facility directory (data/facilities/)."""

    name: str
    type: str
    area: str
    source: str


class ReferralResult(BaseModel):
    """Output of the Referral Agent: the final, patient-facing outcome of the whole pipeline."""

    level: TriageLevel
    message: str
    facility: Optional[Facility] = None


class ClinicalHistorySummary(BaseModel):
    """
    The structured, physician-ready history summary format SIH26047 asks
    for: Chief complaint -> HPI -> Past history -> Drug/allergy -> Family
    -> Personal -> ROS -> Prior investigations (see
    docs/sih/SIH26047_Patient_Case_Taking_Software.md, Module C).

    This does not replace TriageDecision - it subsumes it. priority_level
    carries the same red-flag/triage safety net CarePilot already has
    (app/agents/intake.py, app/agents/triage.py); this schema is a richer
    output shape built on top of that existing, tested logic, not a
    separate system.

    is_reviewed_by_physician defaults to False on purpose - the PS is
    explicit that the AI drafts, the doctor decides ("AI is a scribe,
    never the decision-maker"). A summary a physician hasn't reviewed
    yet must be visibly a draft, never presented as final.

    case_id defaults to None on purpose - it is only ever populated once
    a summary has actually been persisted (app/db.py's CaseStore.save(),
    called from the live /case-intake* endpoints in app/main.py). A
    summary built directly - every construction site in this repo's own
    tests (tests/test_schemas.py, tests/test_history_intake.py, etc.)
    plus any future one that builds a summary before it's ever saved -
    has no case_id yet, and that's the honest state to represent: None,
    not an empty string standing in for "not saved yet."
    """

    chief_complaint: str = Field(..., min_length=3)
    history_of_present_illness: str = Field(..., min_length=3)
    past_medical_surgical_history: Optional[str] = None
    drug_allergy_history: Optional[str] = None
    family_history: Optional[str] = None
    personal_history: Optional[str] = None
    review_of_systems: Optional[str] = None
    prior_investigations_summary: Optional[str] = None
    priority_level: TriageLevel
    is_reviewed_by_physician: bool = False
    case_id: Optional[str] = None

    @field_validator("chief_complaint")
    @classmethod
    def _reject_invisible_chief_complaint(cls, value: str) -> str:
        """
        Real bug, found by actually tracing what a drafting-backend
        response can produce, not assumed away: app/agents/history_intake.py's
        _parse() only falls back to case.symptom_text when the model's
        CHIEF_COMPLAINT line is *empty* after str.strip() (`fields.get(...)
        or case.symptom_text`), but str.strip() - same gap as
        PatientInput._reject_whitespace_only above - leaves Unicode
        *format* characters (category "Cf": zero-width space/joiner, the
        BOM, etc.) untouched. A response line
        "CHIEF_COMPLAINT: ​​​" (three U+200B ZERO WIDTH SPACE) parses to a
        non-empty, non-whitespace-per-str.strip() string that is truthy,
        so the `or` fallback never fires, and it then satisfies this
        field's own min_length=3 - a summary a physician opens and sees
        as blank, silently persisted as if it were real. Reuses
        `_visible_length` rather than reintroducing a second, possibly
        inconsistent copy of the same check.
        """
        if _visible_length(value) < 3:
            raise ValueError("chief_complaint must contain at least 3 non-whitespace characters")
        return value

    @field_validator("history_of_present_illness")
    @classmethod
    def _reject_invisible_history_of_present_illness(cls, value: str) -> str:
        """
        Same failure class as _reject_invisible_chief_complaint above,
        found by auditing app/agents/history_intake.py's _parse() for
        every field that shares its `fields.get(KEY) or case.symptom_text`
        fallback pattern, not just the one already fixed. HPI uses the
        identical pattern (`fields.get("HPI") or case.symptom_text`), so
        an invisible-Unicode-only "HPI: ​​​" response line is just as
        truthy as the chief_complaint case was, and the fallback never
        fires here either. Unlike chief_complaint, this field previously
        had no min_length constraint at all - not even the gameable raw
        character-count floor - so an invisible-only or even a
        genuinely empty HPI would construct successfully with zero
        validation. Field(..., min_length=3) above closes the empty
        case; this validator closes the invisible-only case the same
        way chief_complaint's already does, reusing _visible_length
        rather than a third, possibly-drifting copy of the same check.
        """
        if _visible_length(value) < 3:
            raise ValueError("history_of_present_illness must contain at least 3 non-whitespace characters")
        return value


class AyushAssessment(BaseModel):
    """
    STARTER SCAFFOLD - see data/ayush/dashavidha_pariksha.json for the
    full honesty note. The ten fields below are the Dashavidha Pariksha
    parameters SIH26047's Module A names for AYUSH history mode - free
    text here on purpose, since this project has no validated scoring
    system for any of them yet. Every field is optional: capturing
    eight of ten parameters is more useful than refusing to save
    anything because two weren't answered.

    Deliberately a separate, optional model from ClinicalHistorySummary
    rather than fields bolted onto it - AYUSH-specific intake only
    applies to Ayurvedic OPDs, not every case this system handles.
    """

    prakriti: Optional[str] = None
    vikriti: Optional[str] = None
    sara: Optional[str] = None
    samhanana: Optional[str] = None
    pramana: Optional[str] = None
    satmya: Optional[str] = None
    sattva: Optional[str] = None
    ahara_shakti: Optional[str] = None
    vyayama_shakti: Optional[str] = None
    vaya: Optional[str] = None
    reviewed_by_ayush_practitioner: bool = False
