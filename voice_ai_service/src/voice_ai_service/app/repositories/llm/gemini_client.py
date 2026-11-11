import logging
from typing import AsyncGenerator

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from httpx import HTTPError

from voice_ai_service.app.interfaces.llm import BaseLLM
from voice_ai_service.app.models.dto import LLMArgs


# Per-attempt budget and one retry keep a transient outage well inside the caller's 60 s window.
REQUEST_TIMEOUT_MS = 25_000
RETRY_ATTEMPTS = 2
logger = logging.getLogger(__name__)
TRANSIENT_STATUS_CODES = (408, 429, 500, 502, 503, 504)


class LLMProviderError(RuntimeError):
    """Gemini call failed; ``retryable`` is True for outages, rate limits and timeouts."""

    def __init__(self, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


def classify_error(err: Exception) -> LLMProviderError:
    """Map SDK/transport errors to a provider error so callers can tell outages from bad requests."""
    if isinstance(err, LLMProviderError):
        return err
    if isinstance(err, genai_errors.APIError):
        code = getattr(err, "code", None)
        return LLMProviderError(f"Gemini API error {code}: {err}", retryable=code in TRANSIENT_STATUS_CODES)
    if isinstance(err, (HTTPError, TimeoutError)):
        return LLMProviderError(f"Gemini transport error: {err}", retryable=True)
    return LLMProviderError(f"Unexpected Gemini error: {err}", retryable=False)


def _http_options() -> types.HttpOptions:
    return types.HttpOptions(
        # system_instruction is only accepted on v1beta; google-genai 3.x defaults to v1.
        api_version="v1beta",
        timeout=REQUEST_TIMEOUT_MS,
        retry_options=types.HttpRetryOptions(
            attempts=RETRY_ATTEMPTS, initial_delay=1.0, max_delay=4.0, exp_base=2.0, jitter=0.5,
            http_status_codes=list(TRANSIENT_STATUS_CODES),
        ),
    )


class GeminiClient(BaseLLM):
    """Gemini adapter. ``model_name`` may list fallbacks separated by commas
    (e.g. "gemini-3.8-flash,gemini-3-flash-preview"): when a model is rate-limited
    or overloaded (429/5xx, quotas are per model), the call moves to the next one and
    later calls start from the model that last succeeded."""

    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash") -> None:
        self._api_key = api_key
        self._models = [m.strip() for m in model_name.split(",") if m.strip()] or ["gemini-3.8-flash"]
        self._preferred = 0

    @property
    def _model_name(self) -> str:
        return self._models[self._preferred]

    def _client(self) -> genai.Client:
        return genai.Client(api_key=self._api_key, http_options=_http_options())

    def _order(self) -> list[int]:
        n = len(self._models)
        return [(self._preferred + i) % n for i in range(n)]

    async def _with_fallback(self, call):
        last = None
        for index in self._order():
            model = self._models[index]
            try:
                result = await call(model)
            except Exception as err:
                last = classify_error(err)
                if last.retryable and index != self._order()[-1]:
                    logger.warning("Gemini model %s unavailable (%s); trying the next model", model, str(last)[:80])
                    continue
                raise last from err
            self._preferred = index
            return result
        raise last

    def _build_config(self, args: LLMArgs, model: str | None = None) -> types.GenerateContentConfig:
        model = model or self._model_name
        return types.GenerateContentConfig(
            system_instruction=args.prompt.system_prompt,
            temperature=args.temperature,
            max_output_tokens=max(args.max_tokens, 4096) if model.startswith("gemini-3") else args.max_tokens,
            thinking_config=self._thinking_config(model),
        )

    def _thinking_config(self, model: str | None = None):
        # Gemini 3 supports LOW/MEDIUM/HIGH; MINIMAL is not supported.
        model = model or self._model_name
        return types.ThinkingConfig(thinking_level="LOW") if model.startswith("gemini-3") else None

    async def generate_stream(self, args: LLMArgs) -> AsyncGenerator[str, None]:
        # Fallback is only possible before the first token has been yielded.
        for index in self._order():
            model = self._models[index]
            started = False
            try:
                async with self._client().aio as client:
                    stream = await client.models.generate_content_stream(
                        model=model, contents=args.prompt.user_prompt, config=self._build_config(args, model),
                    )
                    async for event in stream:
                        if event.text:
                            started = True
                            yield event.text
                self._preferred = index
                return
            except Exception as err:
                error = classify_error(err)
                if started or not error.retryable or index == self._order()[-1]:
                    raise error from err
                logger.warning("Gemini model %s unavailable; trying the next model", model)

    async def generate(self, args: LLMArgs) -> str:
        async def call(model):
            async with self._client().aio as client:
                response = await client.models.generate_content(
                    model=model, contents=args.prompt.user_prompt, config=self._build_config(args, model),
                )
                return response.text
        return await self._with_fallback(call)

    async def generate_audio(
        self, audio: bytes, mime_type: str, system_prompt: str, contents: list[str], response_schema,
    ):
        """Generate structured output from supplied text and audio."""
        async def call(model):
            async with self._client().aio as client:
                return await client.models.generate_content(
                    model=model,
                    contents=[*contents, types.Part.from_bytes(data=audio, mime_type=mime_type)],
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        thinking_config=self._thinking_config(model),
                        max_output_tokens=8192,
                    ),
                )
        response = await self._with_fallback(call)
        if isinstance(response.parsed, response_schema):
            return response.parsed
        if response.text:
            return response_schema.model_validate_json(response.text)
        raise RuntimeError("Gemini returned no audio evaluation")
