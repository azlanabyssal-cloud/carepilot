import pytest

from app.adapters.bhashini import (
    BhashiniAdapterError,
    RealBhashiniAdapter,
    bhashini_to_intake,
)


class FakeBhashiniAdapter:
    """Test double implementing the BhashiniAdapter protocol - no network call."""

    def __init__(self, transcript: str, translation: str) -> None:
        self._transcript = transcript
        self._translation = translation
        self.transcribe_calls: list[tuple[bytes, str]] = []
        self.translate_calls: list[tuple[str, str, str]] = []

    def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
        self.transcribe_calls.append((audio_bytes, source_language))
        return self._transcript

    def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
        self.translate_calls.append((text, source_language, target_language))
        return self._translation


def test_bhashini_to_intake_chains_transcribe_then_translate():
    fake = FakeBhashiniAdapter(
        transcript="నాకు జ్వరం గా ఉంది",
        translation="I have a fever",
    )
    audio_bytes = b"fake-flac-bytes"

    result = bhashini_to_intake(fake, audio_bytes)

    assert result == "I have a fever"
    # Proven, not just claimed: transcribe ran on the raw audio, and
    # translate ran on transcribe's output - not on the raw audio again.
    assert fake.transcribe_calls == [(audio_bytes, "te")]
    assert fake.translate_calls == [(fake._transcript, "te", "en")]


def test_bhashini_to_intake_returns_english_text_type():
    fake = FakeBhashiniAdapter(transcript="కడుపు నొప్పి", translation="stomach pain")
    result = bhashini_to_intake(fake, b"more-fake-audio")
    assert isinstance(result, str)
    assert result == "stomach pain"


def test_real_adapter_requires_user_id(monkeypatch):
    monkeypatch.delenv("BHASHINI_USER_ID", raising=False)
    monkeypatch.setenv("BHASHINI_API_KEY", "test-key-not-used-no-network-call")
    with pytest.raises(BhashiniAdapterError):
        RealBhashiniAdapter(user_id=None, api_key=None)


def test_real_adapter_requires_api_key(monkeypatch):
    monkeypatch.setenv("BHASHINI_USER_ID", "test-user-not-used-no-network-call")
    monkeypatch.delenv("BHASHINI_API_KEY", raising=False)
    with pytest.raises(BhashiniAdapterError):
        RealBhashiniAdapter(user_id=None, api_key=None)


def test_real_adapter_requires_both_credentials_missing(monkeypatch):
    monkeypatch.delenv("BHASHINI_USER_ID", raising=False)
    monkeypatch.delenv("BHASHINI_API_KEY", raising=False)
    with pytest.raises(BhashiniAdapterError) as exc_info:
        RealBhashiniAdapter(user_id=None, api_key=None)
    # Clear about *why* it failed, not just that it failed - same bar as
    # TriageBackendError's message in app/agents/triage.py.
    assert "BHASHINI_USER_ID" in str(exc_info.value)
    assert "BHASHINI_API_KEY" in str(exc_info.value)


def test_real_adapter_constructs_with_explicit_credentials():
    # No network call happens at construction time - only at transcribe()/
    # translate() call time, same lazy pattern as AnthropicReasoningBackend.
    adapter = RealBhashiniAdapter(user_id="explicit-user", api_key="explicit-key")
    assert adapter is not None


def test_real_adapter_accepts_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("BHASHINI_USER_ID", "env-user-not-used-no-network-call")
    monkeypatch.setenv("BHASHINI_API_KEY", "env-key-not-used-no-network-call")
    adapter = RealBhashiniAdapter()
    assert adapter is not None
