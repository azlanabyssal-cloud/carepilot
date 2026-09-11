import pytest

from app.agents.ayush_mode import (
    DashavidhaParameter,
    blank_ayush_assessment,
    kiosk_askable_parameters,
    load_dashavidha_parameters,
    physician_only_parameters,
)
from app.schemas import AyushAssessment


def test_load_dashavidha_parameters_returns_all_ten_named_in_the_ps():
    """
    SIH26047's own text names exactly ten parameters (see
    data/ayush/dashavidha_pariksha.json's _source field) - this proves
    the reference file actually has all ten, not a subset that quietly
    dropped one during editing.
    """
    parameters = load_dashavidha_parameters()

    assert len(parameters) == 10
    assert all(isinstance(p, DashavidhaParameter) for p in parameters)

    names = {p.name for p in parameters}
    expected = {
        "Prakriti", "Vikriti", "Sara", "Samhanana", "Pramana",
        "Satmya", "Sattva", "Ahara Shakti", "Vyayama Shakti", "Vaya",
    }
    assert names == expected


def test_load_dashavidha_parameters_every_gloss_is_real_text_not_empty():
    """Catches the specific failure mode of a name being added with a
    placeholder or forgotten gloss - every entry must have real content."""
    parameters = load_dashavidha_parameters()

    for parameter in parameters:
        assert len(parameter.gloss.strip()) > 10, f"{parameter.name} has a suspiciously short or empty gloss"


def test_load_dashavidha_parameters_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load_dashavidha_parameters(path=__import__("pathlib").Path("/nonexistent/dashavidha.json"))


def test_load_dashavidha_parameters_every_entry_has_a_real_acquisition_mode():
    """
    Added 11 Sep 2026 alongside the acquisition_mode field itself: every
    one of the ten parameters must carry a real, non-empty
    acquisition_mode and rationale - not just the name/gloss pair the
    original scaffold had. Catches a parameter silently missing this
    field the same way test_load_dashavidha_parameters_every_gloss_is_real_text_not_empty
    already catches a missing gloss.
    """
    parameters = load_dashavidha_parameters()

    valid_modes = {"patient_self_report", "mixed", "physician_assessment_required"}
    for parameter in parameters:
        assert parameter.acquisition_mode in valid_modes, f"{parameter.name} has an invalid acquisition_mode"
        assert len(parameter.acquisition_rationale.strip()) > 20, f"{parameter.name} has a suspiciously short rationale"


def test_kiosk_askable_parameters_excludes_only_physician_assessment_required():
    """
    Proves the real, load-bearing split this data models: Sara,
    Samhanana, and Pramana - the three parameters
    data/ayush/dashavidha_pariksha.json's own sourced rationale says
    require physical examination (Darshana/Sparshana) - must be
    excluded from what a kiosk can ask, while every patient_self_report
    and mixed parameter must be included.
    """
    askable = kiosk_askable_parameters()
    askable_names = {p.name for p in askable}

    assert askable_names == {
        "Prakriti", "Vikriti", "Satmya", "Sattva",
        "Ahara Shakti", "Vyayama Shakti", "Vaya",
    }
    assert all(p.kiosk_askable for p in askable)


def test_physician_only_parameters_is_the_exact_complement_of_kiosk_askable():
    """
    physician_only_parameters() and kiosk_askable_parameters() must
    partition the full ten with zero overlap and zero gap - proven by
    checking the union and intersection directly, not just trusting
    the two functions individually got it right.
    """
    all_parameters = load_dashavidha_parameters()
    askable = kiosk_askable_parameters()
    physician_only = physician_only_parameters()

    assert {p.name for p in physician_only} == {"Sara", "Samhanana", "Pramana"}
    assert not any(p.kiosk_askable for p in physician_only)

    askable_names = {p.name for p in askable}
    physician_only_names = {p.name for p in physician_only}
    assert askable_names & physician_only_names == set()
    assert askable_names | physician_only_names == {p.name for p in all_parameters}


def test_blank_ayush_assessment_has_every_field_empty_and_unreviewed():
    assessment = blank_ayush_assessment()

    assert isinstance(assessment, AyushAssessment)
    assert assessment.prakriti is None
    assert assessment.vikriti is None
    assert assessment.sara is None
    assert assessment.samhanana is None
    assert assessment.pramana is None
    assert assessment.satmya is None
    assert assessment.sattva is None
    assert assessment.ahara_shakti is None
    assert assessment.vyayama_shakti is None
    assert assessment.vaya is None
    assert assessment.reviewed_by_ayush_practitioner is False


def test_ayush_assessment_accepts_partial_data():
    """Eight of ten filled in is more useful than refusing to save
    anything because two parameters weren't answered - proven, not
    just asserted in the schema's docstring."""
    assessment = AyushAssessment(prakriti="Vata-Pitta", ahara_shakti="moderate, occasional bloating")

    assert assessment.prakriti == "Vata-Pitta"
    assert assessment.ahara_shakti == "moderate, occasional bloating"
    assert assessment.vikriti is None
