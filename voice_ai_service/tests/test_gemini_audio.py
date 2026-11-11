import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from voice_ai_service.app.models.dto import AudioEvaluationSchema, LLMArgs, LLMPrompt
from voice_ai_service.app.repositories.llm.gemini_client import GeminiClient
from voice_ai_service.app.services.dialogue_llm import DialogueModel


class GeminiAudioTest(unittest.IsolatedAsyncioTestCase):
    async def test_text_generation_uses_async_sdk(self):
        models = SimpleNamespace(generate_content=AsyncMock(return_value=SimpleNamespace(text="Hello")))
        client = MagicMock()
        client.aio.models = models
        client.aio.__aenter__ = AsyncMock(return_value=client.aio)
        client.aio.__aexit__ = AsyncMock(return_value=None)
        args = LLMArgs(prompt=LLMPrompt(system_prompt="Greet", user_prompt="Hello"))

        with patch("voice_ai_service.app.repositories.llm.gemini_client.genai.Client", return_value=client):
            response = await DialogueModel(GeminiClient("test-key", "gemini-2.5-flash")).generate_response(args)

        self.assertEqual(response, "Hello")
        models.generate_content.assert_awaited_once()
        client.aio.__aexit__.assert_awaited_once()

    async def test_greeting_stream_uses_async_sdk(self):
        async def chunks():
            yield SimpleNamespace(text="Hello")
            yield SimpleNamespace(text=" Oksana")

        models = SimpleNamespace(generate_content_stream=AsyncMock(return_value=chunks()))
        client = MagicMock()
        client.aio.models = models
        client.aio.__aenter__ = AsyncMock(return_value=client.aio)
        client.aio.__aexit__ = AsyncMock(return_value=None)
        args = LLMArgs(
            prompt=LLMPrompt(system_prompt="Greet", user_prompt="Hello"),
            streaming=True,
        )

        with patch("voice_ai_service.app.repositories.llm.gemini_client.genai.Client", return_value=client):
            stream = await DialogueModel(GeminiClient("test-key")).generate_response(args)
            response = "".join([part async for part in stream])

        self.assertEqual(response, "Hello Oksana")
        models.generate_content_stream.assert_awaited_once()

    async def test_audio_and_question_use_one_structured_gemini_call(self):
        result = AudioEvaluationSchema(
            transcript="An index speeds up lookups.",
            is_on_topic=True,
            score_percent=82,
            comment="Correct basic explanation",
        )
        models = SimpleNamespace(generate_content=AsyncMock(return_value=SimpleNamespace(parsed=result)))
        client = MagicMock()
        client.aio.models = models
        client.aio.__aenter__ = AsyncMock(return_value=client.aio)
        client.aio.__aexit__ = AsyncMock(return_value=None)

        with patch("voice_ai_service.app.repositories.llm.gemini_client.genai.Client", return_value=client):
            actual = await DialogueModel(GeminiClient("test-key")).evaluate_audio(
                b"webm-data", "audio/webm", "What is a database index?", "Correct use of indexing",
            )

        self.assertEqual(actual, result)
        models.generate_content.assert_awaited_once()
        kwargs = models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-3.8-flash")
        self.assertEqual(kwargs["config"].thinking_config.thinking_level.value, "LOW")
        self.assertIn("What is a database index?", kwargs["contents"][0])
        self.assertIn("Correct use of indexing", kwargs["contents"][1])
        self.assertEqual(kwargs["contents"][2].inline_data.data, b"webm-data")
        self.assertEqual(kwargs["contents"][2].inline_data.mime_type, "audio/webm")
        self.assertIs(kwargs["config"].response_schema, AudioEvaluationSchema)

if __name__ == "__main__":
    unittest.main()
