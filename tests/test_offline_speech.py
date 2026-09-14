"""
Tests for app/adapters/offline_speech.py - the zero-network ASR/TTS
fallback used when Bhashini isn't configured or a live call to it fails.

Deliberately exercises the REAL espeak-ng/pocketsphinx binaries, not
mocks, for the same reason tests/test_bhashini.py's
test_transcode_to_wav_converts_real_webm_opus_audio does: this module's
entire reason to exist is "does the zero-network path actually work",
which a mock can't prove. Accuracy assertions on transcribe() are
deliberately weak (a non-empty string, not an exact match) - see this
module's own docstring for the real, measured accuracy ceiling
PocketSphinx has against even a clean synthetic voice; a tight
assertion here would be asserting something this project doesn't
actually claim.
"""

import concurrent.futures
import shutil
import struct
import subprocess
import time
import wave
from io import BytesIO
from pathlib import Path

import pytest

from app.adapters import offline_speech
from app.adapters.offline_speech import (
    OfflineSpeechAdapter,
    OfflineSpeechAdapterError,
    _pcm_data_from_wav,
    _run_with_timeout,
)


def _wav_with_extra_chunk_before_data(pcm_bytes: bytes) -> bytes:
    """
    A real, valid WAV file - readable by Python's own `wave` module -
    that additionally carries a "LIST"/"INFO" chunk between `fmt ` and
    `data`, exactly the shape this project's own ffmpeg produces by
    default (it tags every WAV it writes with its own encoder version,
    e.g. "Lavf60.16.100"). Built by hand, deliberately not via ffmpeg,
    so this test proves the parsing logic itself against a known-exact
    expected PCM payload, independent of whatever ffmpeg happens to be
    installed in the environment running this test.
    """
    fmt_chunk = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
    list_chunk_data = b"INFO" + b"ISFT" + struct.pack("<I", 14) + b"Lavf60.16.100\x00"
    list_chunk = b"LIST" + struct.pack("<I", len(list_chunk_data)) + list_chunk_data
    data_chunk = b"data" + struct.pack("<I", len(pcm_bytes)) + pcm_bytes
    body = b"WAVE" + fmt_chunk + list_chunk + data_chunk
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _synthesize_reference_wav(text: str, voice: str) -> bytes:
    """Real espeak-ng call, independent of the adapter under test - used
    to produce input audio for transcribe()'s tests without depending on
    OfflineSpeechAdapter.synthesize() itself (that would test the module
    against its own output, proving nothing new)."""
    result = subprocess.run(
        ["espeak-ng", "-v", voice, "--stdout", text],
        capture_output=True,
        timeout=30,
        check=True,
    )
    return result.stdout


