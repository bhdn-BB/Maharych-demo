"""Server-only Gemini TTS, converted to MP3 for the interview stream."""
import asyncio
import base64
import shutil
import subprocess

from voice_ai_service.app.core.config import get_settings
from voice_ai_service.app.repositories.llm.gemini_speech import GeminiSpeechRepository
from voice_ai_service.app.services.prompts import render_prompt


def _to_mp3(audio: bytes) -> bytes:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("TTS encoder ffmpeg is not installed")
    try:
        result = subprocess.run(
            [binary, "-v", "error", "-nostdin", "-protocol_whitelist", "pipe",
             "-f", "wav", "-i", "pipe:0", "-map", "0:a:0", "-vn",
             "-c:a", "libmp3lame", "-b:a", "96k", "-f", "mp3", "pipe:1"],
            input=audio, capture_output=True, timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("TTS audio encoding timed out") from exc
    if result.returncode or not result.stdout:
        raise RuntimeError("Could not encode Gemini TTS audio")
    return result.stdout


VOICE_NAMES = {"anna": "Kore", "sophia": "Aoede", "daniel": "Charon", "alex": "Puck"}


class GeminiSpeechSynthesizer:
    """Request speech from Gemini and convert the returned WAV for streaming."""

    def __init__(self, repository=None):
        self.repository = repository or GeminiSpeechRepository()

    async def synthesize(self, text: str, language: str, voice_id: str = "") -> bytes:
        settings = get_settings()
        key = settings.gemini_api_key.strip()
        if not key or key.lower().startswith(("your", "replace", "placeholder")):
            raise RuntimeError("Gemini TTS is not configured")
        if language not in {"uk", "en"}:
            raise ValueError("Unsupported TTS language")
        if not text.strip() or len(text.encode("utf-8")) > 5000:
            raise ValueError("TTS input exceeds provider limit")

        if voice_id and voice_id not in VOICE_NAMES:
            raise ValueError("Unsupported TTS voice")
        voice = VOICE_NAMES[voice_id] if voice_id else (settings.tts_voice_uk if language == "uk" else settings.tts_voice_en)
        spoken_language = "Ukrainian" if language == "uk" else "English"
        response = await self.repository.generate(
            key, settings.gemini_tts_model, text, voice,
            render_prompt("tts_style", language=spoken_language).strip(),
        )
        audio = self._extract_audio(response)
        return await asyncio.to_thread(_to_mp3, audio)

    @staticmethod
    def _extract_audio(response: dict) -> bytes:
        blocks = [
            content
            for step in response.get("steps", [])
            if step.get("type") == "model_output"
            for content in step.get("content", [])
            if content.get("type") == "audio"
        ]
        if not blocks or blocks[-1].get("mime_type") != "audio/wav":
            raise RuntimeError("Gemini TTS returned no WAV audio")
        audio = base64.b64decode(blocks[-1].get("data", ""), validate=True)
        if not audio or len(audio) > 16 * 1024 * 1024:
            raise RuntimeError("Gemini TTS returned empty or oversized audio")
        return audio


async def synthesize(text: str, language: str, voice_id: str = "") -> bytes:
    return await GeminiSpeechSynthesizer().synthesize(text, language, voice_id)
