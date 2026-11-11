from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Protocol

from voice_ai_service.app.models.dto import AudioEvaluationSchema, LLMArgs


class TextGenerator(Protocol):
    """Text generation used by dialogue nodes."""

    async def generate_response(self, llm_parameters: LLMArgs) -> Any: ...


class DialogueLLM(TextGenerator, Protocol):
    """Text and audio operations used by the dialogue coordinator."""

    async def evaluate_audio(
        self, audio: bytes, mime_type: str, question: str, criteria: str,
    ) -> AudioEvaluationSchema: ...


class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, llm_parameters: LLMArgs) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_stream(self, llm_parameters: LLMArgs) -> AsyncIterator[str]:
        raise NotImplementedError
