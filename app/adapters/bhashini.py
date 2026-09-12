"""
Bhashini vernacular (Telugu) adapter layer.

Lets a patient speak Telugu into the intake flow: audio bytes go in,
English text comes out, ready to hand to app/agents/intake.py's existing
symptom_text pipeline. This module does not import or modify intake.py
or app/schemas.py - it is a standalone adapter, wired in by the caller.

Also runs the reverse direction: synthesize() turns text back into
speech (English/Hindi/Telugu). Added later than transcribe()/translate()
specifically to close the "Audio input and Output" ask
(docs/sih/SIH26047_Patient_Case_Taking_Software.md) - input already
worked end-to-end via app/main.py's /case-intake/voice; output had no
code at all until synthesize() and app/main.py's audio-summary endpoint
existed.

Same shape as app/agents/triage.py on purpose: a Protocol so callers can
be unit-tested against a fake backend with no network call, a concrete
real implementation that fails fast with a clear custom error when
credentials are missing, and retry/backoff on the transient-failure
path only. See tests/test_bhashini.py.

VERIFICATION STATUS - read this before trusting anything below:
This environment has no real BHASHINI_USER_ID / BHASHINI_API_KEY, and no
live network call to meity-auth.ulcacontrib.org or dhruva-api.bhashini.gov.in
was made or could be made while building this. The two-step
pipeline-config -> inference request/response shape implemented here is
transcribed from the community-maintained bhashini-api Python wrapper
(github.com/AdityaKukreti/bhashini-api), which itself calls the real
MeitY/Dhruva endpoints - it is the best available ground truth without
credentials, but it is still second-hand. What IS verified: the
orchestration logic (bhashini_to_intake chaining transcribe -> translate),
the credential-missing fail-fast path, and the request bodies matching
the documented shape - all covered by tests/test_bhashini.py using a
fake adapter, zero network calls. What is NOT verified: that Bhashini's
real servers actually respond in the shape assumed here today, that the
pipelineId below is still valid, or that field names haven't changed
since the wrapper was last updated. Do not present this as "tested
against the real API" - it hasn't been, and can't be, in this
environment.

AUDIO FORMAT ADDENDUM (12 Sep 2026), a real, CONFIRMED bug, not an
unverified-against-Bhashini caveat like the rest of this docstring:
web/app.js's in-browser recorder produces WebM/Opus (browsers cannot
reliably record WAV/FLAC directly via MediaRecorder), but transcribe()
used to send those bytes to Bhashini labeled `"audioFormat": "flac"`
unconditionally - and Bhashini's own published API docs and community
integration guides state WebM is not supported and must be converted to
WAV first. This is confirmed by inspection and by Bhashini's own
documented format support, independent of the "no live credentials"
caveat above: every real voice submission through the actual UI was
sending mismatched, undecodable audio, regardless of the speaker or how
they spoke. Fixed by transcoding to 16kHz mono WAV with ffmpeg
(_transcode_to_wav()) before every transcribe() call, and sending the
real, matching audioFormat. What remains unverified is unchanged from
the rest of this docstring: whether Bhashini's real servers accept
*this* WAV encoding's exact parameters (sample width, endianness) has
never been confirmed against a live endpoint, only against ffmpeg's own
standard WAV output and Bhashini's publicly documented format list.

PROXY-ERROR ADDENDUM (12 Sep 2026), a real bug found by actually
attempting a live network call in this environment (not a mocked
test): this environment's own outbound egress proxy rejects
meity-auth.ulcacontrib.org with a 403, which httpx surfaces as
httpx.ProxyError - a real httpx.TransportError subclass, but NOT one of
the two subclasses (httpx.ConnectError, httpx.ReadTimeout)
transcribe()/translate()/synthesize() used to catch and convert to
BhashiniAdapterError. It propagated raw, producing an actual 500
Internal Server Error from a live curl against this repo's own running
server - proof, not a hypothetical, since httpx.ProxyError is exactly
the shape any real deployment behind a corporate/institutional network
proxy (a realistic setup for a hospital IT environment, not just this
dev sandbox) would also hit. Fixed by widening all three methods'
transport-error except clause from the two specific subclasses to the
shared httpx.TransportError parent class, so any network-layer failure
- not just the two this module happened to anticipate - converts to a
clean BhashiniAdapterError/503 instead of a raw crash. The retry
decorators' own narrower (httpx.ConnectError, httpx.ReadTimeout) set is
deliberately unchanged: a 403 from an explicit proxy policy is not a
transient condition retrying would fix, unlike a dropped connection or
a slow response.

TTS ADDENDUM, same honesty standard as above, not a lower one just
because it was added later: synthesize() adds a third taskType ("tts")
to the exact same two-step pipeline-config -> inference mechanism
already described above - that mechanism is equally (un)verified for tts
as it already was for asr/translation, nothing new or riskier about the
plumbing itself. What IS newly, specifically unconfirmed: the TTS
response shape used below (data["pipelineResponse"][0]["audio"][0]
["audioContent"], base64-decoded) is this project's own best-effort
extrapolation from Bhashini's generally published TTS sample shape - it
mirrors the "audio list with a base64 audioContent field" pattern shown
in public Bhashini samples, NOT a line-for-line transcription from the
same community bhashini-api wrapper cited above for asr/translation,
because that wrapper's own TTS code path was not the thing consulted
while writing this. If the real response nests this differently, or
uses a different field name, synthesize()'s parsing line breaks, not the
two-step mechanism around it - see synthesize()'s own docstring for
specifics. app/main.py's audio-summary endpoint now runs the English
summary template through translate() before requesting hi/te synthesis,
closing what was originally a named gap here (this endpoint used to
speak the English template in a hi/te voice, not translated text) - what
remains unverified is narrower than before: the tts pipeline call
itself, and whether the two un-networked calls (translate then
synthesize) compose correctly against Bhashini's real servers.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
from typing import Protocol

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

PIPELINE_CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
INFERENCE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

# The pipelineId used across every public Bhashini sample/wrapper found
# without live credentials to confirm against - MeitY's standard published
# ASR+Translation+TTS pipeline. Unverified in this environment; see the
# module docstring's Verification Status section. Overridable via the
# constructor for exactly that reason.
DEFAULT_PIPELINE_ID = "64392f96daac500b55c543cd"


class BhashiniAdapter(Protocol):
    """Anything that can turn Telugu speech/text into English text, and
    text back into speech.

    A Protocol, not a concrete base class, so bhashini_to_intake() - and,
    for synthesize(), app/main.py's audio-summary endpoint - can be
    unit-tested against a fake adapter - no network call, no credentials
    required. See tests/test_bhashini.py and tests/test_main.py.
    """

    def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str: ...

    def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str: ...

    def synthesize(self, text: str, target_language: str = "en") -> bytes: ...


class BhashiniAdapterError(RuntimeError):
    """Raised when the Bhashini adapter fails, including after retries are exhausted."""


_TARGET_SAMPLE_RATE = 16000  # matches the samplingRate transcribe() already declares to Bhashini below


def _transcode_to_wav(audio_bytes: bytes) -> bytes:
    """
    Real bug, found 12 Sep 2026 by checking what format a browser
    actually records rather than trusting the docstring/type-hint
    ("Telugu speech audio (flac/wav)" - app/main.py's /assess/voice and
    /case-intake/voice) to describe reality: web/app.js's MediaRecorder
    is constructed with no mimeType override
    (`new MediaRecorder(stream)`), so it records in whatever format the
    browser defaults to - WebM/Opus in every Chromium-based browser,
    confirmed by inspecting web/app.js's own onRecordingStopped()/
    extensionForMime(), which explicitly branch on "webm"/"ogg"/"mp4" as
    real, expected outputs. transcribe() below used to base64-encode
    those raw bytes and tell Bhashini's API `"audioFormat": "flac"`
    regardless - a real, confirmed mismatch (cited: Bhashini's own docs
    and community integration guides state WebM is not supported and
    must be converted to WAV first), not a hypothetical edge case. Every
    voice submission through the actual browser UI would send Bhashini
    audio bytes mislabeled as a format they are not, independent of how
    fast or slowly the patient spoke.

    Fixed by transcoding whatever format arrives into 16kHz mono WAV
    with ffmpeg before it ever reaches Bhashini, and sending the real,
    matching `"audioFormat": "wav"` (see transcribe() below) - not by
    trying to get the browser to record WAV/FLAC directly, which
    MediaRecorder cannot reliably do cross-browser (WAV/FLAC are not
    supported MediaRecorder output containers in Chrome/Firefox as of
    this writing; only WebM/Ogg/MP4 containers are). ffmpeg was chosen
    over a pure-Python decoder because correctly decoding arbitrary
    browser-supplied codecs (Opus-in-WebM, AAC-in-MP4) is exactly the
    kind of format-specific complexity a real, battle-tested system tool
    handles correctly and a bespoke decoder would not - the same
    "right-sized, not reinvented" judgment app/db.py's own docstring
    already applies to choosing sqlite3 over an ORM. 16kHz mono is not
    an arbitrary choice: it is the exact samplingRate transcribe()
    already declares to Bhashini, so this normalizes every input to
    match what the request body claims, regardless of what sample rate
    or channel count the source recording actually used.
    """
    if shutil.which("ffmpeg") is None:
        raise BhashiniAdapterError(
            "ffmpeg is not installed in this environment - required to transcode "
            "browser-recorded audio (typically WebM/Opus, not FLAC/WAV) into a "
            "format Bhashini's real ASR API actually accepts."
        )
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-ar", str(_TARGET_SAMPLE_RATE), "-ac", "1", "-f", "wav", "pipe:1"],
            input=audio_bytes,
            capture_output=True,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr_tail = exc.stderr.decode("utf-8", errors="replace")[-500:] if exc.stderr else ""
        raise BhashiniAdapterError(
            f"Could not decode uploaded audio (ffmpeg exit {exc.returncode}): {stderr_tail}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise BhashiniAdapterError("Audio transcoding timed out after 30s.") from exc
    return result.stdout


class RealBhashiniAdapter:
    """Real adapter: calls the two-step MeitY/Dhruva Bhashini pipeline.

    See the module docstring's Verification Status section - this has
    never been exercised against Bhashini's real servers in this
    environment. The request/response shape is transcribed from the
    community bhashini-api wrapper, not confirmed first-hand.
    """

    def __init__(
        self,
        user_id: str | None = None,
        api_key: str | None = None,
        pipeline_id: str = DEFAULT_PIPELINE_ID,
        timeout: float = 30.0,
    ) -> None:
        resolved_user_id = user_id or os.environ.get("BHASHINI_USER_ID")
        resolved_api_key = api_key or os.environ.get("BHASHINI_API_KEY")
        if not resolved_user_id or not resolved_api_key:
            raise BhashiniAdapterError(
                "BHASHINI_USER_ID and/or BHASHINI_API_KEY is not set. Export both in the "
                "environment or pass user_id/api_key explicitly - never hardcode credentials "
                "in source or commit them."
            )
        self._user_id = resolved_user_id
        self._api_key = resolved_api_key
        self._pipeline_id = pipeline_id
        self._timeout = timeout

    # -- Step 1: pipeline config -------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _get_pipeline_config(
        self, task_type: str, source_language: str, target_language: str | None = None
    ) -> tuple[str, str, str]:
        """
        Resolve which serviceId to call for this task, and obtain a
        per-session inference auth key. Returns (service_id, auth_header_name,
        auth_header_value). Raises httpx.HTTPStatusError on a bad HTTP
        response (not retried - see transcribe/translate, which wrap it
        into BhashiniAdapterError) and BhashiniAdapterError directly if
        the response body isn't valid JSON at all, or doesn't have the
        expected shape once parsed.
        """
        language_config: dict = {"sourceLanguage": source_language}
        if target_language:
            language_config["targetLanguage"] = target_language

        body = {
            "pipelineTasks": [{"taskType": task_type, "config": {"language": language_config}}],
            "pipelineRequestConfig": {"pipelineId": self._pipeline_id},
        }
        headers = {"userID": self._user_id, "ulcaApiKey": self._api_key}

        response = httpx.post(PIPELINE_CONFIG_URL, json=body, headers=headers, timeout=self._timeout)
        response.raise_for_status()

        try:
            data = response.json()
            task_config = next(
                task for task in data["pipelineResponseConfig"] if task["taskType"] == task_type
            )
            service_id = task_config["config"][0]["serviceId"]
            auth = data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]
            return service_id, auth["name"], auth["value"]
        except (KeyError, IndexError, StopIteration, json.JSONDecodeError) as exc:
            raise BhashiniAdapterError(
                f"Unexpected pipeline-config response shape for taskType={task_type!r}: {exc}"
            ) from exc

    # -- Step 2: inference ---------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _post_inference(self, body: dict, auth_name: str, auth_value: str) -> dict:
        headers = {auth_name: auth_value}
        response = httpx.post(INFERENCE_URL, json=body, headers=headers, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
        # _transcode_to_wav() runs first, outside the try/except below, on
        # purpose: it raises BhashiniAdapterError directly (see its own
        # docstring for the real format-mismatch bug this fixes) and
        # needs no further conversion - it isn't an httpx exception, so
        # letting it propagate past the except clauses below unchanged
        # is correct, not an oversight.
        wav_bytes = _transcode_to_wav(audio_bytes)
        try:
            service_id, auth_name, auth_value = self._get_pipeline_config("asr", source_language)

            audio_content = base64.b64encode(wav_bytes).decode("ascii")
            body = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {"sourceLanguage": source_language},
                            "serviceId": service_id,
                            "audioFormat": "wav",
                            "samplingRate": _TARGET_SAMPLE_RATE,
                        },
                    }
                ],
                "inputData": {"audio": [{"audioContent": audio_content}]},
            }
            data = self._post_inference(body, auth_name, auth_value)
            return data["pipelineResponse"][0]["output"][0]["source"]
        except httpx.HTTPStatusError as exc:
            raise BhashiniAdapterError(f"Bhashini ASR request failed: {exc}") from exc
        except httpx.TransportError as exc:
            raise BhashiniAdapterError(f"Bhashini ASR request failed after retries: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise BhashiniAdapterError(f"Unexpected ASR inference response shape: {exc}") from exc

    def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
        try:
            service_id, auth_name, auth_value = self._get_pipeline_config(
                "translation", source_language, target_language
            )

            body = {
                "pipelineTasks": [
                    {
                        "taskType": "translation",
                        "config": {
                            "language": {
                                "sourceLanguage": source_language,
                                "targetLanguage": target_language,
                            },
                            "serviceId": service_id,
                        },
                    }
                ],
                "inputData": {"input": [{"source": text}]},
            }
            data = self._post_inference(body, auth_name, auth_value)
            return data["pipelineResponse"][0]["output"][0]["target"]
        except httpx.HTTPStatusError as exc:
            raise BhashiniAdapterError(f"Bhashini translation request failed: {exc}") from exc
        except httpx.TransportError as exc:
            raise BhashiniAdapterError(f"Bhashini translation request failed after retries: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise BhashiniAdapterError(f"Unexpected translation inference response shape: {exc}") from exc

    def synthesize(self, text: str, target_language: str = "en") -> bytes:
        """
        Text -> speech: the "Output" half of "Audio input and Output"
        that had no code at all until this method existed. Mirrors
        transcribe()/translate() exactly on purpose - same two-step
        pipeline-config -> inference call, same retry/error handling
        (inherited from _get_pipeline_config/_post_inference, no new
        retry logic here), same BhashiniAdapterError on failure. No
        second error type invented for the same adapter - same reasoning
        docs/INTERVIEW_NOTES.md's Bhashini entry already gives for
        reusing this file's shape instead of designing something fresh.

        See the module docstring's TTS ADDENDUM before trusting the
        parsing line below: the two-step mechanism is exercised the same
        way transcribe/translate already are, but the specific response
        shape here (["audio"][0]["audioContent"]) is this project's own
        extrapolation from Bhashini's published TTS sample shape, not a
        transcription from the same community wrapper cited for
        transcribe/translate - the least-verified line in this file,
        stated as such rather than passed off as equally solid.

        gender is hardcoded to "female" and audioFormat to "wav" (the
        latter matching the media_type app/main.py's audio-summary
        endpoint declares to callers) - real Bhashini TTS services
        generally require picking both, and no caller-facing need to
        choose either has come up yet. Both are as unverified against
        live behavior as the rest of this method; overridable later the
        same way DEFAULT_PIPELINE_ID already is, if a real credential
        ever shows either assumption is wrong.
        """
        try:
            # TTS, like ASR, only ever needs one language (the language
            # to speak the text in) - passed into the source_language
            # slot, same convention transcribe() already uses above,
            # since _get_pipeline_config's signature is shaped for the
            # two-language translation case but tts/asr only need one.
            service_id, auth_name, auth_value = self._get_pipeline_config("tts", target_language)

            body = {
                "pipelineTasks": [
                    {
                        "taskType": "tts",
                        "config": {
                            "language": {"sourceLanguage": target_language},
                            "serviceId": service_id,
                            "gender": "female",
                            "audioFormat": "wav",
                        },
                    }
                ],
                "inputData": {"input": [{"source": text}]},
            }
            data = self._post_inference(body, auth_name, auth_value)
            audio_content = data["pipelineResponse"][0]["audio"][0]["audioContent"]
            return base64.b64decode(audio_content)
        except httpx.HTTPStatusError as exc:
            raise BhashiniAdapterError(f"Bhashini TTS request failed: {exc}") from exc
        except httpx.TransportError as exc:
            raise BhashiniAdapterError(f"Bhashini TTS request failed after retries: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise BhashiniAdapterError(f"Unexpected TTS inference response shape: {exc}") from exc
        except (ValueError, TypeError) as exc:
            # base64.b64decode raises binascii.Error (a ValueError
            # subclass) on malformed/non-base64 content - guarded here
            # for the same reason the response-shape KeyError/IndexError
            # case above is: an unexpected real response should surface
            # as a clear BhashiniAdapterError, not an unrelated raw
            # exception type leaking out of this adapter.
            raise BhashiniAdapterError(f"Unexpected TTS audio encoding: {exc}") from exc


def bhashini_to_intake(adapter: BhashiniAdapter, audio_bytes: bytes, source_language: str = "te") -> str:
    """
    Pure orchestration, no I/O of its own: transcribe audio in
    source_language, then translate the transcript to English. Returns
    English text - the caller is responsible for handing it to
    app/agents/intake.py's existing symptom_text pipeline. Takes the
    adapter as a parameter rather than constructing one internally, same
    reason run_triage_reasoning(case, backend) does in
    app/agents/triage.py - it makes this function testable with a fake,
    no network or credentials required.

    Real, serious bug fixed 12 Sep 2026: source_language used to be
    hardcoded to "te" right here, with no parameter to override it at
    all, and every call site (app/main.py's /assess/voice and
    /case-intake/voice) passed no language through from the request -
    both endpoints' own docstrings admitted this plainly ("Telugu voice
    in"). The UI (web/index.html, web/i18n.js) has been trilingual
    (English/Hindi/Telugu) since early in this project; the voice
    pipeline silently was not - an English or Hindi speaker's recording
    was sent to Bhashini declared as Telugu regardless of what they
    actually said, which for a real ASR service means near-total
    transcription failure, not just degraded accuracy. Not a hypothetical:
    found by reading this function's own hardcoded "te" against the
    Literal["te", "hi", "en"] language parameter just added to both
    voice endpoints, not by observing a live failure (no live Bhashini
    credentials exist here to fail against) - but the code path itself,
    read plainly, could not have produced a correct result for a
    non-Telugu speaker before this fix, independent of Bhashini's real
    server behavior.

    source_language == target_language == "en" skips the translate()
    call entirely rather than asking Bhashini to "translate" English to
    English - a real no-op some translation APIs handle fine and others
    reject outright as an invalid same-language pair; skipping it is
    correct either way and saves a real network round trip.
    """
    transcript = adapter.transcribe(audio_bytes, source_language=source_language)
    if source_language == "en":
        return transcript
    return adapter.translate(transcript, source_language=source_language, target_language="en")
