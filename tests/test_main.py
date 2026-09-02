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
import uuid

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


def test_assess_ordinary_case_returns_503_not_500_when_backend_rationale_is_invisible_only(monkeypatch):
    """
    Real bug, same failure class as the Day 6 /assess/voice bug and the
    Day 8/9 ClinicalHistorySummary fixes: TriageDecision.rationale had no
    validation at all until today, so a model response whose RATIONALE
    line is invisible-Unicode-only survives AnthropicReasoningBackend._parse()'s
    `.strip()` unchanged - non-empty per str.strip(), so `TriageDecision(...)`
    used to construct successfully with a rationale that renders as
    completely blank. Exercises the REAL AnthropicReasoningBackend.propose()
    -> _parse() path end to end through the live endpoint, not a hand-rolled
    fake backend, by monkeypatching only the network call (_call) - proving
    the fix's ValidationError-to-TriageBackendError conversion actually runs
    here, not just in isolation (see tests/test_triage.py for the
    isolated version of this same regression).
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used-no-network-call")
    monkeypatch.setattr(
        main_module.AnthropicReasoningBackend,
        "_call",
        lambda self, case: "LEVEL: urgent\nRATIONALE: ​​​",
    )

    response = client.post(
        "/assess",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "failed after retries" in response.json()["detail"]


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
    text_body = text_response.json()
    voice_body = voice_response.json()
    # case_id is expected to differ, not a bug to hide: app/db.py's
    # CaseStore.save() persists each POST as its own, independent case
    # record with a freshly generated id, even when the clinical content
    # is identical - popped from both before the equality check below so
    # this test keeps proving its actual claim (identical CONTENT from
    # both entry points), while also positively confirming persistence
    # really did happen twice, independently, rather than just ignoring
    # the field.
    assert text_body.pop("case_id") != voice_body.pop("case_id")
    assert text_body == voice_body


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


def test_case_intake_returns_503_not_500_when_drafted_chief_complaint_is_invisible_only(monkeypatch):
    """
    Regression test for a second real bug, same root cause as the "ok"
    case above but not caught by it: "ok" is short but *visible* - it
    fails min_length=3 outright. A drafting backend that returns three
    U+200B ZERO WIDTH SPACE characters instead ("​​​") is a different
    shape - it satisfies min_length=3 as a raw character count and isn't
    empty/falsy, so history_intake.py's `or case.symptom_text` fallback
    doesn't fire either. Before app/schemas.py's ClinicalHistorySummary
    gained its own _reject_invisible_chief_complaint validator (same fix
    class as PatientInput's own zero-width-space regression, see
    tests/test_schemas.py), this would have constructed successfully - a
    summary a physician opens and sees as completely blank, persisted as
    if it were real content, not caught by any test until this one.
    """
    from app.agents.history_intake import HistoryDraft
    from app.schemas import TriageDecision, TriageLevel

    class FakeTriageBackend:
        def propose(self, case):
            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class InvisibleChiefComplaintBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            return HistoryDraft(chief_complaint="​​​", history_of_present_illness="fine for now")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", InvisibleChiefComplaintBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "unusable draft" in response.json()["detail"]


def test_case_intake_returns_503_not_500_when_drafted_hpi_is_too_short(monkeypatch):
    """
    Sibling regression test to the chief_complaint "ok" case above, for the
    field a Day-9 audit found unguarded: history_of_present_illness had no
    min_length constraint at all before this fix, so a drafting backend
    returning a two-character HPI like "ok" would have constructed and
    persisted a ClinicalHistorySummary successfully. Reproduced directly
    with TestClient(app, raise_server_exceptions=True) before this test was
    written, same standing rule as every other bug in this file.
    """
    from app.agents.history_intake import HistoryDraft
    from app.schemas import TriageDecision, TriageLevel

    class FakeTriageBackend:
        def propose(self, case):
            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class ShortHpiBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            return HistoryDraft(chief_complaint="mild cough", history_of_present_illness="ok")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", ShortHpiBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "unusable draft" in response.json()["detail"]


def test_case_intake_returns_503_not_500_when_drafted_hpi_is_invisible_only(monkeypatch):
    """
    Regression test for the real bug this session found: the exact same
    failure class as
    test_case_intake_returns_503_not_500_when_drafted_chief_complaint_is_invisible_only
    above, on the sibling field history_of_present_illness -
    history_intake.py's _parse() uses the identical
    `fields.get("HPI") or case.symptom_text` fallback, so a drafting
    backend returning three U+200B ZERO WIDTH SPACE characters for HPI is
    just as truthy as the chief_complaint case, and the fallback doesn't
    fire. Before app/schemas.py's ClinicalHistorySummary.history_of_present_illness
    gained a min_length=3 Field constraint and its own
    _reject_invisible_history_of_present_illness validator, this field had
    *no* validation at all - not even a length floor - so this would have
    constructed and persisted successfully, a summary a physician opens
    and sees as blank in its narrative-of-illness field specifically, not
    caught by any test until this one.
    """
    from app.agents.history_intake import HistoryDraft
    from app.schemas import TriageDecision, TriageLevel

    class FakeTriageBackend:
        def propose(self, case):
            return TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="mild", confidence=0.6)

    class InvisibleHpiBackend:
        def __init__(self, *args, **kwargs):
            pass

        def draft(self, case):
            return HistoryDraft(chief_complaint="mild cough", history_of_present_illness="​​​")

    monkeypatch.setattr(main_module, "AnthropicReasoningBackend", lambda *a, **k: FakeTriageBackend())
    monkeypatch.setattr(main_module, "AnthropicHistoryDraftingBackend", InvisibleHpiBackend)

    response = client.post(
        "/case-intake",
        json={"symptom_text": "mild cough for two days", "age": 25, "duration_days": 2},
    )

    assert response.status_code == 503
    assert "unusable draft" in response.json()["detail"]


# -- Case persistence (app/db.py's CaseStore, wired into /case-intake* and GET /cases*) --
#
# These tests hit the real _CASE_STORE app/main.py builds at import time -
# the real data/cases.db on disk, not a temp file - deliberately, unlike
# tests/test_db.py's isolated CaseStore unit tests: the actual thing worth
# proving here is that the live app singleton really persists a case and
# really reads it back, which a swapped-in fake store couldn't prove.
# Assertions below check membership/round-trip of the one case each test
# just created, never exact list length or full-table equality, since
# other saved cases legitimately coexist in that same real file across
# a whole test run (and across whatever else has run the app before).


def test_case_intake_response_carries_a_real_case_id(monkeypatch):
    """
    The actual point of building a real case database at all: a
    /case-intake response must carry a real, freshly-generated case_id,
    not None - otherwise a physician still has no way to pull this case
    back up later, same gap this whole feature exists to close. Uses the
    red-flag short-circuit so this needs zero API keys, same trick every
    credential-free test in this file already uses.
    """
    _clear_credentials(monkeypatch)
    response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    assert response.status_code == 200
    case_id = response.json()["case_id"]
    assert case_id is not None
    # Round-trips through uuid.UUID's own parser in the exact canonical
    # hex form uuid.uuid4().hex produces - proves it's a genuine uuid4,
    # not just "some non-null string."
    assert uuid.UUID(hex=case_id).hex == case_id


def test_get_case_round_trips_a_saved_case(monkeypatch):
    """Proves GET /cases/{case_id} actually reads back what /case-intake
    just persisted - not just that both endpoints exist independently."""
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    get_response = client.get(f"/cases/{case_id}")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["case_id"] == case_id
    assert body["chief_complaint"] == "severe bleeding and unconscious"
    assert body["priority_level"] == "emergency"


def test_get_unknown_case_returns_a_clean_404():
    """A case_id that was never saved must be a clean, documented 404 -
    not a 500, not an empty 200, not a silently-wrong result."""
    response = client.get(f"/cases/{uuid.uuid4().hex}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Case not found."


def test_list_cases_includes_what_was_just_saved(monkeypatch):
    """
    GET /cases must reflect real persisted state, not an empty stub -
    proven by saving a case and confirming its case_id shows up in the
    listing (membership, not exact length: see this section's own note
    above on why exact-count assertions would be the wrong test here).
    """
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    list_response = client.get("/cases")

    assert list_response.status_code == 200
    listed_ids = [case["case_id"] for case in list_response.json()]
    assert case_id in listed_ids


# -- Audio summary (app/adapters/bhashini.py's new synthesize(), via GET /cases/{case_id}/audio-summary) --


def test_case_audio_summary_returns_404_for_unknown_case():
    """Same 404 contract as GET /cases/{case_id} - a case that doesn't
    exist has no audio to synthesize, and that's reported the same way,
    not a different failure convention for this one endpoint."""
    response = client.get(f"/cases/{uuid.uuid4().hex}/audio-summary")
    assert response.status_code == 404
    assert response.json()["detail"] == "Case not found."


def test_case_audio_summary_returns_503_when_bhashini_not_configured(monkeypatch):
    """Same construction-failure branch /case-intake/voice already has -
    missing BHASHINI_USER_ID/BHASHINI_API_KEY must fail as a clean 503,
    not a raw crash, applied consistently to the new endpoint too."""
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    response = client.get(f"/cases/{case_id}/audio-summary")

    assert response.status_code == 503
    assert "Bhashini" in response.json()["detail"]


def test_case_audio_summary_returns_503_when_synthesis_itself_fails(monkeypatch):
    """Distinct from the construction-failure test above: the adapter
    constructs fine, but .synthesize() itself raises (e.g. the live
    Bhashini TTS call failed) - the second of the two 503 branches this
    endpoint's docstring promises, same as every other backend call in
    this file already tests both branches separately."""
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    class FailingTtsAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def synthesize(self, text: str, target_language: str = "en") -> bytes:
            raise BhashiniAdapterError("simulated Bhashini TTS failure")

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FailingTtsAdapter)

    response = client.get(f"/cases/{case_id}/audio-summary")

    assert response.status_code == 503
    assert "Bhashini" in response.json()["detail"]


def test_case_audio_summary_returns_the_adapters_audio_bytes_with_wav_media_type(monkeypatch):
    """
    Proves /cases/{case_id}/audio-summary actually calls synthesize() and
    returns exactly its bytes with the right media type - not just that
    the endpoint exists and returns 200. The fake also asserts on the
    text it was handed, confirming the spoken-summary template really
    does carry this case's own priority_level and chief_complaint, not a
    hardcoded placeholder string.
    """
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    class FakeTtsAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def synthesize(self, text: str, target_language: str = "en") -> bytes:
            assert "emergency" in text
            assert "severe bleeding and unconscious" in text
            assert target_language == "en"
            return b"FAKE-WAV-AUDIO-BYTES"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeTtsAdapter)

    response = client.get(f"/cases/{case_id}/audio-summary")

    assert response.status_code == 200
    assert response.content == b"FAKE-WAV-AUDIO-BYTES"
    assert response.headers["content-type"] == "audio/wav"


def test_case_audio_summary_passes_the_requested_language_through(monkeypatch):
    """language is a real parameter that reaches the adapter, not silently
    ignored - proven by asserting the fake received exactly what was
    requested in the query string."""
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    class FakeTtsAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            assert source_language == "en"
            assert target_language == "te"
            return "TELUGU TRANSLATION"

        def synthesize(self, text: str, target_language: str = "en") -> bytes:
            assert target_language == "te"
            return b"FAKE-TELUGU-AUDIO"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", FakeTtsAdapter)

    response = client.get(f"/cases/{case_id}/audio-summary", params={"language": "te"})

    assert response.status_code == 200
    assert response.content == b"FAKE-TELUGU-AUDIO"


def test_case_audio_summary_translates_before_synthesizing_for_non_english(monkeypatch):
    """
    Regression test for a real, named gap this endpoint used to have:
    a hi/te request used to hand the English summary template straight
    to synthesize(), asking Bhashini to speak English text in a
    different voice rather than actually translated speech. Proven here
    by asserting synthesize() receives the translate() call's OUTPUT, not
    the original English template - if the endpoint regressed to the old
    behavior, this fake's synthesize() would see "Priority level:
    emergency..." instead and fail the assertion below.
    """
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    class TranslatingTtsAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
            assert "emergency" in text  # the untranslated English template reached translate()
            return "hi-TRANSLATED-SUMMARY"

        def synthesize(self, text: str, target_language: str = "en") -> bytes:
            assert text == "hi-TRANSLATED-SUMMARY"  # synthesize() got translate()'s output, not the English template
            return b"FAKE-HINDI-AUDIO"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", TranslatingTtsAdapter)

    response = client.get(f"/cases/{case_id}/audio-summary", params={"language": "hi"})

    assert response.status_code == 200
    assert response.content == b"FAKE-HINDI-AUDIO"


def test_case_audio_summary_does_not_translate_for_english(monkeypatch):
    """The other half of the same contract: language="en" (the default)
    must NOT call translate() at all - synthesize() gets the English
    template directly, since there's nothing to translate it to."""
    _clear_credentials(monkeypatch)
    create_response = client.post(
        "/case-intake",
        json={"symptom_text": "severe bleeding and unconscious", "age": 40, "duration_days": 0},
    )
    case_id = create_response.json()["case_id"]

    class NoTranslateAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def translate(self, *args, **kwargs):
            raise AssertionError("translate() should never be called for language='en'")

        def synthesize(self, text: str, target_language: str = "en") -> bytes:
            assert "emergency" in text
            return b"FAKE-ENGLISH-AUDIO"

    monkeypatch.setattr(main_module, "RealBhashiniAdapter", NoTranslateAdapter)

    response = client.get(f"/cases/{case_id}/audio-summary")

    assert response.status_code == 200
    assert response.content == b"FAKE-ENGLISH-AUDIO"


def test_case_audio_summary_rejects_an_unsupported_language():
    """FastAPI's own Literal["en", "hi", "te"] validation must reject a
    bad language value with a clean 422 at the request boundary - same
    "validate at the boundary" discipline docs/INTERVIEW_NOTES.md's
    Entry 2 already established, proven here rather than just claimed in
    the endpoint's own docstring."""
    response = client.get(f"/cases/{uuid.uuid4().hex}/audio-summary", params={"language": "fr"})
    assert response.status_code == 422
