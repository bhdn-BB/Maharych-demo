import json
import unittest
from unittest.mock import AsyncMock

from langchain_core.exceptions import OutputParserException

from voice_ai_service.app.services.voice_conversation.generation import InterviewGeneration


class InterviewGenerationTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_passes_persisted_history_as_data(self):
        provider = type("Provider", (), {})()
        provider.generate_response = AsyncMock(return_value=json.dumps({"question": "What would you improve next?"}))
        generator = InterviewGeneration(provider)
        history = [{"role": "user", "content": "I would use a cache."}]

        result = await generator.question("Ask one question.", {"history": history})

        self.assertEqual(result.question, "What would you improve next?")
        request = provider.generate_response.await_args.args[0]
        self.assertEqual(json.loads(request.prompt.user_prompt)["history"], history)
        self.assertIn("untrusted", request.prompt.system_prompt)

    async def test_invalid_model_response_is_rejected(self):
        provider = type("Provider", (), {})()
        provider.generate_response = AsyncMock(return_value='{"question": "short"}')
        with self.assertRaises(OutputParserException):
            await InterviewGeneration(provider).question("Ask one question.", {})
