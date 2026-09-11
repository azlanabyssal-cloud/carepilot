import pytest

from app.agents.socrates_intake import SocratesQuestion, generate_socrates_questions


def test_generate_socrates_questions_returns_all_eight_categories_in_standard_order():
    """
    SOCRATES is a real, fixed eight-category mnemonic - this proves all
    eight are present, in the standard order, not a subset that quietly
    dropped one during editing.
    """
    questions = generate_socrates_questions("chest pain since this morning")

    categories = [q.category for q in questions]
    assert categories == [
        "Site",
        "Onset",
        "Character",
        "Radiation",
        "Associated symptoms",
        "Time course",
        "Exacerbating/relieving factors",
        "Severity",
    ]
    assert all(isinstance(q, SocratesQuestion) for q in questions)


def test_generate_socrates_questions_every_question_is_real_text_not_empty():
    questions = generate_socrates_questions("abdominal pain")

    for q in questions:
        assert len(q.question.strip()) > 10, f"{q.category} has a suspiciously short or empty question"


def test_generate_socrates_questions_is_identical_regardless_of_complaint_text():
    """
    Proves the real design claim in this module's own docstring: the
    eight-question set is complaint-agnostic by clinical design, not
    branching per exact wording - two very different complaints must
    produce the exact same question set, not two different ones that
    happen to look similar.
    """
    chest_pain_questions = generate_socrates_questions("chest pain since this morning")
    headache_questions = generate_socrates_questions("severe headache for two days")

    assert chest_pain_questions == headache_questions


def test_generate_socrates_questions_does_not_graft_the_raw_complaint_into_the_question_text():
    """
    Real, deliberate design choice, not an oversight: questions use
    "it"/"this", never the raw complaint string - proven here so a
    future edit can't silently start string-formatting the complaint
    into these templates and produce broken-English questions for a
    full-sentence complaint like "chest pain since this morning."
    """
    questions = generate_socrates_questions("chest pain since this morning")

    for q in questions:
        assert "chest pain" not in q.question.lower()
        assert "since this morning" not in q.question.lower()


def test_generate_socrates_questions_raises_on_empty_chief_complaint():
    with pytest.raises(ValueError):
        generate_socrates_questions("")


def test_generate_socrates_questions_raises_on_whitespace_only_chief_complaint():
    with pytest.raises(ValueError):
        generate_socrates_questions("   ")
