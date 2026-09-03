import pytest
from pydantic import ValidationError

from app.agents.triage import (
    AnthropicReasoningBackend,
    TriageBackendError,
    run_triage_reasoning,
)
from app.schemas import CaseSummary, TriageDecision, TriageLevel


class FakeBackend:
    """Test double implementing the ReasoningBackend protocol - no network call."""

    def __init__(self, decision: TriageDecision) -> None:
        self._decision = decision
        self.called = False

    def propose(self, case: CaseSummary) -> TriageDecision:
        self.called = True
        return self._decision


def _case(text: str, red_flags: list[str] | None = None) -> CaseSummary:
    return CaseSummary(
        symptom_text=text,
        age=30,
        duration_days=1,
        has_image=False,
        red_flag_terms=red_flags or [],
    )


def test_red_flag_case_short_circuits_without_calling_backend():
    fake = FakeBackend(TriageDecision(level=TriageLevel.SELF_CARE, rationale="should not be used", confidence=0.5))
    case = _case("chest pain", red_flags=["chest pain"])

    decision = run_triage_reasoning(case, fake)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.confidence == 1.0
    assert fake.called is False  # this is the actual point of the design - proven, not claimed


def test_ordinary_case_delegates_to_backend():
    fake = FakeBackend(
        TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="persistent mild symptom", confidence=0.7)
    )
    case = _case("mild cough for two days")

    decision = run_triage_reasoning(case, fake)

    assert decision.level == TriageLevel.CLINIC_VISIT
    assert fake.called is True


def test_anthropic_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(TriageBackendError):
        AnthropicReasoningBackend(api_key=None)


def test_anthropic_backend_parses_well_formed_response():
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: Symptom pattern warrants same-day evaluation."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT
    assert decision.rationale == "Symptom pattern warrants same-day evaluation."


def test_anthropic_backend_defaults_to_urgent_on_unparseable_level():
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: not_a_real_level\nRATIONALE: unclear."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT


def test_anthropic_backend_parse_rejects_zero_width_space_only_rationale():
    """
    Regression test for a real bug, the same failure class as
    ClinicalHistorySummary.chief_complaint/history_of_present_illness
    (see docs/INTERVIEW_NOTES.md, Days 8-9): _parse()'s
    `line.split(":", 1)[1].strip()` on a "RATIONALE: ​​​" (three U+200B
    ZERO WIDTH SPACE characters) response line leaves the invisible
    characters untouched - non-empty per str.strip() - so before
    TriageDecision.rationale had its own _visible_length-based validator
    (app/schemas.py), this constructed a TriageDecision whose rationale
    renders as completely blank. _parse() itself has no try/except, so
    the underlying pydantic.ValidationError surfaces directly here -
    see test_anthropic_backend_propose_converts_invalid_rationale_to_triage_backend_error
    below for proof that propose() (the real call path) converts it to
    the same TriageBackendError every other backend failure already is.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: ​​​"

    with pytest.raises(ValidationError):
        backend._parse(raw)


def test_anthropic_backend_propose_converts_invalid_rationale_to_triage_backend_error(monkeypatch):
    """
    Proves propose() - the actual method run_triage_reasoning() calls,
    not _parse() in isolation - catches the ValidationError above and
    raises TriageBackendError instead, the same failure convention every
    other backend error in this module already uses. Without this,
    app/main.py's _run_triage (which only catches TriageBackendError,
    not ValidationError) would let this surface as a raw 500 instead of
    the clean 503 test_main.py's
    test_assess_ordinary_case_returns_503_not_500_when_backend_rationale_is_invisible_only
    proves it now returns.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    monkeypatch.setattr(backend, "_call", lambda case: "LEVEL: urgent\nRATIONALE: ​​​")
    case = _case("mild cough for two days")

    with pytest.raises(TriageBackendError):
        backend.propose(case)


def test_anthropic_backend_call_converts_empty_content_response_to_triage_backend_error(monkeypatch):
    """
    Real bug, found by auditing every third-party-API backend in this
    codebase for the same failure class the last five days' entries in
    docs/INTERVIEW_NOTES.md already fixed elsewhere: a manually-parsed
    response shape that isn't defended against raising a raw, uncaught
    exception. GroqReasoningBackend._call (app/agents/groq_backends.py)
    already wraps its own response-shape parsing in
    `except (KeyError, IndexError)`, and app/adapters/bhashini.py does
    the same in four places - but AnthropicReasoningBackend._call's
    `message.content[0].text` had no such guard. Reproduced directly
    first: `backend._client.messages.create` returning a message whose
    `.content` is an empty list makes `message.content[0]` raise a raw
    IndexError - confirmed via a Python REPL before this test or the fix
    were written. Without the fix, that IndexError is not one of the
    types propose()'s own `except (APIConnectionError, RateLimitError,
    APIStatusError)` matches, so it would propagate straight through
    run_triage_reasoning() and out of app/main.py's _run_triage (which
    only catches TriageBackendError) as a raw 500 - see
    test_assess_ordinary_case_returns_503_not_500_when_backend_returns_no_content_blocks
    in tests/test_main.py for the live-endpoint proof.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")

    class _EmptyContentMessage:
        content: list = []

    monkeypatch.setattr(backend._client.messages, "create", lambda **kwargs: _EmptyContentMessage())
    case = _case("mild cough for two days")

    with pytest.raises(TriageBackendError, match="Unexpected Anthropic response shape"):
        backend._call(case)


def test_anthropic_backend_propose_converts_empty_content_response_to_triage_backend_error(monkeypatch):
    """
    Same regression as the test above, exercised through propose() - the
    method run_triage_reasoning() actually calls - not _call() in
    isolation, the same "prove it at the real call path, not just the
    helper" standard test_anthropic_backend_propose_converts_invalid_rationale_to_triage_backend_error
    above already uses.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")

    class _EmptyContentMessage:
        content: list = []

    monkeypatch.setattr(backend._client.messages, "create", lambda **kwargs: _EmptyContentMessage())
    case = _case("mild cough for two days")

    with pytest.raises(TriageBackendError, match="Unexpected Anthropic response shape"):
        backend.propose(case)
