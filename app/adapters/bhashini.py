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
import logging
import os
from typing import Protocol

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
        the response body doesn't have the expected shape.
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
        data = response.json()

        try:
            task_config = next(
                task for task in data["pipelineResponseConfig"] if task["taskType"] == task_type
            )
            service_id = task_config["config"][0]["serviceId"]
            auth = data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]
            return service_id, auth["name"], auth["value"]
        except (KeyError, IndexError, StopIteration) as exc:
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
        try:
            service_id, auth_name, auth_value = self._get_pipeline_config("asr", source_language)

            audio_content = base64.b64encode(audio_bytes).decode("ascii")
            body = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {"sourceLanguage": source_language},
                            "serviceId": service_id,
                            "audioFormat": "flac",
                            "samplingRate": 16000,
                        },
                    }
                ],
                "inputData": {"audio": [{"audioContent": audio_content}]},
            }
            data = self._post_inference(body, auth_name, auth_value)
            return data["pipelineResponse"][0]["output"][0]["source"]
        except httpx.HTTPStatusError as exc:
            raise BhashiniAdapterError(f"Bhashini ASR request failed: {exc}") from exc
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise BhashiniAdapterError(f"Bhashini ASR request failed after retries: {exc}") from exc
        except (KeyError, IndexError) as exc:
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
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise BhashiniAdapterError(f"Bhashini translation request failed after retries: {exc}") from exc
        except (KeyError, IndexError) as exc:
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
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise BhashiniAdapterError(f"Bhashini TTS request failed after retries: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise BhashiniAdapterError(f"Unexpected TTS inference response shape: {exc}") from exc
        except (ValueError, TypeError) as exc:
            # base64.b64decode raises binascii.Error (a ValueError
            # subclass) on malformed/non-base64 content - guarded here
            # for the same reason the response-shape KeyError/IndexError
            # case above is: an unexpected real response should surface
            # as a clear BhashiniAdapterError, not an unrelated raw
            # exception type leaking out of this adapter.
            raise BhashiniAdapterError(f"Unexpected TTS audio encoding: {exc}") from exc


def bhashini_to_intake(adapter: BhashiniAdapter, audio_bytes: bytes) -> str:
    """
    Pure orchestration, no I/O of its own: transcribe Telugu audio, then
    translate the transcript to English. Returns English text - the
    caller is responsible for handing it to app/agents/intake.py's
    existing symptom_text pipeline (PatientInput.symptom_text already
    documents "English or Telugu", so this function is what makes the
    Telugu half of that promise real). Takes the adapter as a parameter
    rather than constructing one internally, same reason
    run_triage_reasoning(case, backend) does in app/agents/triage.py -
    it makes this function testable with a fake, no network or
    credentials required.
    """
    telugu_text = adapter.transcribe(audio_bytes, source_language="te")
    return adapter.translate(telugu_text, source_language="te", target_language="en")
