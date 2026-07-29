import pytest

from app.agents.triage import TriageBackendError
from app.agents.verify import GuidelineIndex, load_guideline_chunks
from app.agents.referral import load_facilities
from app.evaluation import (
    EvalCase,
    EvalCaseResult,
    compute_report,
    evaluate_case,
    load_eval_cases,
    run_evaluation,
)
from app.schemas import TriageDecision, TriageLevel


def _index():
    return GuidelineIndex(load_guideline_chunks())


def _facilities():
    return load_facilities()


def test_load_eval_cases_reads_the_bundled_dataset():
    cases = load_eval_cases()
    assert len(cases) >= 10
    levels_present = {c.expected_level for c in cases}
    # All four triage levels have at least one ground-truth case - a
    # dataset that only covered "emergency" would make the recall number
    # look good while testing nothing about the other three paths.
    assert levels_present == {
        TriageLevel.SELF_CARE,
        TriageLevel.CLINIC_VISIT,
        TriageLevel.URGENT,
        TriageLevel.EMERGENCY,
    }


def test_evaluate_case_red_flag_case_never_calls_backend():
    def backend_factory():
        raise AssertionError("backend_factory should never be called for a red-flag case")

    case = EvalCase(
        case_id="test-emergency",
        symptom_text="chest pain and sweating",
        expected_level=TriageLevel.EMERGENCY,
        notes="test fixture",
    )

    result = evaluate_case(case, _index(), _facilities(), backend_factory)

    assert result.evaluated is True
    assert result.actual_level == TriageLevel.EMERGENCY


def test_evaluate_case_reports_skipped_when_backend_unavailable():
    def failing_backend_factory():
        raise TriageBackendError("ANTHROPIC_API_KEY is not set.")

    case = EvalCase(
        case_id="test-needs-llm",
        symptom_text="mild headache today, otherwise fine",
        expected_level=TriageLevel.SELF_CARE,
        notes="test fixture - no red-flag terms, needs a real backend",
    )

    result = evaluate_case(case, _index(), _facilities(), failing_backend_factory)

    assert result.evaluated is False
    assert result.actual_level is None
    assert "ANTHROPIC_API_KEY" in result.error


def test_compute_report_emergency_recall_is_correct_with_a_known_false_negative():
    # Hand-constructed, hand-verified: 3 true emergencies, 2 correctly
    # caught, 1 missed. Expected recall = 2/3, not "some number that
    # looks plausible" - this is the actual arithmetic check.
    results = [
        EvalCaseResult(case_id="e1", expected_level=TriageLevel.EMERGENCY, actual_level=TriageLevel.EMERGENCY, evaluated=True),
        EvalCaseResult(case_id="e2", expected_level=TriageLevel.EMERGENCY, actual_level=TriageLevel.EMERGENCY, evaluated=True),
        EvalCaseResult(case_id="e3-missed", expected_level=TriageLevel.EMERGENCY, actual_level=TriageLevel.URGENT, evaluated=True),
        EvalCaseResult(case_id="s1", expected_level=TriageLevel.SELF_CARE, actual_level=TriageLevel.SELF_CARE, evaluated=True),
    ]

    report = compute_report(results)

    assert report.emergency_recall == pytest.approx(2 / 3)
    assert report.emergency_false_negatives == ["e3-missed"]
    assert report.accuracy == pytest.approx(3 / 4)


def test_compute_report_handles_no_evaluated_cases_without_crashing():
    results = [
        EvalCaseResult(case_id="skipped", expected_level=TriageLevel.URGENT, actual_level=None, evaluated=False, error="no key"),
    ]

    report = compute_report(results)

    assert report.evaluated_count == 0
    assert report.skipped_count == 1
    assert report.accuracy is None
    assert report.emergency_recall is None


def test_run_evaluation_end_to_end_reports_a_real_false_negative():
    """
    A fake backend that deliberately gets one non-red-flag emergency
    case wrong, proving the false-negative reporting actually works
    end-to-end through run_evaluation - not just in the unit-level
    compute_report test above.
    """

    class DeliberatelyWrongBackend:
        def propose(self, case) -> TriageDecision:
            # Always under-calls to urgent, regardless of what the case
            # actually needed - simulates a real model failure mode.
            return TriageDecision(level=TriageLevel.URGENT, rationale="fake underestimate", confidence=0.5)

    cases = [
        EvalCase(
            case_id="fake-em-missed-by-model",
            symptom_text="can't catch my breath at all, room is spinning",
            expected_level=TriageLevel.EMERGENCY,
            notes="paraphrased, no red-flag term, model should catch this but this fake deliberately doesn't",
        ),
        EvalCase(
            case_id="fake-urgent-correct",
            symptom_text="high fever, feeling very weak",
            expected_level=TriageLevel.URGENT,
            notes="test fixture",
        ),
    ]

    report = run_evaluation(cases, backend_factory=lambda: DeliberatelyWrongBackend())

    assert report.evaluated_count == 2
    assert report.emergency_recall == 0.0
    assert report.emergency_false_negatives == ["fake-em-missed-by-model"]
