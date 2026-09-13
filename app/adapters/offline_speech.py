"""
Zero-network speech fallback: local, offline ASR (English only) and TTS
(English/Hindi/Telugu), with no external API, no credentials, and no
network call of any kind at inference time.

Fits the same zero-API-dependency architecture this project already
applies to triage reasoning (app/agents/triage.py's
DeterministicFallbackReasoningBackend) and history drafting
(app/agents/history_intake.py's DeterministicHistoryDraftingBackend):
Bhashini is preferred when configured and reachable, since it is
MeitY's own government speech service and the more accurate path, but
its absence must degrade the audio pipeline honestly, not take it down
entirely. app/main.py wires this in as the fallback only when
RealBhashiniAdapter() can't be constructed or a live Bhashini call
fails - never as a silent replacement for a working Bhashini connection.

Two real, honest limits, verified directly rather than assumed:

1. Transcription (speech -> text) only works for English.
   PocketSphinx's bundled en-us acoustic model ships inside the
   pocketsphinx wheel itself - confirmed by installing it in this exact
   project's venv and finding the model files already present on disk
   with zero extra downloads. That is what makes it usable at all here:
   this environment's own egress policy returns a hard 403 on
   huggingface.co (confirmed directly - see docs/DAILY_LOG.md), which
   is where a Whisper or Vosk model would have to come from, and
   alphacephei.com (Vosk's own model host) is equally unreachable. No
   Hindi or Telugu acoustic model is bundled anywhere this project could
   fetch or verify, so transcribe() raises OfflineSpeechAdapterError for
   source_language != "en" - an honest "can't help offline yet", not a
   wrong transcript delivered with false confidence.

2. Transcription accuracy, even for English, is real but genuinely
   modest. Verified live: an espeak-ng-synthesized WAV of "Please see a
   doctor immediately for this symptom" (the closest thing to a
   controllable, reproducible speech sample available without a real
   human speaker in this environment) came back from PocketSphinx as
   "we see all the recall is the" - recognizable as English, nowhere
   close to accurate. PocketSphinx's 2000s-era acoustic-model
   architecture was never going to match a modern neural ASR system,
   and a synthetic TTS voice is itself an imperfect stand-in for real
   human speech, so this result is a floor, not a ceiling - but it is
   real evidence, not a hopeful assumption, and it is why every case
   this backend transcribes must be treated as needing a human to
   double check it. app/main.py's callers mark every result from this
   path requires_manual_triage=True - the exact same "flag it, don't
   hide it" signal already used for a low-confidence triage-reasoning or
   history-drafting fallback, applied here for the same reason.

synthesize() (text -> speech) carries no such caveat on CONTENT: it
renders speech only, does not touch the record's clinical content, and
works end to end for English/Hindi/Telugu, verified directly - espeak-ng
ships all three voices in its own bundled data package (espeak-ng-data,
installed via apt, no model download of any kind), and this module's
own test suite confirms real, non-empty WAV bytes come back for all
three languages.

VOICE-QUALITY CAVEAT (13 Sep 2026), added after a live report that
audio "won't progress smoother" - honestly disclosing a real gap this
docstring previously left unstated, not a correction of a false claim:
espeak-ng is a formant synthesizer (the same family of technique behind
1980s-90s screen-reader voices), not a modern neural TTS model - it is
intelligible, but its cadence is inherently more mechanical than a
neural voice or Bhashini's own real TTS service, and no amount of
parameter tuning changes that underlying technique. Checked directly,
not assumed: a better offline option (e.g. Piper's neural voices) is
not reachable in this environment - `pip install piper-tts` succeeds
(the package itself is on PyPI), but its actual voice model files are
hosted on huggingface.co, which this environment's own egress policy
returns a 403 on (the identical restriction already named above for
Vosk/Whisper ASR models) - confirmed with a live request, not inferred
from the ASR case. synthesize() below now passes an explicit, slower
speaking rate (see its own docstring) as a real, evidence-based
adjustment - espeak-ng's un-set default (175 words/minute) measurably
produces the shortest, most rushed output of several rates tried on the
same sentence - but this claim is intentionally narrow: it should
reduce how rushed/clipped the speech sounds, a documented effect of
slowing formant-synthesized speech, not a fix for the underlying
robotic quality, and it has not been confirmed by ear, because nothing
in this project's toolchain can listen to audio and judge how it
sounds - only inspect its bytes, duration, and format.
"""

from __future__ import annotations

