import pytest

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
