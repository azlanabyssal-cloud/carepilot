"""
CarePilot - API entrypoint.

All four agents are wired in: Intake, Triage-Reasoning,
Guideline-Verification, Referral. Each has a paired entry in
docs/INTERVIEW_NOTES.md explaining the design decisions, not just the
code. Remaining work is the CV image-triage model, the Bhashini
vernacular layer, deployment, and the explainability/evaluation pass -
see the build roadmap.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.adapters.bhashini import BhashiniAdapterError, RealBhashiniAdapter, bhashini_to_intake
from app.agents.history_intake import AnthropicHistoryDraftingBackend, HistoryDraftingError, run_history_intake
from app.agents.intake import run_intake
from app.agents.referral import load_facilities, run_referral
from app.agents.triage import AnthropicReasoningBackend, TriageBackendError, run_triage_reasoning
from app.agents.verify import GuidelineIndex, load_guideline_chunks, verify_triage_decision
from app.schemas import CaseSummary, ClinicalHistorySummary, PatientInput, ReferralResult, TriageDecision

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CarePilot",
    description="Agentic rural health-triage and referral copilot - triage aid, not a diagnostic tool.",
    version="1.0.0",
)

# Built once at import time, not per-request - both are deterministic
# given their source files, so rebuilding either on every call would be
# wasted work with no benefit.
_GUIDELINE_INDEX = GuidelineIndex(load_guideline_chunks())
_FACILITIES = load_facilities()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/intake", response_model=CaseSummary)
def intake(patient_input: PatientInput) -> CaseSummary:
    """Runs the Intake Agent only - normalization plus the deterministic red-flag scan."""
    return run_intake(patient_input)


def _run_triage(case: CaseSummary) -> TriageDecision:
    """
    Shared by /triage and /assess so both endpoints have identical
    behavior around the red-flag short-circuit and credential failures
    - duplicating this logic across two routes is exactly how they'd
    quietly drift out of sync over time.
    """
    if case.has_red_flag:
        return run_triage_reasoning(case, backend=_NullBackendNeverCalled())

    try:
        backend = AnthropicReasoningBackend()
    except TriageBackendError as exc:
        logger.error("Triage backend unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Triage reasoning backend is not configured.") from exc

    try:
        return run_triage_reasoning(case, backend)
    except TriageBackendError as exc:
        logger.error("Triage reasoning failed: %s", exc)
        raise HTTPException(status_code=503, detail="Triage reasoning backend failed after retries.") from exc


@app.post("/triage", response_model=TriageDecision)
def triage(patient_input: PatientInput) -> TriageDecision:
    """
    Runs Intake then Triage-Reasoning only - no verification, no
    referral. Kept as its own endpoint so this stage stays testable and
    demoable in isolation, same reason /intake stayed standalone.
    """
    case = run_intake(patient_input)
    return _run_triage(case)


def _run_pipeline(case: CaseSummary) -> ReferralResult:
    """
    Shared by /assess and /assess/voice - the tail end of the pipeline
    (Triage-Reasoning -> Guideline-Verification -> Referral) is identical
    regardless of whether the case arrived as typed English/Telugu text
    or as Telugu audio transcribed by Bhashini first. Extracted here so
    the two endpoints can't quietly diverge in behavior the way
    duplicating this logic inline in both would eventually allow.
    """
    decision = _run_triage(case)
    verified = verify_triage_decision(case, decision, _GUIDELINE_INDEX)
    return run_referral(case, verified, _FACILITIES)


@app.post("/assess", response_model=ReferralResult)
def assess(patient_input: PatientInput) -> ReferralResult:
    """
    The full pipeline, all four agents: Intake -> Triage-Reasoning ->
    Guideline-Verification -> Referral. This is the real product - a
    result a patient could actually act on, not an intermediate label.
    /intake and /triage stay behind it as narrower, independently
    testable slices.
    """
    case = run_intake(patient_input)
    return _run_pipeline(case)


@app.post("/assess/voice", response_model=ReferralResult)
async def assess_voice(
    audio: UploadFile = File(..., description="Telugu speech audio (flac/wav)."),
    age: Optional[int] = Form(default=None),
    duration_days: Optional[int] = Form(default=None),
) -> ReferralResult:
    """
    Telugu voice in, the same ReferralResult /assess produces out. This
    is the adapter layer app/adapters/bhashini.py was built for on Day 3
    - it was never wired into a live request path until now.

    Deliberately NOT a new agent and NOT a change to app/agents/intake.py:
    Bhashini transcription+translation happens here, at the API boundary,
    producing plain English symptom_text that flows into the exact same
    PatientInput -> run_intake -> _run_pipeline path /assess already
    uses. The red-flag scan, the LLM reasoning, the guideline check, the
    referral logic - none of it needs to know or care that this request
    started as Telugu audio instead of typed text.

    Returns 503, not a raw crash, if BHASHINI_USER_ID/BHASHINI_API_KEY
    aren't configured or the Bhashini request fails - same pattern as
    the ANTHROPIC_API_KEY handling above, applied consistently rather
    than only where it was convenient the first time.

    Also returns a clean 422, not a raw 500, if the transcribed/translated
    text is too short for PatientInput's own min_length=3 contract (e.g.
    silence, a garbled clip, or a genuinely empty translation) - see the
    real bug this closed, documented in docs/INTERVIEW_NOTES.md.
    """
    audio_bytes = await audio.read()

    try:
        adapter = RealBhashiniAdapter()
    except BhashiniAdapterError as exc:
        logger.error("Bhashini adapter unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Bhashini backend is not configured.") from exc

    try:
        symptom_text = bhashini_to_intake(adapter, audio_bytes)
    except BhashiniAdapterError as exc:
        logger.error("Bhashini request failed: %s", exc)
        raise HTTPException(status_code=503, detail="Bhashini request failed.") from exc

    try:
        patient_input = PatientInput(symptom_text=symptom_text, age=age, duration_days=duration_days)
    except ValidationError as exc:
        logger.error("Bhashini output failed PatientInput validation: %s", exc)
        raise HTTPException(
            status_code=422,
            detail="Transcribed audio did not produce usable symptom text (too short or empty).",
        ) from exc

    case = run_intake(patient_input)
    return _run_pipeline(case)


def _run_case_intake(case: CaseSummary) -> ClinicalHistorySummary:
    """
    SIH26047's actual output shape (docs/sih/SIH26047_Patient_Case_Taking_Software.md,
    Module C): a structured, physician-ready history, not a bare triage
    level. priority_level always comes from _run_triage - already
    safety-tested (red-flag short-circuit, 503 on backend failure) - and
    the History-Intake Agent never touches or infers it (see
    app/agents/history_intake.py's module docstring for why).

    For a red-flag case, the summary is built directly from the
    patient's own words, with zero calls to the drafting backend -
    mirroring Entry 4's reasoning in app/agents/triage.py: the one
    safety-critical path must not depend on any external API being
    reachable, authenticated, or correct, including this one. Every
    other case gets a real drafted narrative from
    AnthropicHistoryDraftingBackend, same 503-on-failure pattern as
    _run_triage - a drafting failure can only ever produce a clear
    error, never a wrong-but-plausible priority level, because priority
    was already decided before this function ever calls the backend.
    """
    decision = _run_triage(case)

    if case.has_red_flag:
        return ClinicalHistorySummary(
            chief_complaint=case.symptom_text,
            history_of_present_illness=case.symptom_text,
            priority_level=decision.level,
        )

    try:
        backend = AnthropicHistoryDraftingBackend()
    except HistoryDraftingError as exc:
        logger.error("History-drafting backend unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="History-drafting backend is not configured.") from exc

    try:
        return run_history_intake(case, decision, backend)
    except HistoryDraftingError as exc:
        logger.error("History drafting failed: %s", exc)
        raise HTTPException(status_code=503, detail="History-drafting backend failed after retries.") from exc


@app.post("/case-intake", response_model=ClinicalHistorySummary)
def case_intake(patient_input: PatientInput) -> ClinicalHistorySummary:
    """
    Intake -> Triage-Reasoning (decides priority_level) -> History-Intake
    (drafts the physician-ready narrative around that already-safe
    decision). Kept separate from /assess rather than replacing it:
    /assess answers "what level of care does this need," /case-intake
    answers "what's the structured history a physician can act on" -
    SIH26047's actual ask - and both share the exact same safety-critical
    priority decision underneath, never two different answers to it.

    Malformed input (e.g. symptom_text under PatientInput's own
    min_length=3) never reaches this function at all - FastAPI/Pydantic
    reject it with a 422 at the request-body boundary, same as /intake
    and /assess already do.
    """
    case = run_intake(patient_input)
    return _run_case_intake(case)


@app.post("/case-intake/voice", response_model=ClinicalHistorySummary)
async def case_intake_voice(
    audio: UploadFile = File(..., description="Telugu speech audio (flac/wav)."),
    age: Optional[int] = Form(default=None),
    duration_days: Optional[int] = Form(default=None),
) -> ClinicalHistorySummary:
    """
    Telugu voice in, the same ClinicalHistorySummary /case-intake produces
    out. Exact same wiring as /assess/voice (app/adapters/bhashini.py
    transcribes+translates at the API boundary, producing plain English
    symptom_text that flows into the same PatientInput -> run_intake ->
    _run_case_intake path /case-intake already uses) - deliberately not a
    new agent, not a change to app/agents/intake.py, same reasoning as
    /assess/voice's own docstring.

    Same failure handling as /assess/voice: 503 if Bhashini isn't
    configured or the request fails, 422 if the transcribed/translated
    text is too short for PatientInput's own min_length=3 contract.

    Real, honest limitation, stated plainly rather than glossed over:
    browser microphones typically record webm/opus via the MediaRecorder
    API, not flac/wav - this endpoint accepts whatever bytes are uploaded
    and passes them to Bhashini unchanged, matching /assess/voice's own
    behavior. Whether Bhashini's real API accepts webm/opus as well as
    flac/wav has not been confirmed against live credentials in this
    environment, same honesty standard as app/adapters/bhashini.py's own
    "Verification Status" section.
    """
    audio_bytes = await audio.read()

    try:
        adapter = RealBhashiniAdapter()
    except BhashiniAdapterError as exc:
        logger.error("Bhashini adapter unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Bhashini backend is not configured.") from exc

    try:
        symptom_text = bhashini_to_intake(adapter, audio_bytes)
    except BhashiniAdapterError as exc:
        logger.error("Bhashini request failed: %s", exc)
        raise HTTPException(status_code=503, detail="Bhashini request failed.") from exc

    try:
        patient_input = PatientInput(symptom_text=symptom_text, age=age, duration_days=duration_days)
    except ValidationError as exc:
        logger.error("Bhashini output failed PatientInput validation: %s", exc)
        raise HTTPException(
            status_code=422,
            detail="Transcribed audio did not produce usable symptom text (too short or empty).",
        ) from exc

    case = run_intake(patient_input)
    return _run_case_intake(case)


class _NullBackendNeverCalled:
    """
    Passed to run_triage_reasoning only on the red-flag path, where the
    function's own logic guarantees .propose() is never invoked. If that
    guarantee is ever broken by a future change, this raises loudly
    instead of silently trying to reach a real API with no key.
    """

    def propose(self, case) -> TriageDecision:  # pragma: no cover - should be unreachable
        raise AssertionError("Backend was called on a red-flag case - the short-circuit guarantee was broken.")


# Mounted at a sub-path, not "/", so this never shadows /health, /intake,
# /triage, /assess, /assess/voice, /case-intake, /docs, or /openapi.json -
# all of which are registered above as exact-path routes that take
# priority only because they exist; a mount at "/" would instead catch
# every unmatched path, including these, since StaticFiles(html=True)
# happily 404s or serves index.html for anything it doesn't recognize.
# This is a static demo frontend for the /case-intake endpoint (see
# web/index.html, web/app.js, web/styles.css) - no build step, no
# framework, plain files served as-is.
app.mount("/ui", StaticFiles(directory="web", html=True), name="ui")
