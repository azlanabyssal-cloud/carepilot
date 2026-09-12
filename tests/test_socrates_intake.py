import pytest

from app.agents.socrates_intake import (
    SocratesQuestion,
    classify_complaint_category,
    generate_followup_questions,
    generate_socrates_questions,
)


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


# --- classify_complaint_category / generate_followup_questions ------------------------


@pytest.mark.parametrize(
    "chief_complaint,expected_category",
    [
        ("chest pain since this morning", "pain_or_general"),
        ("abdominal pain", "pain_or_general"),
        ("severe headache for two days", "pain_or_general"),
        ("joint pain in both knees", "pain_or_general"),
        ("cough for the past 8 days that isn't improving", "respiratory"),
        ("shortness of breath when climbing stairs", "respiratory"),
        ("a small rash on my arm that isn't painful but has been growing", "dermatological"),
        ("itchy skin on both hands", "dermatological"),
        ("vomiting and loose motions since last night", "gastrointestinal"),
        ("feeling nauseous all day", "gastrointestinal"),
        ("high fever around 103F since yesterday, feeling very weak", "general_systemic"),
        ("fatigue and weight loss over the past month", "general_systemic"),
    ],
)
def test_classify_complaint_category_matches_real_symptom_text(chief_complaint, expected_category):
    assert classify_complaint_category(chief_complaint) == expected_category


def test_classify_complaint_category_prefers_the_more_specific_category_when_both_match():
    """
    "fever and a cough" contains both a general_systemic term (fever) and
    a respiratory term (cough) - proves the classifier picks the more
    specific, more clinically useful framework (respiratory) rather than
    the generic one that happens to match too, per _CATEGORY_TERMS's own
    documented ordering.
    """
    assert classify_complaint_category("fever and a cough") == "respiratory"


def test_classify_complaint_category_falls_back_for_an_unmatched_complaint():
    assert classify_complaint_category("slight sore throat since this morning") == "pain_or_general"


def test_generate_followup_questions_returns_socrates_for_pain_complaints():
    """
    The real regression guard for this whole feature: adding new
    categories must never change what a pain complaint gets - it must
    still be exactly generate_socrates_questions()'s own output, not a
    near-identical copy that could quietly drift from it.
    """
    assert generate_followup_questions("chest pain since this morning") == generate_socrates_questions(
        "chest pain since this morning"
    )


def test_generate_followup_questions_returns_a_different_real_template_per_category():
    respiratory = generate_followup_questions("cough for the past 8 days")
    dermatological = generate_followup_questions("itchy rash on my arm")
    gastrointestinal = generate_followup_questions("vomiting since last night")
    general_systemic = generate_followup_questions("fatigue and weight loss")

    all_question_sets = [respiratory, dermatological, gastrointestinal, general_systemic]
    for questions in all_question_sets:
        assert all(isinstance(q, SocratesQuestion) for q in questions)
        assert all(len(q.question.strip()) > 10 for q in questions)

    # Every one of the four is genuinely distinct content, not the same
    # template with a different category label slapped on.
    question_texts = [tuple(q.question for q in questions) for questions in all_question_sets]
    assert len(set(question_texts)) == len(question_texts)


def test_generate_followup_questions_does_not_graft_the_raw_complaint_into_the_question_text():
    for complaint in ("cough for the past 8 days", "itchy rash on my arm", "vomiting since last night", "fatigue and weight loss"):
        for q in generate_followup_questions(complaint):
            assert complaint.lower() not in q.question.lower()


def test_generate_followup_questions_raises_on_empty_chief_complaint():
    with pytest.raises(ValueError):
        generate_followup_questions("")


def test_generate_followup_questions_raises_on_whitespace_only_chief_complaint():
    with pytest.raises(ValueError):
        generate_followup_questions("   ")
