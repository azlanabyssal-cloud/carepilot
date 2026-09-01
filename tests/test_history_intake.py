import pytest
from pydantic import ValidationError

from app.agents.history_intake import (
    AnthropicHistoryDraftingBackend,
    HistoryDraft,
    HistoryDraftingError,
    run_history_intake,
)
from app.schemas import CaseSummary, TriageDecision, TriageLevel


class FakeBackend:
    """Test double implementing the HistoryDraftingBackend protocol - no network call."""

    def __init__(self, draft: HistoryDraft) -> None:
        self._draft = draft
        self.called_with: CaseSummary | None = None

    def draft(self, case: CaseSummary) -> HistoryDraft:
        self.called_with = case
        return self._draft


def _case(text: str = "chest pain for two days", red_flags: list[str] | None = None) -> CaseSummary:
    return CaseSummary(
        symptom_text=text,
        age=45,
        duration_days=2,
        has_image=False,
        red_flag_terms=red_flags or [],
    )


def test_run_history_intake_never_overrides_the_already_decided_priority():
    """
    The core safety property this whole agent exists to preserve: no
    matter what the drafting backend returns, priority_level always
    comes from the TriageDecision passed in, never from the draft -
    proven here, not just claimed in the docstring.
    """
    fake = FakeBackend(HistoryDraft(chief_complaint="mild headache", history_of_present_illness="onset today"))
    decision = TriageDecision(level=TriageLevel.EMERGENCY, rationale="red-flag term detected", confidence=1.0)

    summary = run_history_intake(_case(), decision, fake)

    assert summary.priority_level == TriageLevel.EMERGENCY
    assert summary.is_reviewed_by_physician is False


def test_run_history_intake_calls_the_backend_with_the_real_case():
    fake = FakeBackend(HistoryDraft(chief_complaint="cough", history_of_present_illness="two days, no fever"))
    case = _case("persistent cough for two days")
    decision = TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild, persistent", confidence=0.7)

    summary = run_history_intake(case, decision, fake)

    assert fake.called_with is case
    assert summary.chief_complaint == "cough"
    assert summary.history_of_present_illness == "two days, no fever"


def test_run_history_intake_carries_optional_fields_through_when_present():
    fake = FakeBackend(
        HistoryDraft(
            chief_complaint="chest pain",
            history_of_present_illness="onset two hours ago",
            past_medical_surgical_history="hypertension",
            drug_allergy_history="penicillin allergy",
            family_history="father had a heart attack",
            personal_history="smoker",
            review_of_systems="no fever",
        )
    )
    decision = TriageDecision(level=TriageLevel.URGENT, rationale="needs same-day review", confidence=0.75)

    summary = run_history_intake(_case(), decision, fake)

    assert summary.past_medical_surgical_history == "hypertension"
    assert summary.drug_allergy_history == "penicillin allergy"
    assert summary.family_history == "father had a heart attack"
    assert summary.personal_history == "smoker"
    assert summary.review_of_systems == "no fever"


def test_anthropic_history_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HistoryDraftingError):
        AnthropicHistoryDraftingBackend(api_key=None)


def test_anthropic_history_backend_parses_well_formed_response():
    backend = AnthropicHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
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


def test_anthropic_history_backend_parses_zero_width_space_chief_complaint_as_present_not_blank():
    """
    Reproduces, through the real _parse() path (not a constructed
    HistoryDraft), the input shape that exposed a real bug: a response
    line "CHIEF_COMPLAINT: ​​​" (three U+200B ZERO WIDTH SPACE
    characters) survives _parse()'s own `.strip()` unchanged - str.strip()
    only removes Unicode whitespace (category "Zs"), not invisible
    Unicode format characters (category "Cf") - so it's non-empty/truthy
    and _parse()'s `fields.get("CHIEF_COMPLAINT") or case.symptom_text`
    fallback never fires. This asserts the honest, narrow fact about
    _parse() itself: it hands the invisible text through unchanged,
    exactly as a non-empty visible string would be. The next test proves
    what used to happen next, and what now happens instead.
    """
    backend = AnthropicHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    case = _case("mild headache, no other symptoms")
    raw = (
        "CHIEF_COMPLAINT: ​​​\n"
        "HPI: mild headache, no other symptoms\n"
        "PAST_HISTORY: NONE\n"
        "DRUG_ALLERGY: NONE\n"
        "FAMILY_HISTORY: NONE\n"
        "PERSONAL_HISTORY: NONE\n"
        "ROS: NONE"
    )

    draft = backend._parse(raw, case)

    assert draft.chief_complaint == "​​​"
    assert draft.chief_complaint != case.symptom_text


