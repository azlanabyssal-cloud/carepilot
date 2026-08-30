"""
History-Intake Agent.

Turns a patient's free-text symptom description into the structured,
physician-ready narrative fields SIH26047 asks for (see
docs/sih/SIH26047_Patient_Case_Taking_Software.md, Module A/C: chief
complaint, HPI, past/drug/family/personal history, review of systems).

Deliberately does NOT decide priority_level. That decision already
exists, already tested, already safety-critical:
app/agents/intake.py's red-flag scan and app/agents/triage.py's
Triage-Reasoning Agent decide it before this agent ever runs. This
agent's only job is drafting the narrative story around a decision
someone else already made safely - same reasoning as why
app/agents/verify.py never re-decides an already-escalated EMERGENCY
level (see its own docstring).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional, Protocol

from anthropic import Anthropic, APIConnectionError, APIStatusError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.schemas import CaseSummary, ClinicalHistorySummary, TriageDecision

logger = logging.getLogger(__name__)

DRAFTING_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are a clinical history-taking assistant for a rural/OPD healthcare context. "
    "You NEVER diagnose and NEVER prescribe. You turn a patient's own words into a "
    "structured, physician-readable history draft. If the patient did not mention a "
    "section, write NONE for it rather than inventing details."
)


@dataclass(frozen=True)
class HistoryDraft:
    """
    The narrative fields a backend drafts from a case - everything
    ClinicalHistorySummary needs EXCEPT priority_level and
    is_reviewed_by_physician, which are never derived here (see module
    docstring).
    """

    chief_complaint: str
    history_of_present_illness: str
    past_medical_surgical_history: Optional[str] = None
    drug_allergy_history: Optional[str] = None
    family_history: Optional[str] = None
    personal_history: Optional[str] = None
    review_of_systems: Optional[str] = None


class HistoryDraftingBackend(Protocol):
    """Anything that can draft a HistoryDraft from a case summary.

    A Protocol, not a concrete base class, so run_history_intake() can
    be unit-tested against a fake backend - no network call, no API key
    required. Same shape as app/agents/triage.py's ReasoningBackend, on
    purpose - see docs/INTERVIEW_NOTES.md's Bhashini entry for why
    reusing an already-proven pattern beats inventing a new one.
    """

    def draft(self, case: CaseSummary) -> HistoryDraft: ...


class HistoryDraftingError(RuntimeError):
    """Raised when drafting fails, including after retries are exhausted."""


class AnthropicHistoryDraftingBackend:
    """Real backend: calls the Anthropic Messages API."""

    def __init__(self, api_key: str | None = None, model: str = DRAFTING_MODEL) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise HistoryDraftingError(
                "ANTHROPIC_API_KEY is not set. Export it in the environment or pass "
                "api_key explicitly - never hardcode a key in source or commit one."
            )
        self._client = Anthropic(api_key=resolved_key)
        self._model = model

    @retry(
        retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _call(self, case: CaseSummary) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": self._build_prompt(case)}],
        )
        return message.content[0].text

    @staticmethod
    def _build_prompt(case: CaseSummary) -> str:
        age_part = f"Age: {case.age}. " if case.age is not None else ""
        duration_part = f"Duration: {case.duration_days} day(s). " if case.duration_days is not None else ""
        return (
            f"{age_part}{duration_part}Patient's own words: {case.symptom_text}\n\n"
            "Respond with exactly these seven lines, no other text:\n"
            "CHIEF_COMPLAINT: <one short phrase>\n"
            "HPI: <one or two sentences on onset, character, duration>\n"
            "PAST_HISTORY: <text, or NONE if not mentioned>\n"
            "DRUG_ALLERGY: <text, or NONE if not mentioned>\n"
            "FAMILY_HISTORY: <text, or NONE if not mentioned>\n"
            "PERSONAL_HISTORY: <text, or NONE if not mentioned>\n"
            "ROS: <text, or NONE if not mentioned>"
        )

    def draft(self, case: CaseSummary) -> HistoryDraft:
        try:
            raw = self._call(case)
        except (APIConnectionError, RateLimitError, APIStatusError) as exc:
            logger.error("History-drafting backend failed after retries: %s", exc)
            raise HistoryDraftingError(str(exc)) from exc

        return self._parse(raw, case)

    @staticmethod
    def _parse(raw: str, case: CaseSummary) -> HistoryDraft:
        # Cautious default, same philosophy as triage.py's _parse: if a
        # required field can't be found in the model's response, fall
        # back to the patient's own reported text rather than raising -
        # a slightly-wrong-shaped draft the physician can edit is a
        # better failure mode than a crash on the one path meant to
        # save the physician time.
        fields: dict[str, str] = {}
        for line in raw.splitlines():
            for key in ("CHIEF_COMPLAINT", "HPI", "PAST_HISTORY", "DRUG_ALLERGY", "FAMILY_HISTORY",
                        "PERSONAL_HISTORY", "ROS"):
                prefix = f"{key}:"
                if line.upper().startswith(prefix):
                    fields[key] = line.split(":", 1)[1].strip()
                    break

        def optional(key: str) -> Optional[str]:
            value = fields.get(key)
            if not value or value.upper() == "NONE":
                return None
            return value

        chief_complaint = fields.get("CHIEF_COMPLAINT") or case.symptom_text
        history_of_present_illness = fields.get("HPI") or case.symptom_text

        return HistoryDraft(
            chief_complaint=chief_complaint,
            history_of_present_illness=history_of_present_illness,
            past_medical_surgical_history=optional("PAST_HISTORY"),
            drug_allergy_history=optional("DRUG_ALLERGY"),
            family_history=optional("FAMILY_HISTORY"),
            personal_history=optional("PERSONAL_HISTORY"),
            review_of_systems=optional("ROS"),
        )


def run_history_intake(
    case: CaseSummary, decision: TriageDecision, backend: HistoryDraftingBackend
) -> ClinicalHistorySummary:
    """
    Combines the already-decided priority_level (from
    app/agents/triage.py) with a freshly-drafted narrative history.
    This function never touches priority - see module docstring for why.
    """
    draft = backend.draft(case)
    return ClinicalHistorySummary(
        chief_complaint=draft.chief_complaint,
        history_of_present_illness=draft.history_of_present_illness,
        past_medical_surgical_history=draft.past_medical_surgical_history,
        drug_allergy_history=draft.drug_allergy_history,
        family_history=draft.family_history,
        personal_history=draft.personal_history,
        review_of_systems=draft.review_of_systems,
        priority_level=decision.level,
        is_reviewed_by_physician=False,
    )
