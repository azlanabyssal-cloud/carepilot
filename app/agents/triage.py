"""
Triage-Reasoning Agent.

Proposes a triage level for cases the Intake Agent's deterministic scan
did NOT already flag as an emergency. See docs/INTERVIEW_NOTES.md,
Entry 4, for why the red-flag short-circuit lives here and not in
Intake itself.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

from anthropic import Anthropic, APIConnectionError, APIStatusError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.schemas import CaseSummary, TriageDecision, TriageLevel

logger = logging.getLogger(__name__)

REASONING_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are a triage-support assistant for a rural primary-healthcare context. "
    "You NEVER diagnose and NEVER prescribe. You propose exactly one triage level: "
    "self_care, clinic_visit, urgent, or emergency, with a short rationale grounded "
    "only in the patient-reported information given to you. If the information is "
    "insufficient to rule out a serious cause, propose the more cautious (higher) level."
)


class ReasoningBackend(Protocol):
    """Anything that can propose a triage level from a case summary.

    A Protocol, not a concrete base class, so run_triage_reasoning() can
    be unit-tested against a fake backend - no network call, no API key
    required. See tests/test_triage.py.
    """

    def propose(self, case: CaseSummary) -> TriageDecision: ...


class TriageBackendError(RuntimeError):
    """Raised when the reasoning backend fails, including after retries are exhausted."""


class AnthropicReasoningBackend:
    """Real backend: calls the Anthropic Messages API."""

    def __init__(self, api_key: str | None = None, model: str = REASONING_MODEL) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise TriageBackendError(
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
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": self._build_prompt(case)}],
        )
        return message.content[0].text

    @staticmethod
    def _build_prompt(case: CaseSummary) -> str:
        age_part = f"Age: {case.age}. " if case.age is not None else ""
        duration_part = f"Duration: {case.duration_days} day(s). " if case.duration_days is not None else ""
        return (
            f"{age_part}{duration_part}Reported symptoms: {case.symptom_text}\n\n"
            "Respond with exactly two lines, no other text:\n"
            "LEVEL: <self_care|clinic_visit|urgent|emergency>\n"
            "RATIONALE: <one sentence, grounded only in the symptoms above>"
        )

    def propose(self, case: CaseSummary) -> TriageDecision:
        try:
            raw = self._call(case)
        except (APIConnectionError, RateLimitError, APIStatusError) as exc:
            logger.error("Triage reasoning backend failed after retries: %s", exc)
            raise TriageBackendError(str(exc)) from exc

        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> TriageDecision:
        # Cautious default: if the model's response can't be parsed cleanly,
        # fail toward "urgent" (see a human sooner) rather than "self_care"
        # (see no one). Silent failure toward the safe direction, not toward
        # the convenient one.
        level = TriageLevel.URGENT
        rationale = raw.strip()

        for line in raw.splitlines():
            if line.upper().startswith("LEVEL:"):
                value = line.split(":", 1)[1].strip().lower()
                try:
                    level = TriageLevel(value)
                except ValueError:
                    logger.warning("Unrecognized triage level from model: %r - defaulting to urgent", value)
            elif line.upper().startswith("RATIONALE:"):
                rationale = line.split(":", 1)[1].strip()

        return TriageDecision(level=level, rationale=rationale, confidence=0.75)


def run_triage_reasoning(case: CaseSummary, backend: ReasoningBackend) -> TriageDecision:
    """
    The Intake Agent's deterministic red-flag scan takes precedence: if a
    known emergency term was already found, this agent does not spend a
    model call second-guessing it - it short-circuits straight to
    EMERGENCY, and the backend is never invoked. Proven, not just
    asserted, in test_red_flag_case_short_circuits_without_calling_backend.
    """
    if case.has_red_flag:
        return TriageDecision(
            level=TriageLevel.EMERGENCY,
            rationale=f"Deterministic red-flag term(s) detected: {', '.join(case.red_flag_terms)}.",
            confidence=1.0,
        )

    return backend.propose(case)