def test_run_history_intake_rejects_a_zero_width_space_only_chief_complaint_instead_of_persisting_it():
    """
    Regression test for a real bug: before app/schemas.py's
    ClinicalHistorySummary gained its own _reject_invisible_chief_complaint
    validator, a HistoryDraft carrying an invisible-only chief_complaint
    (the exact shape the previous test proves _parse() can produce)
    would satisfy min_length=3 as a raw character count and construct
    successfully - a summary a physician opens and sees as completely
    blank, persisted as if it were real. run_history_intake() must now
    raise pydantic's ValidationError instead, the same signal
    app/main.py's _run_case_intake already catches and turns into a
    clean 503 rather than persisting an unusable draft (see
    app/main.py's own comment on that except-ValidationError branch).
    """
    fake = FakeBackend(
        HistoryDraft(chief_complaint="​​​", history_of_present_illness="onset this morning")
    )
    decision = TriageDecision(level=TriageLevel.SELF_CARE, rationale="mild, no red flags", confidence=0.8)

    with pytest.raises(ValidationError):
        run_history_intake(_case(), decision, fake)


def test_anthropic_history_backend_parses_zero_width_space_hpi_as_present_not_blank():
    """
    Same failure class as test_anthropic_history_backend_parses_zero_width_space_chief_complaint_as_present_not_blank
    above, found by auditing _parse() for every field sharing its
    `fields.get(KEY) or case.symptom_text` fallback pattern, not just the one
    already fixed. A response line "HPI: ​​​" (three U+200B ZERO WIDTH SPACE
    characters) survives _parse()'s own `.strip()` unchanged for the exact
    same reason chief_complaint's did - str.strip() removes Unicode
    whitespace (category "Zs") but not invisible Unicode format characters
    (category "Cf") - so it's non-empty/truthy and never triggers _parse()'s
    `or case.symptom_text` fallback. This asserts the honest, narrow fact
    about _parse() itself: it hands the invisible text through unchanged.
    The next test proves what used to happen next, and what now happens
    instead.
    """
    backend = AnthropicHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    case = _case("mild headache, no other symptoms")
    raw = (
        "CHIEF_COMPLAINT: mild headache\n"
        "HPI: ​​​\n"
        "PAST_HISTORY: NONE\n"
        "DRUG_ALLERGY: NONE\n"
        "FAMILY_HISTORY: NONE\n"
        "PERSONAL_HISTORY: NONE\n"
        "ROS: NONE"
    )

    draft = backend._parse(raw, case)

    assert draft.history_of_present_illness == "​​​"
    assert draft.history_of_present_illness != case.symptom_text


def test_run_history_intake_rejects_a_zero_width_space_only_hpi_instead_of_persisting_it():
    """
    Regression test for a real bug: before app/schemas.py's
    ClinicalHistorySummary.history_of_present_illness gained a min_length=3
    Field constraint and its own _reject_invisible_history_of_present_illness
    validator, a HistoryDraft carrying an invisible-only
    history_of_present_illness (the exact shape the previous test proves
    _parse() can produce) would construct successfully with zero
    validation - unlike chief_complaint, this field had no min_length at
    all before this fix. run_history_intake() must now raise pydantic's
    ValidationError instead, the same signal app/main.py's _run_case_intake
    already catches and turns into a clean 503 rather than persisting an
    unusable draft.
    """
    fake = FakeBackend(
        HistoryDraft(chief_complaint="chest pain", history_of_present_illness="​​​")
    )
    decision = TriageDecision(level=TriageLevel.SELF_CARE, rationale="mild, no red flags", confidence=0.8)

    with pytest.raises(ValidationError):
        run_history_intake(_case(), decision, fake)


def test_anthropic_history_backend_falls_back_to_patient_text_on_unparseable_response():
    """
    If the model's response doesn't follow the requested format at all,
    the required fields must still be non-empty (ClinicalHistorySummary
    enforces min_length=3 on chief_complaint) - falling back to the
    patient's own reported text is the honest, non-inventing recovery,
    not a crash or a fabricated placeholder.
    """
    backend = AnthropicHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    case = _case("severe stomach pain since last night")

    draft = backend._parse("I'm not sure how to format this.", case)

    assert draft.chief_complaint == case.symptom_text
    assert draft.history_of_present_illness == case.symptom_text
