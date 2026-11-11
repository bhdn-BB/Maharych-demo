"""Validate bounded WebM recordings before sending them to the provider."""

import array
import asyncio
import math
import shutil
import subprocess


class SilentAudioError(ValueError):
    """The recording decodes but contains (almost) no speech, e.g. a muted or wrong microphone.
    Providers tend to invent an answer for such audio, so it must never reach them."""


SAMPLE_RATE = 16000
FRAME = SAMPLE_RATE // 50          # 20 ms frames
VOICE_RMS = 300                    # about -40 dBFS for 16-bit PCM
MIN_VOICED_SECONDS = 1.0


def voiced_seconds(pcm: bytes, stop_at: float | None = None) -> float:
    """Seconds of 16-bit mono PCM whose 20 ms RMS is above the speech threshold
    (counting stops early once ``stop_at`` seconds are found)."""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    voiced = 0
    for start in range(0, len(samples) - FRAME + 1, FRAME):
        frame = samples[start:start + FRAME]
        if math.sqrt(sum(x * x for x in frame) / FRAME) >= VOICE_RMS:
            voiced += 1
            if stop_at is not None and voiced * FRAME / SAMPLE_RATE >= stop_at:
                break
    return voiced * FRAME / SAMPLE_RATE


class FFmpegAudioDecoder:
    """Decode the first audio stream to mono PCM using FFmpeg."""

    def decode(self, audio: bytes) -> bytes:
        binary = shutil.which("ffmpeg")
        if not binary:
            raise RuntimeError("Audio validator ffmpeg is not installed")
        try:
            result = subprocess.run(
                [
                    binary, "-v", "error", "-nostdin", "-protocol_whitelist", "pipe",
                    "-f", "matroska", "-i", "pipe:0", "-map", "0:a:0", "-t", "121", "-vn",
                    "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1",
                ],
                input=audio,
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Audio decoding timed out") from exc
        if result.returncode:
            raise ValueError("Recording is invalid or exceeds 120 seconds")
        return result.stdout


class AudioValidator:
    """Check the container and decoded duration of an interview recording."""

    def __init__(self, decoder: FFmpegAudioDecoder | None = None) -> None:
        self._decoder = decoder if decoder is not None else FFmpegAudioDecoder()

    def validate(self, audio: bytes, mime_type: str) -> None:
        if mime_type.split(";")[0] != "audio/webm" or not audio or len(audio) > 8 * 1024 * 1024:
            raise ValueError("Expected a complete WebM recording of at most 8 MiB")
        if not audio.startswith(b"\x1a\x45\xdf\xa3"):
            raise ValueError("Invalid WebM header")
        decoded = self._decoder.decode(audio)
        if not decoded or len(decoded) > 120.1 * 16000 * 2:
            raise ValueError("Recording is invalid or exceeds 120 seconds")
        if voiced_seconds(decoded, stop_at=MIN_VOICED_SECONDS) < MIN_VOICED_SECONDS:
            raise SilentAudioError("No speech detected in the recording")

    async def validate_async(self, audio: bytes, mime_type: str) -> None:
        await asyncio.to_thread(self.validate, audio, mime_type)


def _validate(audio: bytes, mime_type: str) -> None:
    AudioValidator().validate(audio, mime_type)


async def validate_audio(audio: bytes, mime_type: str) -> None:
    await AudioValidator().validate_async(audio, mime_type)