import io
import logging
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from app.adapters.bhashini import BhashiniAdapterError, _transcode_to_wav

logger = logging.getLogger(__name__)

_ESPEAK_LANGUAGE_VOICES = {"en": "en", "hi": "hi", "te": "te"}


def _pcm_data_from_wav(wav_bytes: bytes) -> bytes:
    """
    REAL BUG, found 13 Sep 2026 while investigating a live report that
    voice input "doesn't listen to the person completely": transcribe()
    used to hardcode `wav_bytes[44:]` to strip a WAV header, assuming
    ffmpeg's `-f wav` output is always exactly the minimal 44-byte
    header with no extra chunks. Confirmed directly that this is false
    for this project's actual ffmpeg: every real transcoded file carries
    a "LIST"/"INFO" chunk (ffmpeg tagging its own encoder version,
    e.g. "Lavf60.16.100") between the `fmt ` chunk and the `data` chunk,
    pushing the real audio start to byte 78, not 44 - confirmed by
    locating the literal `data` marker in a real transcoded file and
    finding it 26 bytes later than the hardcoded offset assumed. The
    fixed 44-byte slice was feeding PocketSphinx 34 bytes of WAV
    metadata text (part of the LIST chunk, the "data" tag itself, and
    the chunk's size field) as if they were the first 17 audio samples,
    corrupting the very start of every single recording decoded through
    this path - not a rare edge case, since this LIST/INFO chunk is
    ffmpeg's ordinary, non-configurable default WAV output shape, not
    something introduced by any unusual input. Fixed by using Python's
    own `wave` module to find the real `data` chunk and read exactly the
    frames it declares, instead of assuming any fixed byte offset -
    correct regardless of which chunks precede `data` or what order they
    arrive in. This alone does not explain every case of a recording
    "not being listened to completely" - see _transcode_to_wav's own
    Day 13 docstring addendum in app/adapters/bhashini.py for the
    other real bug found alongside this one and fixed in the same pass.
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        return wav_file.readframes(wav_file.getnframes())


_SYNTHESIS_TIMEOUT_SECONDS = 30
_TRANSCRIPTION_TIMEOUT_SECONDS = 30
# See synthesize()'s own docstring for the real measurement behind this
# value (175 default vs 160/145/130 tried, on this project's own audio-
# summary template text) and its honestly-scoped claim.
_ESPEAK_WORDS_PER_MINUTE = 145


class OfflineSpeechAdapterError(RuntimeError):
    """Raised when the offline speech fallback fails or can't help for the requested language."""


