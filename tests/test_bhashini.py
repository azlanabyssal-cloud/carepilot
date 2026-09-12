import base64
import io
import subprocess
import wave

import httpx
import pytest

from app.adapters.bhashini import (
    BhashiniAdapterError,
    RealBhashiniAdapter,
    _transcode_to_wav,
    bhashini_to_intake,
)


def _tiny_wav_bytes() -> bytes:
    """
    A genuinely valid, minimal WAV clip (0.1s of silence at 16kHz mono) -
    real audio bytes ffmpeg can actually decode, needed since
    transcribe() now runs every input through _transcode_to_wav() before
    reaching the HTTP layer these tests exercise. Deliberately not a
    placeholder like b"fake-audio" - that string isn't decodable audio
    at all, and would now fail at the transcoding step before ever
    reaching the httpx.post mock these tests are actually testing.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)
    return buf.getvalue()


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


def test_bhashini_to_intake_respects_source_language_parameter():
    """
    Real, serious bug fixed 12 Sep 2026: source_language used to be
    hardcoded to "te" inside this function, with no parameter to
    override it - every voice submission was declared Telugu to
    Bhashini regardless of what the patient actually spoke or which
    language app/main.py's endpoints were told about. Proves the
    parameter is now actually threaded through to transcribe(), not
    just accepted and ignored.
    """
    fake = FakeBhashiniAdapter(transcript="मुझे बुखार है", translation="I have a fever")
    audio_bytes = b"fake-hindi-audio"

    result = bhashini_to_intake(fake, audio_bytes, source_language="hi")

    assert result == "I have a fever"
    assert fake.transcribe_calls == [(audio_bytes, "hi")]
    assert fake.translate_calls == [(fake._transcript, "hi", "en")]


def test_bhashini_to_intake_skips_translate_for_english_source():
    """
    source_language="en" must skip translate() entirely rather than
    asking Bhashini to "translate" English to English - a same-language
    pair some translation APIs handle as a no-op and others reject
    outright. Proven by asserting translate_calls stayed empty, not just
    that the returned text happens to look right.
    """
    fake = FakeBhashiniAdapter(transcript="I have a fever", translation="SHOULD NOT BE USED")
    audio_bytes = b"fake-english-audio"

    result = bhashini_to_intake(fake, audio_bytes, source_language="en")

    assert result == "I have a fever"
    assert fake.transcribe_calls == [(audio_bytes, "en")]
    assert fake.translate_calls == []


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
        adapter.transcribe(_tiny_wav_bytes())


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
        adapter.transcribe(_tiny_wav_bytes())


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


# -- Audio format transcoding (12 Sep 2026 - see _transcode_to_wav's own docstring) --


def _real_webm_opus_bytes() -> bytes:
    """
    Generates a REAL WebM/Opus file with ffmpeg itself - the same
    container/codec web/app.js's browser-side MediaRecorder actually
    produces (confirmed by that file's own onRecordingStopped()/
    extensionForMime(), which explicitly handle "webm" as a real,
    expected case) - not a synthetic stand-in. Proves _transcode_to_wav
    against the actual failure mode this fix addresses, not just against
    already-WAV input.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:a", "libopus", "-f", "webm", "pipe:1",
        ],
        capture_output=True,
        timeout=10,
        check=True,
    )
    return result.stdout


def test_transcode_to_wav_converts_real_webm_opus_audio():
    webm_bytes = _real_webm_opus_bytes()

    wav_bytes = _transcode_to_wav(webm_bytes)

    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        assert wav_file.getframerate() == 16000
        assert wav_file.getnchannels() == 1


def test_transcode_to_wav_is_a_real_conversion_not_a_passthrough():
    # The whole point of the fix: input bytes and output bytes must
    # differ (different container/codec entirely), not just be copied
    # through unchanged with a relabeled format string.
    webm_bytes = _real_webm_opus_bytes()

    wav_bytes = _transcode_to_wav(webm_bytes)

    assert wav_bytes != webm_bytes
    assert webm_bytes[:4] != b"RIFF"  # confirms the input really was WebM, not WAV to begin with


def test_transcode_to_wav_raises_bhashini_adapter_error_on_undecodable_input():
    with pytest.raises(BhashiniAdapterError, match="Could not decode uploaded audio"):
        _transcode_to_wav(b"this is not audio at all, just plain text bytes")


def test_transcribe_sends_the_real_transcoded_wav_bytes_with_matching_audio_format(monkeypatch):
    """
    Real regression test for the actual bug: transcribe() used to
    base64-encode the RAW, untranscoded input and unconditionally claim
    "audioFormat": "flac" - a confirmed mismatch against what browsers
    actually record (see _transcode_to_wav's own docstring). Proves the
    request body Bhashini actually receives now carries real, transcoded
    WAV bytes with a matching "wav" audioFormat, by inspecting the exact
    JSON body _post_inference is called with - not by inference from a
    successful round trip alone.
    """
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")
    webm_bytes = _real_webm_opus_bytes()
    expected_wav_bytes = _transcode_to_wav(webm_bytes)
    captured_bodies = []

    def fake_post(url, json=None, headers=None, timeout=None):
        captured_bodies.append(json)
        if url == "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline":
            return _pipeline_config_response("asr")
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"pipelineResponse": [{"output": [{"source": "transcribed text"}]}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = adapter.transcribe(webm_bytes, source_language="te")

    assert result == "transcribed text"
    inference_body = captured_bodies[1]
    asr_config = inference_body["pipelineTasks"][0]["config"]
    assert asr_config["audioFormat"] == "wav"
    assert asr_config["samplingRate"] == 16000
    sent_audio_content = inference_body["inputData"]["audio"][0]["audioContent"]
    assert base64.b64decode(sent_audio_content) == expected_wav_bytes
    # And explicitly NOT the raw, untranscoded WebM bytes - the exact
    # mismatch this fix closes.
    assert base64.b64decode(sent_audio_content) != webm_bytes


# -- httpx.ProxyError conversion (12 Sep 2026 - see the module docstring's own addendum) --


def test_transcribe_converts_proxy_error_to_bhashini_adapter_error(monkeypatch):
    """
    Real bug, found by attempting a live network call against this
    environment's own outbound proxy (not a mocked test): a corporate/
    institutional network proxy rejecting the real Bhashini endpoint
    raises httpx.ProxyError, a real httpx.TransportError subclass that
    is NOT httpx.ConnectError or httpx.ReadTimeout - the only two
    transcribe() used to catch and convert. It propagated raw as an
    actual, reproduced 500 Internal Server Error from a live curl
    against this repo's own running uvicorn server before this fix.
    """
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")

    def fake_post(*args, **kwargs):
        raise httpx.ProxyError("403 Forbidden")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Bhashini ASR request failed after retries"):
        adapter.transcribe(_tiny_wav_bytes())


def test_translate_converts_proxy_error_to_bhashini_adapter_error(monkeypatch):
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")

    def fake_post(*args, **kwargs):
        raise httpx.ProxyError("403 Forbidden")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Bhashini translation request failed after retries"):
        adapter.translate("some text")


def test_synthesize_converts_proxy_error_to_bhashini_adapter_error(monkeypatch):
    adapter = RealBhashiniAdapter(user_id="u", api_key="k")

    def fake_post(*args, **kwargs):
        raise httpx.ProxyError("403 Forbidden")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(BhashiniAdapterError, match="Bhashini TTS request failed after retries"):
        adapter.synthesize("some text")
