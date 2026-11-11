import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

import array

from voice_ai_service.app.services.audio_validation import (
    AudioValidator, SilentAudioError, _validate, voiced_seconds,
)


WEBM_MAGIC = bytes([0x1A, 0x45, 0xDF, 0xA3])


def pcm(seconds, amplitude):
    """16 kHz mono 16-bit square-ish wave of the given amplitude."""
    n = int(16000 * seconds)
    return array.array("h", (amplitude if (i // 20) % 2 else -amplitude for i in range(n))).tobytes()


class AudioValidationTest(unittest.TestCase):
    def test_validator_uses_decoder_only_for_valid_container(self):
        decoder = Mock()
        decoder.decode.return_value = pcm(2, 3000)
        validator = AudioValidator(decoder)

        with self.assertRaises(ValueError):
            validator.validate(b"invalid", "audio/webm")
        decoder.decode.assert_not_called()

        audio = b"\x1a\x45\xdf\xa3"
        validator.validate(audio, "audio/webm")
        decoder.decode.assert_called_once_with(audio)

    def test_invalid_container_size_and_format_are_rejected(self):
        for audio, mime in ((b"", "audio/webm"), (b"not webm", "audio/webm"),
                            (b"\x1a\x45\xdf\xa3", "audio/mpeg"), (b"x" * (8 * 1024 * 1024 + 1), "audio/webm")):
            with self.subTest(mime=mime, size=len(audio)), self.assertRaises(ValueError):
                _validate(audio, mime)

    def test_missing_validator_is_not_silently_skipped(self):
        with patch("voice_ai_service.app.services.audio_validation.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                _validate(b"\x1a\x45\xdf\xa3", "audio/webm")

    def test_decoder_rejects_too_long_and_broken_audio(self):
        with patch("voice_ai_service.app.services.audio_validation.shutil.which", return_value="ffmpeg"), patch(
            "voice_ai_service.app.services.audio_validation.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, stdout=b"x" * (121 * 16000 * 2))
            with self.assertRaises(ValueError):
                _validate(b"\x1a\x45\xdf\xa3", "audio/webm")
            run.return_value = subprocess.CompletedProcess([], 1, stdout=b"")
            with self.assertRaises(ValueError):
                _validate(b"\x1a\x45\xdf\xa3", "audio/webm")

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not available")
    def test_real_webm_decoder_and_duration_limit(self):
        for seconds in (2, 121):
            audio = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                "sine=frequency=440:sample_rate=16000", "-t", str(seconds), "-c:a", "libopus", "-f", "webm", "pipe:1"],
                capture_output=True, check=True).stdout
            if seconds == 2:
                _validate(audio, "audio/webm")
            else:
                with self.assertRaises(ValueError):
                    _validate(audio, "audio/webm")


class SpeechPresenceTest(unittest.TestCase):
    """Silent recordings make the model invent an answer, so they are stopped before the provider."""

    def test_voiced_seconds_counts_only_loud_frames(self):
        self.assertAlmostEqual(voiced_seconds(pcm(2, 3000)), 2.0, places=1)
        self.assertEqual(voiced_seconds(pcm(2, 0)), 0.0)
        self.assertEqual(voiced_seconds(pcm(2, 100)), 0.0, "background hiss is not speech")
        self.assertAlmostEqual(voiced_seconds(pcm(1, 0) + pcm(1.5, 3000)), 1.5, places=1)

    def test_silent_and_too_short_recordings_are_rejected(self):
        for label, audio in (("muted", pcm(10, 0)), ("hiss", pcm(10, 120)), ("cough", pcm(9.5, 0) + pcm(0.5, 5000))):
            decoder = Mock()
            decoder.decode.return_value = audio
            with self.subTest(label), self.assertRaises(SilentAudioError):
                AudioValidator(decoder).validate(WEBM_MAGIC, "audio/webm")

    def test_silent_audio_is_a_value_error_for_existing_callers(self):
        self.assertTrue(issubclass(SilentAudioError, ValueError))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not available")
    def test_real_silent_webm_is_rejected(self):
        audio = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "5",
                                "-c:a", "libopus", "-f", "webm", "pipe:1"], capture_output=True, check=True).stdout
        with self.assertRaises(SilentAudioError):
            _validate(audio, "audio/webm")
