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
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.adapters.bhashini import BhashiniAdapterError, RealBhashiniAdapter, bhashini_to_intake
from app.agents.history_intake import AnthropicHistoryDraftingBackend, HistoryDraftingError, run_history_intake
from app.agents.intake import run_intake
from app.agents.referral import load_facilities, run_referral
from app.agents.triage import AnthropicReasoningBackend, TriageBackendError, run_triage_reasoning
from app.agents.verify import GuidelineIndex, load_guideline_chunks, verify_triage_decision
from app.db import CaseStore
from app.models.ocr import OcrError, extract_dates, extract_medication_mentions, extract_text
from app.schemas import CaseSummary, ClinicalHistorySummary, PatientInput, ReferralResult, TriageDecision

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CarePilot",
    description="Agentic rural health-triage and referral copilot - triage aid, not a diagnostic tool.",
    version="1.0.0",
)

# Built once at import time, not per-request - _GUIDELINE_INDEX and
# _FACILITIES are deterministic given their source files, so rebuilding
# either on every call would be wasted work with no benefit. _CASE_STORE
# is different in kind (it owns durable state on disk, not a rebuildable
# in-memory index) but the same "one shared instance for the process
# lifetime" shape - see app/db.py's CaseStore docstring for why that's
# still safe here despite FastAPI running sync routes across a
# worker-thread pool.
_GUIDELINE_INDEX = GuidelineIndex(load_guideline_chunks())
_FACILITIES = load_facilities()
_CASE_STORE = CaseStore()


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
    except ValidationError as exc:
        # The backend responded and _parse() ran, but produced a
        # chief_complaint under ClinicalHistorySummary's own
        # min_length=3 (e.g. a one/two-word non-answer like "ok" that
        # survives the `or case.symptom_text` fallback because it's
        # non-empty). Same failure class as the Day 6 /assess/voice
        # bug: a manually-constructed Pydantic model bypasses FastAPI's
        # automatic request-body validation, so this must be caught
        # explicitly or it surfaces as a raw 500.
        logger.error("History-drafting backend produced an invalid draft: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="History-drafting backend produced an unusable draft.",
        ) from exc


@app.post("/case-intake", response_model=ClinicalHistorySummary)
def case_intake(patient_input: PatientInput) -> ClinicalHistorySummary:
    """
    Intake -> Triage-Reasoning (decides priority_level) -> History-Intake
    (drafts the physician-ready narrative around that already-safe
    decision) -> persisted (app/db.py's CaseStore), so the result is
    something a physician can pull back up later via GET /cases/{case_id},
    not just a response that flashes by once. Kept separate from /assess
    rather than replacing it: /assess answers "what level of care does
    this need," /case-intake answers "what's the structured history a
    physician can act on" - SIH26047's actual ask - and both share the
    exact same safety-critical priority decision underneath, never two
    different answers to it.

    Malformed input (e.g. symptom_text under PatientInput's own
    min_length=3) never reaches this function at all - FastAPI/Pydantic
    reject it with a 422 at the request-body boundary, same as /intake
    and /assess already do.
    """
    case = run_intake(patient_input)
    summary = _run_case_intake(case)
    case_id = _CASE_STORE.save(summary, source="text")
    return summary.model_copy(update={"case_id": case_id})


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

    Persisted the same way /case-intake is (app/db.py's CaseStore,
    source="voice" instead of "text") - a case captured by voice is no
    less real, and no less something a physician needs to find later,
    than one typed in directly.
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
    summary = _run_case_intake(case)
    case_id = _CASE_STORE.save(summary, source="voice")
    return summary.model_copy(update={"case_id": case_id})


def _build_investigations_summary(ocr_text: str, medications: list[str], dates: list[str]) -> str:
    """
    Turns raw OCR'd document text into the short, physician-scannable
    summary that fills ClinicalHistorySummary.prior_investigations_summary
    - not the raw OCR dump itself, which is often long and includes OCR
    noise. Medications and dates are surfaced as their own lines because
    they're the two things Module B specifically asks a physician be able
    to see at a glance, not because the raw text alone is unreadable.
    """
    lines = []
    if medications:
        lines.append("Possible medications mentioned: " + ", ".join(medications))
    if dates:
        lines.append("Dates found in document: " + ", ".join(dates))
    lines.append("Extracted document text: " + ocr_text.strip())
    return "\n".join(lines)


