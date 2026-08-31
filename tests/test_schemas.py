"""
Tests for app/schemas.py's data contracts. Most schemas are exercised
indirectly through the agents that use them (see tests/test_intake.py,
tests/test_triage.py, etc.) - ClinicalHistorySummary isn't consumed by
any agent yet (it's the new SIH26047-facing output contract, not wired
into the pipeline), so it gets its own direct tests here rather than
staying unverified until something happens to call it.
"""

import pytest
from pydantic import ValidationError

from app.schemas import ClinicalHistorySummary, PatientInput, TriageLevel


def test_patient_input_rejects_whitespace_only_symptom_text():
    """
    Regression test for a real bug found by brutal-input testing against
    a live server: "   " (three spaces) satisfies min_length=3 as a raw
    character count and was reaching the AI backend as if it were real
    symptom text - burning a real API call on input with no actual
    information in it. Caught by actually sending it, not assumed away.
    """
    with pytest.raises(ValidationError):
        PatientInput(symptom_text="   ")


def test_patient_input_rejects_whitespace_only_even_with_more_spaces():
    """Same bug, different length - proves this isn't just an off-by-one
    fix for exactly 3 spaces, it's a real stripped-length check."""
    with pytest.raises(ValidationError):
        PatientInput(symptom_text="          ")


def test_patient_input_accepts_real_text_with_surrounding_whitespace():
    """The fix must not reject legitimate input that merely has leading/
    trailing whitespace around real content - only whitespace-only input."""
    patient_input = PatientInput(symptom_text="  mild headache  ")
    assert patient_input.symptom_text == "  mild headache  "


def test_patient_input_rejects_zero_width_space_only_symptom_text():
    """
    Regression test for a real bug found by brutal-input testing against a
    live server: "​​​" (three U+200B ZERO WIDTH SPACE characters)
    renders as completely blank, yet satisfied both min_length=3 and the
    original _reject_whitespace_only check, because str.strip() removes
    real whitespace (category "Zs") but not invisible Unicode format
    characters (category "Cf"). Caught by actually sending the bytes, the
    same discipline that found the original whitespace-only bug.
    """
    with pytest.raises(ValidationError):
        PatientInput(symptom_text="​​​")


def test_patient_input_rejects_byte_order_mark_only_symptom_text():
    """
    Same bug, a different invisible character (U+FEFF, the BOM/zero-width
    no-break space) - proves the fix filters the whole Unicode "format"
    category, not just the one zero-width-space codepoint it was first
    found with.
    """
    with pytest.raises(ValidationError):
        PatientInput(symptom_text="﻿﻿﻿")


def test_patient_input_accepts_real_text_containing_an_incidental_zero_width_character():
    """
    The fix must not overcorrect: real symptom text that happens to
    contain an incidental zero-width character (a plausible artifact of
    mobile-keyboard/IME input or a copy-paste) must still be accepted,
    since it clearly carries real clinical content alongside the invisible
    character - only input with no real content left after filtering
    should be rejected.
    """
    patient_input = PatientInput(symptom_text="che​st pain since yesterday")
    assert patient_input.symptom_text == "che​st pain since yesterday"


def test_clinical_history_summary_builds_with_only_required_fields():
    summary = ClinicalHistorySummary(
        chief_complaint="chest pain for two days",
        history_of_present_illness="dull ache, worse on exertion, no radiation",
        priority_level=TriageLevel.URGENT,
    )
    assert summary.chief_complaint == "chest pain for two days"
    assert summary.priority_level == TriageLevel.URGENT
    # Every optional history section defaults to None, not an empty string -
    # "not asked yet" and "asked, patient said nothing" are different states,
    # same distinction app/models/ocr.py already draws for blank vs bad input.
    assert summary.past_medical_surgical_history is None
    assert summary.drug_allergy_history is None
    assert summary.family_history is None
    assert summary.personal_history is None
    assert summary.review_of_systems is None
    assert summary.prior_investigations_summary is None


def test_clinical_history_summary_defaults_to_not_yet_physician_reviewed():
    """
    The PS is explicit: the AI drafts, the doctor decides. A summary
    that hasn't been through physician review must default to
    unreviewed, not silently look final - proven here, not just
    asserted in the docstring.
    """
    summary = ClinicalHistorySummary(
        chief_complaint="mild headache",
        history_of_present_illness="onset this morning, no visual changes",
        priority_level=TriageLevel.SELF_CARE,
    )
    assert summary.is_reviewed_by_physician is False


def test_clinical_history_summary_rejects_too_short_chief_complaint():
    """Same min_length=3 contract PatientInput already enforces on symptom_text -
    consistent validation at every entry point, not just the original one."""
    with pytest.raises(ValidationError):
        ClinicalHistorySummary(
            chief_complaint="ok",
            history_of_present_illness="onset this morning",
            priority_level=TriageLevel.SELF_CARE,
        )


def test_clinical_history_summary_requires_a_priority_level():
    with pytest.raises(ValidationError):
        ClinicalHistorySummary(
            chief_complaint="chest pain",
            history_of_present_illness="onset two hours ago",
        )


def test_clinical_history_summary_accepts_full_history_when_provided():
    summary = ClinicalHistorySummary(
        chief_complaint="chest pain",
        history_of_present_illness="onset two hours ago, radiating to left arm",
        past_medical_surgical_history="hypertension, diagnosed 2019",
        drug_allergy_history="allergic to penicillin",
        family_history="father had a heart attack at 55",
        personal_history="smokes 5 cigarettes/day",
        review_of_systems="no fever, no cough",
        prior_investigations_summary="ECG from 2023: normal sinus rhythm",
        priority_level=TriageLevel.EMERGENCY,
        is_reviewed_by_physician=True,
    )
    assert summary.family_history == "father had a heart attack at 55"
    assert summary.is_reviewed_by_physician is True
