"""
End-to-end tests for the actual FastAPI app - not the individual agent
functions (those have their own test files), the wiring: does a real
HTTP request through app.main actually produce the right response and
status code. This file didn't exist before Day 4 - every endpoint check
across the first three days was manual curl, never regression-tested.
That's a real gap, closed here, not just noted.
"""

import os

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.adapters.bhashini import BhashiniAdapterError
from app.main import app

client = TestClient(app)


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