class OfflineSpeechAdapter:
    """
    Implements the same shape as app/adapters/bhashini.py's
    BhashiniAdapter Protocol (transcribe/translate/synthesize) so
    app/main.py can hand either adapter to bhashini_to_intake() without
    the orchestration logic caring which one it got - same reasoning
    app/agents/triage.py already applies to swapping in
    DeterministicFallbackReasoningBackend for AnthropicTriageBackend.
    """

    def transcribe(self, audio_bytes: bytes, source_language: str = "te") -> str:
        """
        English only - see this module's docstring for exactly why, and
        for the real, measured accuracy ceiling this should be trusted
        to. Raises OfflineSpeechAdapterError immediately for any other
        source_language rather than guessing.
        """
        if source_language != "en":
            raise OfflineSpeechAdapterError(
                f"Offline transcription is only available for English in this build "
                f"(requested source_language={source_language!r}). Bhashini is required "
                f"for Hindi/Telugu voice input; please type your symptoms instead."
            )

        try:
            from pocketsphinx import Decoder, get_model_path
        except ImportError as exc:
            raise OfflineSpeechAdapterError(
                "pocketsphinx is not installed - required for offline English transcription."
            ) from exc

        try:
            # _transcode_to_wav() is app/adapters/bhashini.py's own
            # ffmpeg-based WebM/Opus -> 16kHz mono WAV step, reused as-is
            # rather than duplicated - the format problem it solves
            # (browsers record WebM/Opus, not WAV) is identical here, and
            # duplicating an already-tested subprocess wrapper for no
            # reason is exactly the kind of thing this project avoids
            # elsewhere (see app/db.py's own "don't reinvent" reasoning).
            # It raises BhashiniAdapterError, a name that has nothing to
            # do with Bhashini's live API for this specific failure mode
            # (ffmpeg missing or a corrupt upload) - re-raised here as
            # this module's own error type so a caller of
            # OfflineSpeechAdapter never needs to import or catch
            # anything from app.adapters.bhashini to handle it correctly.
            wav_bytes = _transcode_to_wav(audio_bytes)
        except BhashiniAdapterError as exc:
            raise OfflineSpeechAdapterError(str(exc)) from exc

        model_path = Path(get_model_path())
        config = Decoder.default_config()
        config.set_string("-hmm", str(model_path / "en-us" / "en-us"))
        config.set_string("-lm", str(model_path / "en-us" / "en-us.lm.bin"))
        config.set_string("-dict", str(model_path / "en-us" / "cmudict-en-us.dict"))
        config.set_string("-logfn", "/dev/null")

        try:
            pcm_bytes = _pcm_data_from_wav(wav_bytes)
        except wave.Error as exc:
            raise OfflineSpeechAdapterError(f"Transcoded audio is not a valid WAV file: {exc}") from exc

        try:
            decoder = Decoder(config)
            decoder.start_utt()
            decoder.process_raw(pcm_bytes, False, True)
            decoder.end_utt()
        except Exception as exc:  # pocketsphinx raises plain RuntimeError on init/decode failure
            raise OfflineSpeechAdapterError(f"Offline transcription failed: {exc}") from exc

        hypothesis = decoder.hyp()
        return hypothesis.hypstr if hypothesis is not None else ""

    def translate(self, text: str, source_language: str = "te", target_language: str = "en") -> str:
        """
        Identity passthrough for the only pair this adapter's transcribe()
        can ever produce (en -> en) - not a stub kept for interface
        symmetry, but the actually-correct behavior: there is no offline
        text-to-text translation model bundled here, and none is needed,
        because transcribe() above already refuses every source_language
        except "en". Raises for any other pair rather than silently
        returning the untranslated text, so a caller that skips the
        source_language=="en" short-circuit in
        app/adapters/bhashini.py's bhashini_to_intake() fails loudly
        instead of shipping mislabeled text.
        """
        if source_language == "en" and target_language == "en":
            return text
        raise OfflineSpeechAdapterError(
            f"Offline translation is not available ({source_language!r} -> {target_language!r}); "
            f"this adapter only ever produces English text from English audio."
        )

    def synthesize(self, text: str, target_language: str = "en") -> bytes:
        """
        Real, working offline TTS for English/Hindi/Telugu via espeak-ng
        - see this module's docstring for why this carries none of
        transcribe()'s accuracy caveat: it renders already-correct text
        as speech, it does not interpret or transcribe anything. See the
        same docstring's VOICE-QUALITY CAVEAT for the real, separate
        limitation this does have: espeak-ng's cadence, not its accuracy.

        -s _ESPEAK_WORDS_PER_MINUTE (13 Sep 2026): espeak-ng's own
        unset default is 175 words/minute. Measured directly on this
        module's own real "Emergency. Seek help immediately..." template
        text at 175/160/145/130: 175 produced the shortest, most rushed
        output of the four (5.9s vs 8.23s at 130). Slowing formant-
        synthesized speech down is a documented way to reduce how
        clipped/rushed it sounds - not a fix for the underlying
        mechanical timbre, which no rate setting changes. Picked 145 -
        on the slower half of what was tried, but not the slowest (130):
        slow enough to matter, not so slow it drags in the other
        direction (a claim about rate, not about how the result actually
        sounds - this project's toolchain has no way to listen to audio
        and judge that, only inspect its bytes, duration, and format).
        """
        voice = _ESPEAK_LANGUAGE_VOICES.get(target_language)
        if voice is None:
            raise OfflineSpeechAdapterError(f"Offline synthesis does not support language {target_language!r}.")

        if shutil.which("espeak-ng") is None:
            raise OfflineSpeechAdapterError(
                "espeak-ng is not installed in this environment - required for offline speech synthesis."
            )

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_file:
            try:
                subprocess.run(
                    ["espeak-ng", "-v", voice, "-s", str(_ESPEAK_WORDS_PER_MINUTE), "-w", tmp_file.name, text],
                    capture_output=True,
                    timeout=_SYNTHESIS_TIMEOUT_SECONDS,
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                stderr_tail = exc.stderr.decode("utf-8", errors="replace")[-500:] if exc.stderr else ""
                raise OfflineSpeechAdapterError(f"espeak-ng synthesis failed: {stderr_tail}") from exc
            except subprocess.TimeoutExpired as exc:
                raise OfflineSpeechAdapterError("Offline speech synthesis timed out after 30s.") from exc

            return Path(tmp_file.name).read_bytes()
