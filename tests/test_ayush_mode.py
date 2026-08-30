import pytest

from app.agents.ayush_mode import DashavidhaParameter, blank_ayush_assessment, load_dashavidha_parameters
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
