from app.agents.intake import run_intake, scan_red_flags
from app.schemas import PatientInput


def test_scan_red_flags_catches_known_term():
    flags = scan_red_flags("I have had chest pain since this morning")
    assert "chest pain" in flags


def test_scan_red_flags_is_case_insensitive():
    flags = scan_red_flags("Patient is UNCONSCIOUS and not responding")
    assert "unconscious" in flags


def test_scan_red_flags_misses_paraphrase_by_design():
    # Documents a real, known limitation - see docs/INTERVIEW_NOTES.md
    # entry 1. This test exists so the limitation is asserted on
    # purpose, not discovered by accident later.
    flags = scan_red_flags("I can't catch my breath properly")
    assert flags == []


def test_run_intake_normalizes_and_flags():
    case = run_intake(
        PatientInput(symptom_text="  severe bleeding from the arm  ", age=34, duration_days=0, has_image=False)
    )
    assert case.symptom_text == "severe bleeding from the arm"
    assert case.has_red_flag is True
    assert "severe bleeding" in case.red_flag_terms


def test_run_intake_no_red_flags():
    case = run_intake(PatientInput(symptom_text="mild headache since yesterday", duration_days=1))
    assert case.has_red_flag is False
    assert case.red_flag_terms == []
