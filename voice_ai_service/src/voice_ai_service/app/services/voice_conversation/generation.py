"""LangChain interview generation and response validation."""
import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from voice_ai_service.app.models.dto import LLMArgs, LLMPrompt
from voice_ai_service.app.services.prompts import render_prompt


class InterviewQuestion(BaseModel):
    question: str = Field(min_length=10, max_length=1500)


class InterviewSummary(BaseModel):
    summary: str
    recommendation: str
    strengths: list[str]
    improvements: list[str]


class DialogueChatModel(BaseChatModel):
    """Adapt the existing async provider boundary to LangChain messages."""

    provider: Any = Field(exclude=True)

    @property
    def _llm_type(self) -> str:
        return "interview_provider"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError("Interview generation is asynchronous")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        system = next(message.content for message in messages if isinstance(message, SystemMessage))
        user = next(message.content for message in reversed(messages) if isinstance(message, HumanMessage))
        text = await self.provider.generate_response(LLMArgs(
            prompt=LLMPrompt(system_prompt=system, user_prompt=user),
            max_tokens=2000, temperature=0.2,
        ))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


class InterviewGeneration:
    def __init__(self, provider):
        self.agent = create_agent(model=DialogueChatModel(provider=provider), tools=[])

    async def _generate(self, schema, instruction: str, context: dict):
        parser = PydanticOutputParser(pydantic_object=schema)
        result = await self.agent.ainvoke({"messages": [
            SystemMessage(content=render_prompt("structured_system", instruction=instruction,
                                                schema=json.dumps(schema.model_json_schema()))),
            HumanMessage(content=json.dumps(context, ensure_ascii=False, default=str)),
        ]})
        return parser.parse(result["messages"][-1].content)

    async def question(self, instruction: str, context: dict) -> InterviewQuestion:
        return await self._generate(InterviewQuestion, instruction, context)

    async def summary(self, instruction: str, context: dict) -> InterviewSummary:
        return await self._generate(InterviewSummary, instruction, context)
