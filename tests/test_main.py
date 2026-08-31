"""
End-to-end tests for the actual FastAPI app - not the individual agent
functions (those have their own test files), the wiring: does a real
HTTP request through app.main actually produce the right response and
status code. This file didn't exist before Day 4 - every endpoint check
across the first three days was manual curl, never regression-tested.
That's a real gap, closed here, not just noted.
"""

import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

import app.main as main_module
from app.adapters.bhashini import BhashiniAdapterError
from app.main import app

client = TestClient(app)


def _render_text_image(text: str) -> bytes:
    """Same real-rendered-text helper as tests/test_ocr.py - no fixture files, no license question."""
    image = Image.new("L", (500, 120), color=255)
    draw = ImageDraw.Draw(image)
    draw.text((10, 40), text, fill=0, font=ImageFont.load_default())
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _clear_credentials(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("BHASHINI_USER_ID", raising=False)
    monkeypatch.delenv("BHASHINI_API_KEY", raising=False)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_intake_normalizes_and_flags():
    response = client.post("/intake", json={"symptom_text": "  mild headache  ", "duration_days": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["symptom_text"] == "mild headache"
    assert body["red_flag_terms"] == []


def test_intake_rejects_too_short_symptom_text():
    # PatientInput.symptom_text has min_length=3 - this is FastAPI/Pydantic
    # validation, not app logic, but it's still a real contract the API
    # promises and nothing here had ever actually exercised it before.
    response = client.post("/intake", json={"symptom_text": "ok"})
    assert response.status_code == 422


def test_assess_red_flag_case_short_circuits_without_any_api_key(monkeypatch):
    _clear_credentials(monkeypatch)
    response = client.post(
        "/assess",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "emergency"
    assert body["facility"] is None


def test_assess_ordinary_case_fails_gracefully_without_api_key(monkeypatch):
    _clear_credentials(monkeypatch)
    response = client.post(
        "/assess",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_assess_voice_fails_gracefully_without_bhashini_credentials(monkeypatch):
    _clear_credentials(monkeypatch)
    response = client.post(
        "/assess/voice",
        files={"audio": ("symptom.flac", b"fake-audio-bytes", "audio/flac")},
        data={"age": "30"},
    )
    assert response.status_code == 503
    assert "Bhashini" in response.json()["detail"]


def test_assess_voice_wires_transcription_into_the_full_pipeline(monkeypatch):
    """
    Proves the actual new logic in /assess/voice: that a successful
    Bhashini transcription really does flow into run_intake and the rest
    of the pipeline, not just that the endpoint exists. Uses a fake
    adapter substituted onto app.main.RealBhashiniAdapter - same
    dependency-substitution approach as the rest of this codebase's unit
    tests, applied here at the one seam that's constructed inline inside
    the endpoint rather than passed in.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "raw telugu transcript"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            assert text == "raw telugu transcript"  # proves transcribe's output feeds translate
            return "chest pain and unconscious"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeAdapter)

    response = client.post(
        "/assess/voice",
        files={"audio": ("symptom.flac", b"fake-audio-bytes", "audio/flac")},
        data={"age": "50"},
    )

    assert response.status_code == 200
    body = response.json()
    # The fake's translated text contains real red-flag terms - this
    # proves the transcribed/translated text actually reached
    # run_intake's red-flag scan, not just that the endpoint returned 200.
    assert body["level"] == "emergency"


def test_assess_voice_fails_gracefully_when_transcription_itself_fails(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FailingTranscribeAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            raise BhashiniAdapterError("simulated Bhashini ASR failure")

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            raise AssertionError("translate should never run if transcribe failed")

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FailingTranscribeAdapter)

    response = client.post(
        "/assess/voice",
        files={"audio": ("symptom.flac", b"fake-audio-bytes", "audio/flac")},
    )

    assert response.status_code == 503
    assert "Bhashini" in response.json()["detail"]


def test_assess_voice_returns_422_not_500_on_empty_translation(monkeypatch):
    """
    Regression test for a real bug: a Bhashini translation that comes back
    empty (silence, a garbled clip, or a genuinely blank recording) used to
    reach PatientInput(symptom_text="", ...) unguarded. PatientInput has
    min_length=3 (app/schemas.py) and pydantic.ValidationError is not one of
    FastAPI's automatically-handled exception types when raised manually
    inside a route body, so this previously surfaced as a raw, unhandled 500
    Internal Server Error instead of a clean, documented client error -
    caught here by actually driving the endpoint, not by reading the code
    and assuming the min_length constraint would be enforced automatically.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class EmptyTranslationAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "silence"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            return ""

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", EmptyTranslationAdapter)

    response = client.post(
        "/assess/voice",
        files={"audio": ("blank.flac", b"fake-audio-bytes", "audio/flac")},
    )

    assert response.status_code == 422
    assert "too short or empty" in response.json()["detail"]


def test_assess_voice_returns_422_not_500_on_too_short_translation(monkeypatch):
    """Same bug, boundary case: 2 characters is one under PatientInput's min_length=3."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class TooShortTranslationAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "hm"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            return "hm"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", TooShortTranslationAdapter)

    response = client.post(
        "/assess/voice",
        files={"audio": ("short.flac", b"fake-audio-bytes", "audio/flac")},
    )

    assert response.status_code == 422


def test_assess_and_assess_voice_agree_on_equivalent_input(monkeypatch):
    """
    Proves the design claim in app/main.py's assess_voice docstring - "the
    same ReferralResult /assess produces" - by actually asserting equality
    between the two endpoints' responses, instead of trusting the comment
    that says so.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    text_response = client.post(
        "/assess", json={"symptom_text": "severe bleeding", "age": 40, "duration_days": 0}
    )

    class FakeAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "raw telugu transcript"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            return "severe bleeding"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeAdapter)
    voice_response = client.post(
        "/assess/voice",
        files={"audio": ("a.flac", b"x", "audio/flac")},
        data={"age": "40", "duration_days": "0"},
    )

    assert text_response.status_code == voice_response.status_code == 200
    assert text_response.json() == voice_response.json()


def test_case_intake_rejects_malformed_input_before_any_agent_runs():
    """
    Malformed input (symptom_text under PatientInput's own min_length=3)
    must be rejected at the request-body boundary with a clear 422 -
    never reach run_history_intake and fail there in some less legible
    way. Same contract test_intake_rejects_too_short_symptom_text
    already proves for /intake, applied to the new endpoint.
    """
    response = client.post("/case-intake", json={"symptom_text": "ok"})
    assert response.status_code == 422


def test_case_intake_red_flag_case_never_calls_the_drafting_backend(monkeypatch):
    """
    The actual safety property this design exists to guarantee: an
    emergency case gets its priority_level from the already-tested
    red-flag short-circuit and its narrative from the patient's own
    words directly - the AI history-drafting backend is never even
    constructed. Proven by making backend construction itself raise,
    then confirming the endpoint still succeeds - if this test passes,
    the code path genuinely never touched the backend.
    """
    _clear_credentials(monkeypatch)

    class ExplodingBackend:
        def __init__(self, *args, **kwargs):
            raise AssertionError("History-drafting backend was constructed on a red-flag case.")

    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", ExplodingBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["priority_level"] == "emergency"
    assert body["chief_complaint"] == "severe bleeding and unconscious"
    assert body["is_reviewed_by_physician"] is False


def test_case_intake_ordinary_case_fails_gracefully_without_api_key(monkeypatch):
    """
    Same 503-not-500 contract as test_assess_ordinary_case_fails_gracefully_without_api_key,
    for the new endpoint's own two possible failure points (triage
    backend, then history-drafting backend).
    """
    _clear_credentials(monkeypatch)
    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_case_intake_ordinary_case_fails_gracefully_when_history_backend_unavailable(monkeypatch):
    """
    Distinct from test_case_intake_ordinary_case_fails_gracefully_without_api_key:
    that test fails at the triage step (missing ANTHROPIC_API_KEY stops
    AnthropicReasoningBackend from constructing). This test forces triage
    to SUCCEED, then makes AnthropicHistoryDraftingBackend's own
    construction fail - proving _run_case_intake's second try/except
    branch (the one around AnthropicHistoryDraftingBackend()) actually
    returns 503, not just that the code reads as if it would.
    """
    from app.agents.history_intake import HistoryDraftingError
    from app.schemas import TriageDecision, TriageLevel

    class FakeTriageBackend:
        def propose(self, case):
            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class FailingHistoryBackend:
        def __init__(self, *args, **kwargs):
            raise HistoryDraftingError("simulated: history-drafting backend unavailable")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", FailingHistoryBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_case_intake_ordinary_case_fails_gracefully_when_drafting_itself_fails(monkeypatch):
    """
    A third distinct branch: the drafting backend constructs fine but
    .draft() itself raises (e.g. the Anthropic API call failed after
    retries) - _run_case_intake's second except clause, not its first.
    """
    from app.agents.history_intake import HistoryDraftingError
    from app.schemas import TriageDecision, TriageLevel

    class FakeTriageBackend:
        def propose(self, case):
            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class DraftingFailsBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            raise HistoryDraftingError("simulated: Anthropic API call failed after retries")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", DraftingFailsBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "failed after retries" in response.json()["detail"]


def test_case_intake_voice_fails_gracefully_without_bhashini_credentials(monkeypatch):
    _clear_credentials(monkeypatch)
    response = client.post(
        "/case-intake/voice",
        files={"audio": ("symptom.flac", b"fake-audio-bytes", "audio/flac")},
        data={"age": "30"},
    )
    assert response.status_code == 503
    assert "Bhashini" in response.json()["detail"]


def test_case_intake_voice_red_flag_wires_transcription_into_full_pipeline(monkeypatch):
    """
    Same proof as test_assess_voice_wires_transcription_into_the_full_pipeline,
    for the new endpoint: a successful Bhashini transcription really does
    flow through run_intake into _run_case_intake, and the emergency
    short-circuit still works end to end on voice input, not just typed text.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "raw telugu transcript"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            assert text == "raw telugu transcript"
            return "severe bleeding and unconscious"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeAdapter)

    response = client.post(
        "/case-intake/voice",
        files={"audio": ("symptom.flac", b"fake-audio-bytes", "audio/flac")},
        data={"age": "50"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["priority_level"] == "emergency"
    assert body["chief_complaint"] == "severe bleeding and unconscious"


def test_case_intake_voice_returns_422_on_empty_translation(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class EmptyTranslationAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "silence"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            return ""

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", EmptyTranslationAdapter)

    response = client.post(
        "/case-intake/voice",
        files={"audio": ("blank.flac", b"fake-audio-bytes", "audio/flac")},
    )

    assert response.status_code == 422


def test_case_intake_and_case_intake_voice_agree_on_equivalent_input(monkeypatch):
    """Same design proof as test_assess_and_assess_voice_agree_on_equivalent_input,
    for the /case-intake pair - the two entry points must produce identical
    output for equivalent content, not two different code paths that could drift."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    text_response = client.post(
        "/case-intake", json={"symptom_text": "severe bleeding", "age": 40, "duration_days": 0}
    )

    class FakeAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
            return "raw telugu transcript"

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            return "severe bleeding"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeAdapter)
    voice_response = client.post(
        "/case-intake/voice",
        files={"audio": ("a.flac", b"x", "audio/flac")},
        data={"age": "40", "duration_days": "0"},
    )

    assert text_response.status_code == voice_response.status_code == 200
    assert text_response.json() == voice_response.json()


def test_case_intake_document_rejects_an_undecodable_file(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeTriageBackend:
        def propose(self, case):
            from app.schemas import TriageDecision, TriageLevel

            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())

    response = client.post(
        "/case-intake/document",
        data={"symptom_text": "mild cough for two days"},
        files={"document": ("not-an-image.txt", b"this is definitely not image data", "text/plain")},
    )

    assert response.status_code == 422
    assert "Could not read" in response.json()["detail"]


def test_case_intake_document_extracts_medications_and_dates_from_a_real_image(monkeypatch):
    """
    Proves the actual new logic end-to-end with a REAL rendered image (not
    a mock of extract_text) - a synthetic prescription-like image goes
    through the real Tesseract OCR call, real regex extraction, and the
    result lands in prior_investigations_summary.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeTriageBackend:
        def propose(self, case):
            from app.schemas import TriageDecision, TriageLevel

            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class FakeHistoryBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            from app.agents.history_intake import HistoryDraft

            return HistoryDraft(chief_complaint="mild fever", history_of_present_illness="two days")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", FakeHistoryBackend)

    image_bytes = _render_text_image("PARACETAMOL 500MG BD")

    response = client.post(
        "/case-intake/document",
        data={"symptom_text": "mild fever for two days"},
        files={"document": ("prescription.png", image_bytes, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prior_investigations_summary"] is not None
    assert "PARACETAMOL" in body["prior_investigations_summary"]


def test_case_intake_ordinary_case_drafts_a_real_structured_history(monkeypatch):
    """
    Proves the actual new logic end-to-end with a fake drafting backend:
    a non-red-flag case reaches run_history_intake, and the resulting
    ClinicalHistorySummary carries both the drafted narrative and the
    priority_level that came from triage - not from the draft.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeTriageBackend:
        def propose(self, case):
            from app.schemas import TriageDecision, TriageLevel

            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="persistent mild symptom", confidence=0.7)

    class FakeHistoryBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            from app.agents.history_intake import HistoryDraft

            return HistoryDraft(
                chief_complaint="persistent cough",
                history_of_present_illness="two days, no fever, worse at night",
                past_medical_surgical_history="none reported",
            )

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", FakeHistoryBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "persistent cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chief_complaint"] == "persistent cough"
    assert body["history_of_present_illness"] == "two days, no fever, worse at night"
    assert body["past_medical_surgical_history"] == "none reported"
    assert body["priority_level"] == "clinic_visit"
    assert body["is_reviewed_by_physician"] is False


def test_case_intake_returns_503_not_500_when_drafted_chief_complaint_is_too_short(monkeypatch):
    """
    Regression test for a real Day 7 bug: a drafting backend that
    returns a non-empty but too-short chief_complaint (e.g. "ok") isn't
    caught by history_intake.py's `fields.get(...) or case.symptom_text`
    fallback - that only rescues an empty/missing field, not a short
    one. The resulting HistoryDraft then fails
    ClinicalHistorySummary's own min_length=3 constraint inside
    run_history_intake(), and since that model is constructed manually
    rather than via a FastAPI request-body parameter, the resulting
    pydantic.ValidationError previously propagated as a raw, unhandled
    500 - the same failure class as Day 6's /assess/voice bug, this
    time triggered by the AI backend's own output rather than user
    input. Reproduced directly with TestClient(app,
    raise_server_exceptions=True) before this test was written, per
    this project's standing rule: prove it by running it, not by
    reading the code and assuming it's fine.
    """
    from app.agents.history_intake import HistoryDraft
    from app.schemas import TriageDecision, TriageLevel

    class FakeTriageBackend:
        def propose(self, case):
            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class ShortChiefComplaintBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            return HistoryDraft(chief_complaint="ok", history_of_present_illness="fine for now")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", ShortChiefComplaintBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "unusable draft" in response.json()["detail"]
