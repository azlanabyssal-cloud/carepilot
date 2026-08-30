import pytest

from app.agents.groq_backends import GroqHistoryDraftingBackend, GroqReasoningBackend
from app.agents.history_intake import HistoryDraftingError
from app.agents.triage import TriageBackendError
from app.schemas import CaseSummary, TriageLevel


def _case(text: str = "chest pain for two days") -> CaseSummary:
    return CaseSummary(
        symptom_text=text,
        age=45,
        duration_days=2,
        has_image=False,
        red_flag_terms=[],
    )


# -- GroqReasoningBackend -----------------------------------------------------


def test_groq_reasoning_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(TriageBackendError):
        GroqReasoningBackend(api_key=None)


def test_groq_reasoning_backend_parses_well_formed_response():
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: Symptom pattern warrants same-day evaluation."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT
    assert decision.rationale == "Symptom pattern warrants same-day evaluation."


def test_groq_reasoning_backend_defaults_to_urgent_on_unparseable_level():
    """
    Same cautious-default safety property as
    AnthropicReasoningBackend._parse: an unrecognized LEVEL value must
    fail toward the more cautious "urgent" rather than the more
    convenient "self_care" - proven here, not just assumed to carry
    over because the code was copied.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: not_a_real_level\nRATIONALE: unclear."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT


def test_groq_reasoning_backend_builds_prompt_in_the_shared_line_format():
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    prompt = backend._build_prompt(_case("mild cough for two days"))

    assert "LEVEL: <self_care|clinic_visit|urgent|emergency>" in prompt
    assert "RATIONALE:" in prompt
    assert "mild cough for two days" in prompt


# -- GroqHistoryDraftingBackend ------------------------------------------------


def test_groq_history_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(HistoryDraftingError):
        GroqHistoryDraftingBackend(api_key=None)


def test_groq_history_backend_parses_well_formed_response():
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    raw = (
        "CHIEF_COMPLAINT: chest pain\n"
        "HPI: onset this morning, dull ache, worse on exertion\n"
        "PAST_HISTORY: NONE\n"
        "DRUG_ALLERGY: NONE\n"
        "FAMILY_HISTORY: father had a heart attack at 55\n"
        "PERSONAL_HISTORY: NONE\n"
        "ROS: no fever, no cough"
    )

    draft = backend._parse(raw, _case())

    assert draft.chief_complaint == "chest pain"
    assert draft.history_of_present_illness == "onset this morning, dull ache, worse on exertion"
    # "NONE" in the model's own response must become a real None, not the literal string -
    # otherwise a physician's UI would show the word "NONE" instead of a blank field.
    assert draft.past_medical_surgical_history is None
    assert draft.drug_allergy_history is None
    assert draft.family_history == "father had a heart attack at 55"
    assert draft.personal_history is None
    assert draft.review_of_systems == "no fever, no cough"


def test_groq_history_backend_falls_back_to_patient_text_on_unparseable_response():
    """
    Same fallback safety property as
    AnthropicHistoryDraftingBackend._parse: when the model's response
    doesn't follow the requested format, chief_complaint and
    history_of_present_illness must still be non-empty
    (ClinicalHistorySummary enforces min_length=3 on chief_complaint) -
    falling back to the patient's own reported text is the honest
    recovery, not a crash or a fabricated placeholder.
    """
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    case = _case("severe stomach pain since last night")

    draft = backend._parse("I'm not sure how to format this.", case)

    assert draft.chief_complaint == case.symptom_text
    assert draft.history_of_present_illness == case.symptom_text


def test_groq_history_backend_builds_prompt_in_the_shared_line_format():
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    prompt = backend._build_prompt(_case("persistent cough for two days"))

    assert "CHIEF_COMPLAINT:" in prompt
    assert "HPI:" in prompt
    assert "ROS:" in prompt
    assert "persistent cough for two days" in prompt
