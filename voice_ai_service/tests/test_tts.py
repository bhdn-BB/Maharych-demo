import base64
import io
import json
import shutil
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from voice_ai_service.app.services.tts import GeminiSpeechSynthesizer, _to_mp3, synthesize


class TTSTest(unittest.IsolatedAsyncioTestCase):
    def settings(self, **overrides):
        return SimpleNamespace(**{
            "gemini_api_key": "test-server-key", "gemini_tts_model": "gemini-3.8-flash-tts",
            "tts_voice_uk": "Kore", "tts_voice_en": "Puck", **overrides,
        })

    async def test_language_voice_mp3_and_server_only_key(self):
        for language, spoken, voice in (("uk", "Ukrainian", "Kore"), ("en", "English", "Puck")):
            with self.subTest(language=language):
                requests = []

                def respond(request):
                    requests.append(request)
                    return httpx.Response(200, json={"steps": [{"type": "model_output", "content": [
                        {"type": "audio", "mime_type": "audio/wav", "data": base64.b64encode(b"wav audio").decode()},
                    ]}]})

                client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
                with patch("voice_ai_service.app.services.tts.get_settings", return_value=self.settings()), patch(
                    "voice_ai_service.app.repositories.llm.gemini_speech.httpx.AsyncClient", return_value=client
                ), patch("voice_ai_service.app.services.tts._to_mp3", return_value=b"mp3 audio") as encode:
                    self.assertEqual(await synthesize("Question text", language), b"mp3 audio")
                request = requests[0]
                body = json.loads(request.content)
                self.assertEqual(str(request.url), "https://generativelanguage.googleapis.com/v1beta/interactions")
                self.assertEqual(request.headers["x-goog-api-key"], "test-server-key")
                self.assertNotIn("test-server-key", str(request.url))
                self.assertEqual(body["model"], "gemini-3.8-flash-tts")
                self.assertEqual(body["generation_config"]["speech_config"], [{"voice": voice}])
                content = body["input"][0]["content"][0]
                self.assertEqual(content["text"], "Question text")
                self.assertIn(spoken, content["annotations"][0]["style"])
                self.assertFalse(body["store"])
                encode.assert_called_once_with(b"wav audio")

    async def test_unconfigured_tts_fails_explicitly(self):
        for key in ("", "YOUR_GEMINI_API_KEY", "replace-me"):
            with self.subTest(key=key), patch(
                "voice_ai_service.app.services.tts.get_settings", return_value=self.settings(gemini_api_key=key)
            ), self.assertRaises(RuntimeError):
                await synthesize("Question", "uk")

    async def test_invalid_input_fails_before_network(self):
        for text, language in (("", "uk"), ("x" * 5001, "uk"), ("Question", "de")):
            with self.subTest(language=language, size=len(text)), patch(
                "voice_ai_service.app.services.tts.get_settings", return_value=self.settings()
            ), self.assertRaises(ValueError):
                await synthesize(text, language)

    async def test_selected_voice_reaches_provider(self):
        response = {"steps": [{"type": "model_output", "content": [
            {"type": "audio", "mime_type": "audio/wav", "data": base64.b64encode(b"wav").decode()},
        ]}]}
        repository = SimpleNamespace(generate=AsyncMock(return_value=response))
        with patch("voice_ai_service.app.services.tts.get_settings", return_value=self.settings()), patch(
            "voice_ai_service.app.services.tts._to_mp3", return_value=b"mp3"
        ):
            result = await GeminiSpeechSynthesizer(repository).synthesize("Question", "uk", "daniel")
        self.assertEqual(result, b"mp3")
        self.assertEqual(repository.generate.await_args.args[3], "Charon")

    async def test_unknown_voice_is_rejected_before_provider(self):
        repository = SimpleNamespace(generate=AsyncMock())
        with patch("voice_ai_service.app.services.tts.get_settings", return_value=self.settings()):
            with self.assertRaises(ValueError):
                await GeminiSpeechSynthesizer(repository).synthesize("Question", "en", "unknown")
        repository.generate.assert_not_awaited()

    async def test_provider_failure_and_missing_audio_are_reported(self):
        for status, body, expected in ((429, {}, httpx.HTTPStatusError), (200, {"steps": []}, RuntimeError)):
            with self.subTest(status=status):
                client = httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda _: httpx.Response(status, json=body)
                ))
                with patch("voice_ai_service.app.services.tts.get_settings", return_value=self.settings()), patch(
                    "voice_ai_service.app.repositories.llm.gemini_speech.httpx.AsyncClient", return_value=client
                ), self.assertRaises(expected):
                    await synthesize("Question", "uk")

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not available")
    async def test_real_wav_to_mp3_encoding(self):
        source = io.BytesIO()
        with wave.open(source, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b"\x00\x00" * 2400)
        result = _to_mp3(source.getvalue())
        self.assertTrue(result.startswith(b"ID3") or result.startswith(b"\xff"))
        self.assertGreater(len(result), 100)
