"""
Groq-backed implementations of the Triage-Reasoning and History-Intake
Protocols defined in app/agents/triage.py and app/agents/history_intake.py.

Additive, not a replacement: CarePilot's safety story (red-flag
short-circuit, cautious-default parsing, "AI drafts, physician decides")
lives in the Protocol contracts and the callers that consume them
(run_triage_reasoning, run_history_intake), not in any one vendor's
SDK. Any object satisfying ReasoningBackend/HistoryDraftingBackend can
be swapped in - this module proves that by satisfying both with Groq's
API instead of Anthropic's, so a deployment without Anthropic access
(or one that wants a faster/cheaper model for draft traffic) has a
real second option, not just a stub.

Groq exposes an OpenAI-compatible REST endpoint rather than its own
SDK, so this follows app/adapters/bhashini.py's pattern for a
third-party HTTP API: raw httpx (no new dependency), a fail-fast
missing-credential error, and retry/backoff on the transient-failure
path only. The two prompt formats (LEVEL:/RATIONALE: and
CHIEF_COMPLAINT:/HPI:/...) and both _parse methods are copied from the
Anthropic backends verbatim on purpose - the cautious-default safety
properties they encode (unparseable level -> URGENT; missing required
field -> fall back to the patient's own words) must hold identically
regardless of which vendor answered the prompt. This has not been
exercised against Groq's real servers in this environment (no
GROQ_API_KEY is available here); the request/response shape follows
Groq's publicly documented OpenAI-compatible chat-completions contract,
verified only via the fake-backend tests in
tests/test_groq_backends.py - no network call, same as those tests.
"""

from __future__ import annotations

import logging
import os

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.agents.history_intake import SYSTEM_PROMPT as HISTORY_SYSTEM_PROMPT
from app.agents.history_intake import HistoryDraft, HistoryDraftingError
from app.agents.triage import SYSTEM_PROMPT as TRIAGE_SYSTEM_PROMPT
from app.agents.triage import TriageBackendError
from app.schemas import CaseSummary, TriageDecision, TriageLevel

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def _is_retryable_http_error(exc: BaseException) -> bool:
    """
    Connection drops and timeouts are always worth a retry; a 5xx is
    Groq's own infrastructure having a bad moment and is also worth a
    retry. A 4xx (bad request, bad API key, rate limit that isn't
    surfaced as a 5xx) will not fix itself on attempt two - retrying it
    only delays the real error reaching the caller, so it is left alone
    the same way app/agents/triage.py doesn't retry a non-transient
    Anthropic error.
    """
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


class GroqReasoningBackend:
    """Real backend: calls Groq's OpenAI-compatible chat-completions API.

    Same shape as app/agents/triage.py's AnthropicReasoningBackend on
    purpose - run_triage_reasoning() takes any ReasoningBackend, so this
    class exists to be a drop-in alternative, not a parallel code path
    with its own rules.
    """

    def __init__(self, api_key: str | None = None, model: str = GROQ_MODEL, timeout: float = 30.0) -> None:
        resolved_key = api_key or os.environ.get("GROQ_API_KEY")
        if not resolved_key:
            raise TriageBackendError(
                "GROQ_API_KEY is not set. Export it in the environment or pass "
                "api_key explicitly - never hardcode a key in source or commit one."
            )
        self._api_key = resolved_key
        self._model = model
        self._client = httpx.Client(timeout=timeout)

    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _call(self, case: CaseSummary) -> str:
        response = self._client.post(
            CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_prompt(case)},
                ],
            },
        )
        response.raise_for_status()
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise TriageBackendError(f"Unexpected Groq chat-completions response shape: {exc}") from exc

    @staticmethod
    def _build_prompt(case: CaseSummary) -> str:
        # Identical to AnthropicReasoningBackend._build_prompt - the model
        # being asked is a different vendor, but the contract it must
        # answer under (exactly two lines, LEVEL:/RATIONALE:) is not.
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
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Groq triage reasoning backend failed after retries: %s", exc)
            raise TriageBackendError(str(exc)) from exc

        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> TriageDecision:
        # Copied verbatim from AnthropicReasoningBackend._parse: if the
        # model's response can't be parsed cleanly, fail toward "urgent"
        # (see a human sooner) rather than "self_care" (see no one).
        # This safety property must hold no matter which vendor
        # produced the unparseable text.
        level = TriageLevel.URGENT
        rationale = raw.strip()

        for line in raw.splitlines():
            if line.upper().startswith("LEVEL:"):
                value = line.split(":", 1)[1].strip().lower()
                try:
                    level = TriageLevel(value)
                except ValueError:
                    logger.warning("Unrecognized triage level from Groq model: %r - defaulting to urgent", value)
            elif line.upper().startswith("RATIONALE:"):
                rationale = line.split(":", 1)[1].strip()

        return TriageDecision(level=level, rationale=rationale, confidence=0.75)


class GroqHistoryDraftingBackend:
    """Real backend: calls Groq's OpenAI-compatible chat-completions API.

    Same shape as app/agents/history_intake.py's
    AnthropicHistoryDraftingBackend on purpose - run_history_intake()
    takes any HistoryDraftingBackend, so this class exists to be a
    drop-in alternative, not a parallel code path with its own rules.
    """

    def __init__(self, api_key: str | None = None, model: str = GROQ_MODEL, timeout: float = 30.0) -> None:
        resolved_key = api_key or os.environ.get("GROQ_API_KEY")
        if not resolved_key:
            raise HistoryDraftingError(
                "GROQ_API_KEY is not set. Export it in the environment or pass "
                "api_key explicitly - never hardcode a key in source or commit one."
            )
        self._api_key = resolved_key
        self._model = model
        self._client = httpx.Client(timeout=timeout)

    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _call(self, case: CaseSummary) -> str:
        response = self._client.post(
            CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": HISTORY_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_prompt(case)},
                ],
            },
        )
        response.raise_for_status()
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise HistoryDraftingError(f"Unexpected Groq chat-completions response shape: {exc}") from exc

    @staticmethod
    def _build_prompt(case: CaseSummary) -> str:
        # Identical to AnthropicHistoryDraftingBackend._build_prompt -
        # same seven-line contract, different vendor answering it.
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
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Groq history-drafting backend failed after retries: %s", exc)
            raise HistoryDraftingError(str(exc)) from exc

        return self._parse(raw, case)

    @staticmethod
    def _parse(raw: str, case: CaseSummary) -> HistoryDraft:
        # Copied verbatim from AnthropicHistoryDraftingBackend._parse:
        # if a required field can't be found in the model's response,
        # fall back to the patient's own reported text rather than
        # raising - a slightly-wrong-shaped draft the physician can
        # edit beats a crash, regardless of which vendor produced it.
        fields: dict[str, str] = {}
        for line in raw.splitlines():
            for key in ("CHIEF_COMPLAINT", "HPI", "PAST_HISTORY", "DRUG_ALLERGY", "FAMILY_HISTORY",
                        "PERSONAL_HISTORY", "ROS"):
                prefix = f"{key}:"
                if line.upper().startswith(prefix):
                    fields[key] = line.split(":", 1)[1].strip()
                    break

        def optional(key: str) -> str | None:
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
