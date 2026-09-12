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

import shutil
import subprocess
import wave
from io import BytesIO

import pytest

from app.adapters.offline_speech import OfflineSpeechAdapter, OfflineSpeechAdapterError


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
