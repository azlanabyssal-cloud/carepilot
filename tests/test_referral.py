import pytest

from app.agents.referral import EMERGENCY_MESSAGE, SELF_CARE_MESSAGE, load_facilities, run_referral
from app.schemas import CaseSummary, Facility, TriageDecision, TriageLevel


def _case() -> CaseSummary:
    return CaseSummary(symptom_text="test symptom", age=30, duration_days=1, has_image=False, red_flag_terms=[])


def _decision(level: TriageLevel) -> TriageDecision:
    return TriageDecision(level=level, rationale="test rationale", confidence=0.8)


def _facilities() -> list[Facility]:
    return [
        Facility(name="Test District Hospital", type="District Hospital", area="Kurnool", source="test fixture"),
        Facility(name="Test PHC", type="PHC", area="Kurnool district", source="test fixture"),
    ]


def test_emergency_never_looks_up_a_facility():
    result = run_referral(_case(), _decision(TriageLevel.EMERGENCY), facilities=_facilities())

    assert result.message == EMERGENCY_MESSAGE
    assert result.facility is None


def test_self_care_gives_instructions_not_a_facility():
    result = run_referral(_case(), _decision(TriageLevel.SELF_CARE), facilities=_facilities())

    assert result.message == SELF_CARE_MESSAGE
    assert result.facility is None


def test_urgent_names_a_real_facility_with_same_day_timing():
    result = run_referral(_case(), _decision(TriageLevel.URGENT), facilities=_facilities())

    assert result.facility is not None
    assert result.facility.name == "Test District Hospital"
    assert "as soon as possible today" in result.message


def test_clinic_visit_names_a_facility_with_looser_timing():
    result = run_referral(_case(), _decision(TriageLevel.CLINIC_VISIT), facilities=_facilities())

    assert result.facility is not None
    assert "within the next day or two" in result.message


def test_clinic_visit_raises_without_any_facilities_configured():
    with pytest.raises(ValueError):
        run_referral(_case(), _decision(TriageLevel.CLINIC_VISIT), facilities=[])


def test_load_facilities_reads_the_bundled_kurnool_directory():
    facilities = load_facilities()

    assert len(facilities) >= 1
    assert all(isinstance(f, Facility) for f in facilities)
    # The first entry must be the one verified against the district's own
    # government portal - not a placeholder, since it's what MVP referral
    # actually points patients to via facilities[0].
    assert "Government General Hospital" in facilities[0].name
    assert "VERIFIED" in facilities[0].source
