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


def test_scan_red_flags_catches_term_split_by_a_double_space():
    # Real bug, found by simulating realistic input irregularity, not
    # theorized: every multi-word term in RED_FLAG_TERMS (e.g. "chest
    # pain") was matched with a plain `term in lowered` substring check,
    # which requires the exact single-space spelling. A patient typing
    # on a mobile keyboard, or text that has passed through OCR/voice
    # transcription, can easily produce "chest  pain" (two spaces) -
    # which is NOT a substring of "chest pain", so the deterministic
    # scan silently missed it and the case fell through to the
    # Triage-Reasoning Agent instead of short-circuiting to EMERGENCY,
    # defeating Entry 1's whole "two independent mechanisms" defense.
    flags = scan_red_flags("I have chest  pain since this morning")
    assert "chest pain" in flags


def test_scan_red_flags_catches_term_split_by_a_newline():
    # Same failure class as the double-space case above, different
    # whitespace shape - text copy-pasted from elsewhere, or a
    # line-wrapped OCR/voice-transcription artifact, can put a newline
    # where a single space belongs.
    flags = scan_red_flags("having difficulty\nbreathing right now")
    assert "difficulty breathing" in flags


def test_scan_red_flags_catches_term_split_by_a_tab():
    flags = scan_red_flags("slurred\tspeech noticed by family")
    assert "slurred speech" in flags


def test_scan_red_flags_still_misses_unrelated_text_after_whitespace_normalization():
    # Guards against the fix over-matching: normalizing whitespace must
    # not turn an unrelated phrase into a false positive.
    flags = scan_red_flags("mild  headache  since  yesterday")
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
