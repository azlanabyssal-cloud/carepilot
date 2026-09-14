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
import unicodedata
from typing import Protocol

from anthropic import Anthropic, APIConnectionError, APIStatusError, RateLimitError
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.schemas import CaseSummary, TriageDecision, TriageLevel

logger = logging.getLogger(__name__)


def _strip_invisible(text: str) -> str:
    """
    Like str.strip(), but also strips Unicode *format* characters
    (category "Cf" - zero-width space/joiner/non-joiner, the BOM,
    left/right-to-left marks, etc.) from both ends, not just whitespace.

    str.strip() alone leaves a leading "Cf" character untouched - it
    doesn't satisfy str.isspace(). _parse() below used plain
    line.strip() before checking startswith("LEVEL:")/("RATIONALE:"),
    the exact "Cf is not real content" gap Day 16 already closed for
    app/agents/intake.py's scan_red_flags() and app/schemas.py's
    _visible_length, but named there as a real, unfixed sibling gap in
    this exact function - see docs/INTERVIEW_NOTES.md, Day 16 and 17.
    """
    start, end = 0, len(text)
    while start < end and (text[start].isspace() or unicodedata.category(text[start]) == "Cf"):
        start += 1
    while end > start and (text[end - 1].isspace() or unicodedata.category(text[end - 1]) == "Cf"):
        end -= 1
    return text[start:end]

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
        try:
            return message.content[0].text
        except (IndexError, AttributeError) as exc:
            # Real bug, found by actually simulating an empty-content
            # response, not assumed away: every other third-party-API
            # backend in this codebase already guards its own
            # response-shape parsing this way -
            # GroqReasoningBackend._call (app/agents/groq_backends.py)
            # catches (KeyError, IndexError) around its own
            # response.json()["choices"][0]["message"]["content"], and
            # app/adapters/bhashini.py does the same in four places -
            # but this call site never did. An Anthropic response with
            # an empty `content` list (or a content block with no
            # `.text`, e.g. a non-text block) makes `message.content[0].text`
            # raise a raw IndexError/AttributeError that propose()'s own
            # `except (APIConnectionError, RateLimitError, APIStatusError)`
            # does not match, so it would propagate uncaught through
            # run_triage_reasoning() and out of app/main.py's _run_triage
            # (which only catches TriageBackendError) as a raw 500 -
            # the exact failure class Days 6-10 already fixed five times
            # elsewhere, just never audited for this specific call site.
            raise TriageBackendError(f"Unexpected Anthropic response shape: {exc}") from exc

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

        try:
            return self._parse(raw)
        except ValidationError as exc:
            # The model responded and _parse() ran, but produced a
            # rationale too short - or blank-looking-but-technically-
            # non-empty (invisible Unicode, see TriageDecision.rationale's
            # own validator in app/schemas.py) - to satisfy
            # TriageDecision's own contract. Caught explicitly, same
            # reason app/main.py already catches this exact failure
            # class for ClinicalHistorySummary: a manually-constructed
            # Pydantic model bypasses FastAPI's automatic request-body
            # validation, so an uncaught ValidationError here would
            # surface as a raw 500 instead of the clean 503 every other
            # backend failure in this class already produces.
            logger.error("Triage reasoning backend produced an invalid decision: %s", exc)
            raise TriageBackendError(f"Backend produced an unusable triage decision: {exc}") from exc

    @staticmethod
    def _parse(raw: str) -> TriageDecision:
        # Cautious default: if the model's response can't be parsed cleanly,
        # fail toward "urgent" (see a human sooner) rather than "self_care"
        # (see no one). Silent failure toward the safe direction, not toward
        # the convenient one.
        #
        # Real bug, found by simulating realistic model-formatting
        # irregularity rather than assuming the exact prompted shape, the
        # same discipline that already found the red-flag-scanner
        # whitespace bug (docs/INTERVIEW_NOTES.md, Day 14): each line was
        # matched with `line.upper().startswith("LEVEL:")` - no leading
        # whitespace stripped first - so a response indented with even one
        # leading space ("  LEVEL: emergency", the kind of formatting a
        # model can add on its own inside a markdown bullet, a numbered
        # step, or a code-fence remnant, despite the prompt asking for
        # exactly two bare lines) never matches either prefix. Both
        # branches silently miss, level stays at the URGENT default, and
        # rationale falls back to the *entire raw response* instead of just
        # the intended sentence. For a case where the model itself judged
        # "emergency," that default is a silent one-level DE-escalation to
        # "urgent" - exactly the failure direction this project's own
        # README names as the metric that matters (recall on
        # emergency-flagged cases), not a harmless over-caution the way
        # defaulting to urgent normally is for a genuinely unparseable
        # response.
        #
        # Day 17: line.strip() alone still missed a leading Unicode "Cf"
        # (invisible format) character in front of the prefix - e.g. a
        # ZERO WIDTH SPACE before "LEVEL:" - which silently de-escalated
        # a model-judged "emergency" to the URGENT default, the exact
        # failure direction named as a real, unfixed gap in Day 16.
        # _strip_invisible strips both whitespace and "Cf" characters.
        #
        # Day 18: Day 17's fix only reached the LEVEL:/RATIONALE: prefix
        # check, not the value that comes after the colon on the same
        # line. `stripped_line.split(":", 1)[1].strip()` still used plain
        # str.strip() on the value itself, so a Cf character sitting
        # between the colon and the value (e.g. "LEVEL: ​emergency")
        # left the parsed value as "​emergency" - not an exact match
        # for any TriageLevel member - which raised the caught ValueError
        # and silently fell back to the same URGENT default, the identical
        # dangerous de-escalation direction Days 15-17 already fixed twice
        # over for the prefix half of this same line. Both value
        # extractions below now use _strip_invisible instead of str.strip.
        level = TriageLevel.URGENT
        rationale = _strip_invisible(raw)

        for line in raw.splitlines():
            stripped_line = _strip_invisible(line)
            if stripped_line.upper().startswith("LEVEL:"):
                value = _strip_invisible(stripped_line.split(":", 1)[1]).lower()
                try:
                    level = TriageLevel(value)
                except ValueError:
                    logger.warning("Unrecognized triage level from model: %r - defaulting to urgent", value)
            elif stripped_line.upper().startswith("RATIONALE:"):
                rationale = _strip_invisible(stripped_line.split(":", 1)[1])

        return TriageDecision(level=level, rationale=rationale, confidence=0.75)


