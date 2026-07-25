"""
Referral Agent.

Turns a verified TriageDecision into a concrete next step. Exactly one
of three things comes out of this: self-care guidance, a named facility
referral, or an emergency escalation message. Never a diagnosis, never
a prescription - see docs/INTERVIEW_NOTES.md for why that boundary is
enforced structurally here, not just stated in the README.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.schemas import CaseSummary, Facility, ReferralResult, TriageDecision, TriageLevel

logger = logging.getLogger(__name__)

DEFAULT_FACILITIES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "facilities" / "kurnool_facilities.json"
)

SELF_CARE_MESSAGE = (
    "This can typically be managed at home with rest and fluids. "
    "If it does not improve within 2-3 days, or gets worse, see a doctor."
)

EMERGENCY_MESSAGE = (
    "This needs emergency care right now. Go to the nearest hospital "
    "emergency department or call for emergency transport immediately. "
    "Do not wait."
)


def load_facilities(path: Path = DEFAULT_FACILITIES_PATH) -> list[Facility]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Facility(**entry) for entry in raw]


def run_referral(case: CaseSummary, decision: TriageDecision, facilities: list[Facility]) -> ReferralResult:
    """
    Deliberately simple branching, not a geolocation or nearest-facility
    ranking system. The honest MVP scope is "name a real facility
    category the patient can act on," not "compute the single closest
    one" - that would need real-time location data and a maintained,
    complete district directory this project doesn't have. Stated
    plainly rather than implied.
    """
    if decision.level == TriageLevel.EMERGENCY:
        # No facility lookup on the emergency path, on purpose - even a
        # few hundred milliseconds of lookup time has no place between
        # a real emergency and the instruction to act. Mirrors the same
        # reasoning behind Entry 4's red-flag short-circuit in
        # app/agents/triage.py.
        return ReferralResult(level=TriageLevel.EMERGENCY, message=EMERGENCY_MESSAGE, facility=None)

    if decision.level == TriageLevel.SELF_CARE:
        return ReferralResult(level=TriageLevel.SELF_CARE, message=SELF_CARE_MESSAGE, facility=None)

    if not facilities:
        raise ValueError("run_referral requires at least one facility for clinic_visit/urgent cases.")

    chosen = facilities[0]  # MVP: first curated entry, not distance-ranked - see docstring above
    if decision.level == TriageLevel.URGENT:
        timing = "as soon as possible today"
    else:
        timing = "within the next day or two"

    message = f"Visit {chosen.name} ({chosen.type}, {chosen.area}) {timing}."
    return ReferralResult(level=decision.level, message=message, facility=chosen)
