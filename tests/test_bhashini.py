import httpx
import pytest

from app.adapters.bhashini import (
    BhashiniAdapterError,
    RealBhashiniAdapter,
    bhashini_to_intake,
)


def _pipeline_config_response(task_type: str) -> httpx.Response:
    body = {
        "pipelineResponseConfig": [{"taskType": task_type, "config": [{"serviceId": "svc-1"}]}],
        "pipelineInferenceAPIEndPoint": {"inferenceApiKey": {"name": "auth-name", "value": "auth-value"}},
    }
    return httpx.Response(200, request=httpx.Request("POST", "https://x"), json=body)


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


# -- Day 13: non-JSON response bodies, the same failure class Day 12 -----------
# fixed for GroqReasoningBackend._call (tests/test_groq_backends.py), audited
# here for the first time against this file's own four response.json() call
# sites (named as unchecked in docs/DAILY_LOG.md's Day 12 entry).


def test_transcribe_converts_non_json_pipeline_config_response_to_bhashini_adapter_error(monkeypatch):
    """
    Real bug: RealBhashiniAdapter._get_pipeline_config called
    response.json() with no guard at all around it - response.raise_for_status()
    only rejects a non-2xx status code, so a 200 response whose body isn't
    valid JSON (a misconfigured proxy/gateway returning an HTML error page,
    the exact real-world failure mode Day 12 already fixed for
    GroqReasoningBackend._call) made response.json() raise
    json.JSONDecodeError - a ValueError, not one of the KeyError/IndexError/
    StopIteration types the surrounding except clauses caught - so it
    propagated raw out of transcribe()/translate()/synthesize() instead of
    becoming a clean BhashiniAdapterError. Reproduced first by mocking
    httpx.post directly (not _get_pipeline_config) so the real code path is
    what's actually exercised, confirmed broken before the fix existed.
    """
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"<html>not json</html>")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Unexpected pipeline-config response shape"):
        adapter.transcribe(b"fake-audio")


def test_transcribe_converts_non_json_inference_response_to_bhashini_adapter_error(monkeypatch):
    """
    Same failure mode, one step later: the pipeline-config call succeeds
    and returns valid JSON, but the second-step inference call
    (_post_inference) itself returns a 200 with a non-JSON body.
    _post_inference is a thin helper with no try/except of its own (by
    design - the same as its httpx.HTTPStatusError/ConnectError/ReadTimeout
    failures, which are also converted by the caller, not inside
    _post_inference) so it's transcribe()'s own except clause that has to
    catch this - it didn't, before today's fix.
    """
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")
    responses = [
        _pipeline_config_response("asr"),
        httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"not json at all"),
    ]

    def fake_post(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Unexpected ASR inference response shape"):
        adapter.transcribe(b"fake-audio")


def test_translate_converts_non_json_pipeline_config_response_to_bhashini_adapter_error(monkeypatch):
    """Same proof as transcribe's pipeline-config test, one method over -
    translate() has its own separate except clause that needed the same
    widening, copy-paste is not proof it was actually applied everywhere."""
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"not json")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Unexpected pipeline-config response shape"):
        adapter.translate("some text")


def test_synthesize_converts_non_json_inference_response_to_bhashini_adapter_error(monkeypatch):
    """Same proof as transcribe's inference-step test, for synthesize()'s
    own separate except clause - the TTS path, added later than
    transcribe/translate and never audited against this failure class
    until today."""
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")
    responses = [
        _pipeline_config_response("tts"),
        httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"<not-json/>"),
    ]

    def fake_post(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Unexpected TTS inference response shape"):
        adapter.synthesize("some text")