@app.post("/case-intake/document", response_model=ClinicalHistorySummary)
async def case_intake_document(
    symptom_text: str = Form(..., min_length=3),
    age: Optional[int] = Form(default=None),
    duration_days: Optional[int] = Form(default=None),
    document: UploadFile = File(..., description="A photo or scan of a prescription/lab report/discharge summary."),
) -> ClinicalHistorySummary:
    """
    Module B's actual ask: a patient photographs an existing prescription
    or lab report alongside describing their symptoms, and the resulting
    summary's prior_investigations_summary field carries what OCR could
    read from it (app/models/ocr.py's extract_text), plus the medications
    and dates that OCR extraction was able to pick out
    (extract_medication_mentions, extract_dates) - both already real,
    tested, heuristic (not clinical-NLP) functions, not new here.

    Deliberately single-document per request, not the full multi-document
    chronological timeline app/models/ocr.py's build_document_timeline
    supports - wiring in multiple uploads and a real timeline view is a
    real, named next step, not implemented here to keep this endpoint's
    scope honest and its behavior easy to reason about.

    A bad/undecodable image raises OcrError from extract_text, returned
    here as a clear 422 - never silently treated as "no document text
    found," which would look identical to a genuinely blank document and
    hide a real upload problem from the caller.

    Persisted the same way /case-intake and /case-intake/voice are
    (app/db.py's CaseStore, source="document"), and with
    prior_investigations_summary already merged in first - the whole
    point of saving a document-backed case is that the OCR'd findings are
    still there the next time a physician pulls it up, not just the
    narrative history.
    """
    try:
        patient_input = PatientInput(
            symptom_text=symptom_text, age=age, duration_days=duration_days, has_image=True
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Symptom text was too short or invalid.") from exc

    document_bytes = await document.read()

    try:
        ocr_text = extract_text(document_bytes)
    except OcrError as exc:
        logger.error("OCR failed on uploaded document: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not read the uploaded document: {exc}") from exc

    medications = extract_medication_mentions(ocr_text)
    dates = extract_dates(ocr_text)
    investigations_summary = _build_investigations_summary(ocr_text, medications, dates)

    case = run_intake(patient_input)
    summary = _run_case_intake(case)
    summary = summary.model_copy(update={"prior_investigations_summary": investigations_summary})
    case_id = _CASE_STORE.save(summary, source="document")
    return summary.model_copy(update={"case_id": case_id})


@app.get("/cases", response_model=list[ClinicalHistorySummary])
def list_cases() -> list[ClinicalHistorySummary]:
    """
    Physician-facing case lookup - the actual reason /case-intake* saves
    anything at all. Without an endpoint to read it back, a persisted
    case is no more useful to a physician than an unpersisted one.
    Most-recent-first (app/db.py's CaseStore.list_recent), capped at 50 -
    a real, named scope limit, not pagination, since nothing here yet
    needs to browse deep case history.
    """
    return _CASE_STORE.list_recent()


@app.get("/cases/{case_id}", response_model=ClinicalHistorySummary)
def get_case(case_id: str) -> ClinicalHistorySummary:
    """
    Look up one previously persisted case by its case_id - the id every
    /case-intake* response now carries once saved. 404, not a silent
    empty/null response, when it doesn't exist: "no such case" and "here
    is an empty case" are different states a caller needs to tell apart,
    same distinction app/models/ocr.py already draws between an
    undecodable image and a genuinely blank one.
    """
    summary = _CASE_STORE.get(case_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return summary


@app.get("/cases/{case_id}/audio-summary")
def case_audio_summary(case_id: str, language: Literal["en", "hi", "te"] = "en") -> Response:
    """
    Audio OUTPUT - the half of "Audio input and Output" that had no code
    at all until now. Voice INPUT already worked end-to-end
    (/case-intake/voice, via app/adapters/bhashini.py's transcribe +
    translate); this is the reverse direction, using that same adapter's
    new synthesize() method - see its docstring, and the module
    docstring's TTS ADDENDUM, for exactly what is and isn't verified
    about it.

    Deliberately not clever NLG: the spoken text is a fixed, two-part
    template built from exactly two already-decided fields
    (priority_level, chief_complaint) - e.g. "Priority level: emergency.
    Chief complaint: severe bleeding." The same "state exactly what this
    does, not more" discipline this whole file already holds itself to,
    not an attempt at a naturally-worded summary.

    For hi/te, the template is translated to that language (via the same
    adapter.translate() /case-intake/voice already uses, in the opposite
    direction) before synthesis - closing what was originally a named
    limitation here: without this, a hi/te request asked Bhashini to
    speak the English-template string in that language's voice, not an
    actual Hindi/Telugu sentence. Translation failure is treated the same
    as synthesis failure (503, "Bhashini speech synthesis failed") rather
    than a separate error branch - from the caller's point of view both
    are "this endpoint's Bhashini-backed audio pipeline didn't work,"
    not two different failures to distinguish.

    404 if case_id doesn't exist - same _CASE_STORE.get() contract as
    GET /cases/{case_id}. 503 if the Bhashini adapter isn't configured or
    translation/synthesis itself fails - the same failure convention
    every other backend branch in this file already uses, not a new one
    invented for this endpoint. `language` outside en/hi/te is rejected
    with FastAPI's own automatic 422 (a Literal type, not a manual check)
    - the same "validate at the boundary" discipline
    docs/INTERVIEW_NOTES.md's Entry 2 already established for this
    codebase.

    Returns a raw Response, not response_model=..., because the body is
    audio bytes, not a JSON shape Pydantic could serialize.
    """
    summary = _CASE_STORE.get(case_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    spoken_text = f"Priority level: {summary.priority_level.value}. Chief complaint: {summary.chief_complaint}."

    try:
        adapter = RealBhashiniAdapter()
    except BhashiniAdapterError as exc:
        logger.error("Bhashini adapter unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Bhashini backend is not configured.") from exc

    try:
        if language != "en":
            spoken_text = adapter.translate(spoken_text, source_language="en", target_language=language)
        audio_bytes = adapter.synthesize(spoken_text, target_language=language)
    except BhashiniAdapterError as exc:
        logger.error("Bhashini speech synthesis failed: %s", exc)
        raise HTTPException(status_code=503, detail="Bhashini speech synthesis failed.") from exc

    return Response(content=audio_bytes, media_type="audio/wav")


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