class DeterministicFallbackReasoningBackend:
    """
    Zero-API fallback used only when the real reasoning backend can't be
    constructed (no key) or fails after retries - never a substitute for
    a real clinical judgment, and never reached for a case the
    deterministic red-flag scan already flagged (run_triage_reasoning's
    short-circuit above owns EMERGENCY; this class is only ever invoked
    for cases that scan did NOT flag).

    Always proposes the same fixed TriageLevel.URGENT with confidence=0.0
    - deliberately not an attempt to guess self_care/clinic_visit/urgent
    from symptom_text with keyword heuristics, which would risk exactly
    the "confidently wrong, wrong direction" failure this project's own
    safety discipline (docs/DAILY_LOG.md, Days 14-18) has repeatedly
    found and fixed: a plausible-looking local classifier could
    under-triage a real emergency that the red-flag scanner's fixed term
    list didn't happen to catch. URGENT (not SELF_CARE or CLINIC_VISIT)
    with confidence=0.0 is an honest "route to a human for triage now,
    this was not a real clinical decision" signal, not a diagnosis - the
    same "when in doubt, escalate" principle SYSTEM_PROMPT above already
    asks the real backend to follow, applied without a model at all.
    """

    def propose(self, case: CaseSummary) -> TriageDecision:
        return TriageDecision(
            level=TriageLevel.URGENT,
            rationale=(
                "Automated triage-reasoning backend was unavailable (no API "
                "key, network failure, or exhausted retries). Defaulting to "
                "URGENT so this case reaches a human for prompt triage rather "
                "than being blocked entirely - this is not a clinical judgment."
            ),
            confidence=0.0,
        )


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