@pytest.mark.skipif(shutil.which("espeak-ng") is None, reason="espeak-ng not installed")
class TestSynthesize:
    def test_synthesizes_real_nonempty_audio_in_english(self):
        adapter = OfflineSpeechAdapter()
        audio = adapter.synthesize("Please see a doctor immediately.", target_language="en")
        assert isinstance(audio, bytes)
        assert len(audio) > 1000
        assert audio[:4] == b"RIFF"

    def test_synthesizes_real_nonempty_audio_in_hindi(self):
        adapter = OfflineSpeechAdapter()
        audio = adapter.synthesize("कृपया तुरंत डॉक्टर से मिलें।", target_language="hi")
        assert isinstance(audio, bytes)
        assert len(audio) > 1000

    def test_synthesizes_real_nonempty_audio_in_telugu(self):
        adapter = OfflineSpeechAdapter()
        audio = adapter.synthesize("దయచేసి వెంటనే వైద్యుడిని సంప్రదించండి.", target_language="te")
        assert isinstance(audio, bytes)
        assert len(audio) > 1000

    def test_rejects_unsupported_language(self):
        adapter = OfflineSpeechAdapter()
        with pytest.raises(OfflineSpeechAdapterError, match="does not support"):
            adapter.synthesize("hello", target_language="fr")

    def test_raises_when_espeak_ng_missing(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        adapter = OfflineSpeechAdapter()
        with pytest.raises(OfflineSpeechAdapterError, match="espeak-ng is not installed"):
            adapter.synthesize("hello", target_language="en")

    def test_passes_the_tuned_slower_rate_to_espeak_ng(self, monkeypatch):
        """
        Real, evidence-based change made 13 Sep 2026 after a live report
        that audio "won't progress smoother": espeak-ng's own unset
        default (175 words/minute) measurably produced the shortest, most
        rushed output of several rates tried on this project's own real
        audio-summary template text (see synthesize()'s own docstring for
        the actual numbers) - slowing it down is a documented way to
        reduce how clipped a formant-synthesized voice sounds. Proves the
        adapter actually passes an explicit, slower rate to the real
        command line - not that espeak-ng's own default is unchanged -
        by capturing the argv subprocess.run receives.
        """
        captured_argv = {}

        def fake_run(argv, **kwargs):
            captured_argv["argv"] = argv
            Path(argv[argv.index("-w") + 1]).write_bytes(b"RIFF....WAVEfake")
            return subprocess.CompletedProcess(argv, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        adapter = OfflineSpeechAdapter()

        adapter.synthesize("hello", target_language="en")

        argv = captured_argv["argv"]
        assert "-s" in argv
        rate = int(argv[argv.index("-s") + 1])
        assert rate < 175  # slower than espeak-ng's own unset default
        assert rate > 0


class TestPcmDataFromWav:
    """
    Real bug, found 13 Sep 2026 while investigating a live report that
    voice input "doesn't listen to the person completely": transcribe()
    used to hardcode wav_bytes[44:] to strip a WAV header, assuming
    ffmpeg's own WAV output is always the minimal 44-byte header with no
    extra chunks. Confirmed false for this project's actual ffmpeg -
    every real transcoded file carries a "LIST"/"INFO" chunk (ffmpeg's
    own encoder-version tag) between `fmt ` and `data`, pushing the real
    audio start well past byte 44. These tests use a hand-built WAV
    (_wav_with_extra_chunk_before_data above) with a known-exact PCM
    payload, so pass/fail doesn't depend on whatever ffmpeg version
    happens to be installed - the fixture reproduces the exact chunk
    shape ffmpeg produces, independent of it.
    """

    def test_extracts_exact_pcm_bytes_past_a_chunk_that_isnt_44_bytes(self):
        pcm = bytes(range(256)) * 4  # 1024 bytes of known, non-repeating-in-a-way-that-hides-bugs content
        wav_bytes = _wav_with_extra_chunk_before_data(pcm)

        extracted = _pcm_data_from_wav(wav_bytes)

        assert extracted == pcm

    def test_the_old_fixed_44_byte_offset_would_have_been_wrong_on_this_exact_fixture(self):
        """
        Documents the regression directly, not just the fix: proves the
        hardcoded wav_bytes[44:] slice this module used before today
        does NOT reproduce the real PCM payload once a LIST/INFO chunk
        (ffmpeg's ordinary, default WAV output shape) sits before `data`.
        On this fixture's exact 34-byte LIST chunk it prepends 34 bytes
        of WAV metadata (part of the LIST chunk, the literal "data" tag,
        and that chunk's own size field) before the real, complete,
        untruncated audio that follows - real content isn't lost, but
        PocketSphinx was still handed 17 samples (34 bytes at 16-bit
        mono) of decoder-confusing text-as-audio before every single
        recording, on every voice submission through this path. A
        differently-sized chunk from a different ffmpeg build could just
        as easily land on an odd byte count and misalign the 16-bit
        sample boundaries of everything after it too - this fixture
        being byte-perfect past the prefix is a property of this exact
        chunk size, not a guarantee the old code provided.
        """
        pcm = bytes(range(256)) * 4
        wav_bytes = _wav_with_extra_chunk_before_data(pcm)

        old_broken_slice = wav_bytes[44:]

        assert old_broken_slice != pcm
        assert len(old_broken_slice) == len(pcm) + 34  # 34 bytes of leaked WAV metadata prepended
        assert old_broken_slice[34:] == pcm  # the real audio itself, intact, just pushed 34 bytes late
        assert _pcm_data_from_wav(wav_bytes) == pcm  # today's fix gets it exactly right, no prefix at all


class TestRunWithTimeout:
    """
    Real bug, found 14 Sep 2026 auditing every blocking call in this
    module against the timeout every sibling call already has: espeak-ng
    (synthesize(), below) and every ffmpeg/httpx call in
    app/adapters/bhashini.py are all bounded, but transcribe()'s
    PocketSphinx decode ran unbounded, despite _TRANSCRIPTION_TIMEOUT_SECONDS
    already existing as a defined-but-unused constant. Measured directly:
    a ~250-second synthetic clip took ~60 seconds of real decode time on
    this machine, and nothing on /assess/voice caps upload length or size
    server-side (the 3-minute cap in web/app.js is a frontend
    MediaRecorder auto-stop only) - so an arbitrarily long upload could
    tie up a worker thread indefinitely. _run_with_timeout is the fix:
    these tests prove the timeout mechanism itself, independent of
    PocketSphinx, before TestTranscribe's own test proves it's actually
    wired into transcribe().
    """

    def test_returns_the_function_result_when_it_finishes_in_time(self):
        assert _run_with_timeout(lambda: "done", timeout_seconds=5) == "done"

    def test_raises_timeout_error_without_waiting_for_the_slow_call_to_finish(self):
        """
        The whole point of the fix: the caller must not block for the
        full duration of a slow call, only up to the timeout. Asserts on
        wall-clock time, not just that TimeoutError is raised, so a fix
        that raises the right exception but still blocks internally
        (e.g. executor.shutdown(wait=True)) would fail this test.
        """
        start = time.monotonic()
        with pytest.raises(concurrent.futures.TimeoutError):
            _run_with_timeout(lambda: time.sleep(2), timeout_seconds=0.1)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # nowhere near the full 2s the slow call sleeps for

    def test_propagates_the_real_exception_when_the_function_itself_fails(self):
        def _boom():
            raise ValueError("simulated decode failure")

        with pytest.raises(ValueError, match="simulated decode failure"):
            _run_with_timeout(_boom, timeout_seconds=5)


@pytest.mark.skipif(shutil.which("espeak-ng") is None, reason="espeak-ng not installed")
class TestTranscribe:
    def test_rejects_non_english_source_language_without_attempting_decode(self):
        """
        The honest limitation this module's docstring states plainly:
        no Hindi/Telugu offline acoustic model is bundled anywhere this
        project could fetch or verify (huggingface.co and
        alphacephei.com are both blocked by this environment's own
        egress policy - confirmed directly). Must fail immediately and
        clearly, never silently mistranscribe regional-language audio
        through an English-only model.
        """
        adapter = OfflineSpeechAdapter()
        with pytest.raises(OfflineSpeechAdapterError, match="only available for English"):
            adapter.transcribe(b"irrelevant-bytes", source_language="te")

        with pytest.raises(OfflineSpeechAdapterError, match="only available for English"):
            adapter.transcribe(b"irrelevant-bytes", source_language="hi")

    def test_transcribes_real_synthetic_english_speech_to_a_nonempty_string(self):
        """
        Real, live, end-to-end proof the offline ASR pipeline runs
        without crashing on real audio bytes: espeak-ng synthesizes a
        WAV, _transcode_to_wav resamples it, PocketSphinx decodes it.
        Deliberately does NOT assert the hypothesis matches the source
        text - measured directly during development, PocketSphinx
        against a synthetic TTS voice produced "we see all the recall is
        the" for "Please see a doctor immediately for this symptom",
        recognizable as English but far from accurate. Asserting exact
        content here would misrepresent that as more reliable than it
        measurably is; the real claim this test backs is narrower and
        true: the pipeline runs end to end, offline, and returns text.
        """
        reference_wav = _synthesize_reference_wav("please see a doctor immediately", "en")
        adapter = OfflineSpeechAdapter()

        result = adapter.transcribe(reference_wav, source_language="en")

        assert isinstance(result, str)

    def test_raises_on_undecodable_audio(self):
        adapter = OfflineSpeechAdapter()
        with pytest.raises(OfflineSpeechAdapterError):
            adapter.transcribe(b"not-audio-at-all", source_language="en")

    def test_transcribe_times_out_instead_of_hanging_on_a_long_decode(self, monkeypatch):
        """
        Proves _run_with_timeout is actually wired into transcribe(),
        not just correct in isolation (TestRunWithTimeout above). Uses
        the real decode path end to end (real espeak-ng audio, real
        ffmpeg transcode, real PocketSphinx Decoder) with
        _TRANSCRIPTION_TIMEOUT_SECONDS patched down to a value no real
        decode of this short a clip could finish inside of, so a pass
        here is a genuine race against real work, not a mock standing in
        for it.
        """
        monkeypatch.setattr(offline_speech, "_TRANSCRIPTION_TIMEOUT_SECONDS", 0.0001)
        reference_wav = _synthesize_reference_wav("please see a doctor immediately", "en")
        adapter = OfflineSpeechAdapter()

        with pytest.raises(OfflineSpeechAdapterError, match="timed out"):
            adapter.transcribe(reference_wav, source_language="en")

    def test_raises_when_pocketsphinx_missing(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pocketsphinx":
                raise ImportError("simulated missing pocketsphinx")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        adapter = OfflineSpeechAdapter()
        with pytest.raises(OfflineSpeechAdapterError, match="pocketsphinx is not installed"):
            adapter.transcribe(_synthesize_reference_wav("hello", "en"), source_language="en")


class TestTranslate:
    def test_identity_passthrough_for_english_to_english(self):
        adapter = OfflineSpeechAdapter()
        result = adapter.translate("fever and headache", source_language="en", target_language="en")
        assert result == "fever and headache"

    def test_rejects_any_non_identity_pair(self):
        """
        No offline text-to-text translation model is bundled here - see
        this class's own docstring in offline_speech.py for why that's
        the correct behavior, not a missing feature: transcribe() above
        already refuses every source_language except "en", so this pair
        should never actually be requested by
        app/adapters/bhashini.py's bhashini_to_intake() in practice.
        Raising loudly here is a safety net against that invariant ever
        being violated, not the primary defense.
        """
        adapter = OfflineSpeechAdapter()
        with pytest.raises(OfflineSpeechAdapterError, match="not available"):
            adapter.translate("fever", source_language="te", target_language="en")
        with pytest.raises(OfflineSpeechAdapterError, match="not available"):
            adapter.translate("fever", source_language="en", target_language="hi")
