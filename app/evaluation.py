"""
Evaluation harness.

The metric this project has repeatedly said matters more than raw
accuracy - recall on emergency-flagged cases - has been a checklist item
since Day 1 and never actually computed. This module computes it, for
real, against a real (small, authored, honestly-labeled) test set.

Two honest limits, stated up front rather than discovered by reading
500 lines of code:

1. data/evaluation/test_cases.json is AUTHORED for this project, not
   drawn from a real clinical dataset - same STARTER_SEED-style honesty
   as data/guidelines/seed_guidelines.json and
   data/facilities/kurnool_facilities.json. Each case's "notes" field
   says so explicitly.

2. Cases that don't contain a deterministic red-flag term need a real
   ANTHROPIC_API_KEY to evaluate - the Triage-Reasoning Agent's LLM call
   is what's supposed to catch them, not this harness. Without a key,
   this module still runs and reports which cases it could NOT evaluate
   and why, rather than silently skipping them or crashing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from app.agents.intake import run_intake
from app.agents.referral import load_facilities, run_referral
from app.agents.triage import ReasoningBackend, TriageBackendError, run_triage_reasoning
from app.agents.verify import GuidelineIndex, load_guideline_chunks, verify_triage_decision
from app.schemas import PatientInput, TriageDecision, TriageLevel

logger = logging.getLogger(__name__)

DEFAULT_TEST_CASES_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "evaluation" / "test_cases.json"
)


class EvalCase(BaseModel):
    case_id: str
    symptom_text: str
    age: Optional[int] = None
    duration_days: Optional[int] = None
    expected_level: TriageLevel
    notes: str


class EvalCaseResult(BaseModel):
    case_id: str
    expected_level: TriageLevel
    actual_level: Optional[TriageLevel] = None
    evaluated: bool
    error: Optional[str] = None


class EvaluationReport(BaseModel):
    results: list[EvalCaseResult]
    evaluated_count: int
    skipped_count: int
    accuracy: Optional[float] = None
    emergency_recall: Optional[float] = None
    emergency_false_negatives: list[str] = []


class _BackendNeverCalled:
    """
    Passed only on the red-flag path, where run_triage_reasoning's own
    logic guarantees .propose() is never invoked. Same guardrail idea as
    app/main.py's _NullBackendNeverCalled - kept as a separate small
    class here rather than imported from main.py, since this harness has
    no reason to depend on the API layer to do batch evaluation.
    """

    def propose(self, case) -> TriageDecision:  # pragma: no cover - should be unreachable
        raise AssertionError("Backend was called on a red-flag case during evaluation - short-circuit broke.")


def load_eval_cases(path: Path = DEFAULT_TEST_CASES_PATH) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(**entry) for entry in raw]


def evaluate_case(eval_case: EvalCase, guideline_index: GuidelineIndex, facilities, backend_factory) -> EvalCaseResult:
    """
    backend_factory: a zero-argument callable returning a ReasoningBackend,
    called only when the case actually needs one (i.e. no red-flag term
    matched). Passing this as a factory, not a constructed instance,
    means a missing ANTHROPIC_API_KEY only affects the cases that
    actually need the LLM - the red-flag-covered cases evaluate
    correctly regardless, exactly mirroring app/main.py's own behavior.
    """
    patient_input = PatientInput(
        symptom_text=eval_case.symptom_text,
        age=eval_case.age,
        duration_days=eval_case.duration_days,
    )
    case = run_intake(patient_input)

    try:
        if case.has_red_flag:
            decision = run_triage_reasoning(case, backend=_BackendNeverCalled())
        else:
            backend: ReasoningBackend = backend_factory()
            decision = run_triage_reasoning(case, backend)
    except TriageBackendError as exc:
        return EvalCaseResult(
            case_id=eval_case.case_id,
            expected_level=eval_case.expected_level,
            actual_level=None,
            evaluated=False,
            error=str(exc),
        )

    verified = verify_triage_decision(case, decision, guideline_index)
    referral = run_referral(case, verified, facilities)

    return EvalCaseResult(
        case_id=eval_case.case_id,
        expected_level=eval_case.expected_level,
        actual_level=referral.level,
        evaluated=True,
        error=None,
    )


def compute_report(results: list[EvalCaseResult]) -> EvaluationReport:
    evaluated = [r for r in results if r.evaluated]
    skipped = [r for r in results if not r.evaluated]

    accuracy = None
    if evaluated:
        correct = sum(1 for r in evaluated if r.actual_level == r.expected_level)
        accuracy = correct / len(evaluated)

    emergency_recall = None
    false_negatives: list[str] = []
    true_emergencies = [r for r in evaluated if r.expected_level == TriageLevel.EMERGENCY]
    if true_emergencies:
        caught = [r for r in true_emergencies if r.actual_level == TriageLevel.EMERGENCY]
        emergency_recall = len(caught) / len(true_emergencies)
        false_negatives = [r.case_id for r in true_emergencies if r.actual_level != TriageLevel.EMERGENCY]

    return EvaluationReport(
        results=results,
        evaluated_count=len(evaluated),
        skipped_count=len(skipped),
        accuracy=accuracy,
        emergency_recall=emergency_recall,
        emergency_false_negatives=false_negatives,
    )


def run_evaluation(
    cases: list[EvalCase],
    backend_factory,
    guideline_index: Optional[GuidelineIndex] = None,
    facilities=None,
) -> EvaluationReport:
    index = guideline_index or GuidelineIndex(load_guideline_chunks())
    facility_list = facilities if facilities is not None else load_facilities()

    results = [evaluate_case(case, index, facility_list, backend_factory) for case in cases]
    return compute_report(results)


def _print_report(report: EvaluationReport) -> None:
    print(f"Evaluated: {report.evaluated_count} / {report.evaluated_count + report.skipped_count} cases")
    if report.skipped_count:
        print(f"Skipped (backend unavailable): {report.skipped_count}")
    if report.accuracy is not None:
        print(f"Overall accuracy (evaluated cases only): {report.accuracy:.0%}")
    if report.emergency_recall is not None:
        print(f"Emergency recall (the metric that matters): {report.emergency_recall:.0%}")
        if report.emergency_false_negatives:
            print(f"  FALSE NEGATIVES (missed real emergencies): {report.emergency_false_negatives}")
    else:
        print("Emergency recall: not computable - no true-emergency cases were evaluated.")
    print()
    for r in report.results:
        status = f"-> {r.actual_level.value}" if r.evaluated else f"SKIPPED ({r.error})"
        match = "OK" if (r.evaluated and r.actual_level == r.expected_level) else ""
        print(f"  {r.case_id:30s} expected={r.expected_level.value:12s} {status} {match}")


if __name__ == "__main__":
    from app.agents.triage import AnthropicReasoningBackend

    eval_cases = load_eval_cases()
    report = run_evaluation(eval_cases, backend_factory=AnthropicReasoningBackend)
    _print_report(report)
