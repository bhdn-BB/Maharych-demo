import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from google.genai import errors as genai_errors

from voice_ai_service.app.repositories.llm import gemini_client as gc
from voice_ai_service.app.repositories.llm.gemini_client import (
    GeminiClient, LLMProviderError, classify_error,
)


def api_error(code):
    return genai_errors.APIError(code, {"error": {"code": code, "message": "boom", "status": "X"}})


class ClassifyErrorTest(unittest.TestCase):
    def test_outages_and_rate_limits_are_retryable(self):
        for code in (429, 500, 503):
            self.assertTrue(classify_error(api_error(code)).retryable, code)

    def test_bad_requests_are_not_retryable(self):
        for code in (400, 401, 403, 404):
            self.assertFalse(classify_error(api_error(code)).retryable, code)

    def test_timeouts_and_transport_errors_are_retryable(self):
        self.assertTrue(classify_error(TimeoutError()).retryable)
        self.assertTrue(classify_error(httpx.ConnectError("down")).retryable)

    def test_unknown_errors_are_not_retryable_and_provider_errors_pass_through(self):
        self.assertFalse(classify_error(ValueError("bug")).retryable)
        original = LLMProviderError("x", retryable=True)
        self.assertIs(classify_error(original), original)


class ClientConfigurationTest(unittest.TestCase):
    def test_requests_are_time_bounded_with_one_retry_on_transient_statuses(self):
        options = gc._http_options()
        self.assertEqual(options.timeout, gc.REQUEST_TIMEOUT_MS)
        # system_instruction requires v1beta; the SDK default moved to v1 in google-genai 3.x.
        self.assertEqual(options.api_version, "v1beta")
        self.assertEqual(options.retry_options.attempts, gc.RETRY_ATTEMPTS)
        self.assertIn(429, options.retry_options.http_status_codes)
        self.assertIn(503, options.retry_options.http_status_codes)
        # worst case (all attempts + backoff) must fit the 60 s transition budget
        self.assertLess(gc.REQUEST_TIMEOUT_MS / 1000 * gc.RETRY_ATTEMPTS + 4, 60)


class GenerateWrapsErrorsTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_raises_classified_error(self):
        client = MagicMock()
        client.models.generate_content = AsyncMock(side_effect=api_error(503))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.object(GeminiClient, "_client", return_value=MagicMock(aio=context)):
            llm = GeminiClient("key", "gemini-3.8-flash")
            args = MagicMock()
            args.prompt.user_prompt, args.prompt.system_prompt = "hi", "sys"
            args.temperature, args.max_tokens = 0.1, 100
            with self.assertRaises(LLMProviderError) as raised:
                await llm.generate(args)
        self.assertTrue(raised.exception.retryable)


def fake_client(side_effect):
    client = MagicMock()
    client.models.generate_content = AsyncMock(side_effect=side_effect)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    return client, MagicMock(aio=context)


def text_args():
    args = MagicMock()
    args.prompt.user_prompt, args.prompt.system_prompt = "hi", "sys"
    args.temperature, args.max_tokens = 0.1, 100
    return args


class ModelFallbackTest(unittest.IsolatedAsyncioTestCase):
    """Free-tier quotas are per model: a 429 on one model must not fail the interview."""

    async def test_quota_on_first_model_falls_back_and_remembers_the_working_one(self):
        ok = MagicMock(text="answer")
        client, wrapper = fake_client([api_error(429), ok, ok])
        with patch.object(GeminiClient, "_client", return_value=wrapper):
            llm = GeminiClient("key", "gemini-2.5-flash, gemini-3-flash-preview")
            self.assertEqual(await llm.generate(text_args()), "answer")
            self.assertEqual(await llm.generate(text_args()), "answer")
        models = [call.kwargs["model"] for call in client.models.generate_content.call_args_list]
        self.assertEqual(models, ["gemini-2.5-flash", "gemini-3-flash-preview", "gemini-3-flash-preview"])

    async def test_non_retryable_error_does_not_fall_back(self):
        client, wrapper = fake_client([api_error(400)])
        with patch.object(GeminiClient, "_client", return_value=wrapper):
            llm = GeminiClient("key", "gemini-2.5-flash,gemini-3-flash-preview")
            with self.assertRaises(LLMProviderError) as raised:
                await llm.generate(text_args())
        self.assertFalse(raised.exception.retryable)
        self.assertEqual(client.models.generate_content.call_count, 1)

    async def test_all_models_exhausted_raises_retryable_error(self):
        client, wrapper = fake_client([api_error(429), api_error(503)])
        with patch.object(GeminiClient, "_client", return_value=wrapper):
            llm = GeminiClient("key", "a-model,b-model")
            with self.assertRaises(LLMProviderError) as raised:
                await llm.generate(text_args())
        self.assertTrue(raised.exception.retryable)

    def test_thinking_config_follows_the_model_actually_called(self):
        llm = GeminiClient("key", "gemini-2.5-flash,gemini-3-flash-preview")
        self.assertIsNone(llm._thinking_config("gemini-2.5-flash"))
        self.assertIsNotNone(llm._thinking_config("gemini-3-flash-preview"))
