"""
Transfer objects for API and AI provider boundaries.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from voice_ai_service.app.models.domain import Candidate, InterviewFeedback, InterviewTask, Position, QuestionType, Topic


# ── LLM ──────────────────────────────────────────────────────────────────────

class LLMPrompt(BaseModel):
    system_prompt: str
    user_prompt: str


class LLMArgs(BaseModel):
    prompt: LLMPrompt
    streaming: bool = False
    model_name: str = "gemini-3.8-flash"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=3000, ge=1)


# ── API request / response ────────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    candidate: Candidate
    position: Position
    task: InterviewTask


class SendMessageRequest(BaseModel):
    session_id: str
    audio_bytes_b64: Optional[str] = Field(None, description="Base64-encoded complete audio recording")
    audio_mime_type: str = "audio/webm"
    text_message: Optional[str] = Field(None, description="Plain-text fallback")


class StartInterviewResponse(BaseModel):
    session_id: str
    greeting: str
    first_question: str


class SendMessageResponse(BaseModel):
    session_id: str
    response: str
    stage: str
    topic_index: int
    is_finished: bool
    feedback: Optional[InterviewFeedback] = None


class SessionInfoResponse(BaseModel):
    session_id: str
    stage: str
    topic_index: int
    completed_topics: List[Topic]
    current_topic: Optional[Topic]
    conversation_history: List[Dict[str, str]]
    feedback: Optional[InterviewFeedback] = None



class SubTopicSchema(BaseModel):
    text: str

class TopicSchema(BaseModel):
    main_question: str
    sub_topics: List[str] = []
    question_type: Optional[QuestionType] = QuestionType.GENERAL

class EvaluationSchema(BaseModel):
    is_on_topic: bool
    score_percent: int = Field(ge=0, le=100)
    comment: str


class AudioEvaluationSchema(EvaluationSchema):
    transcript: str = Field(description="Verbatim transcription of the candidate's speech")
    correctness: Optional[int] = Field(default=None, ge=0, le=100)
    completeness: Optional[int] = Field(default=None, ge=0, le=100)
    reasoning: Optional[int] = Field(default=None, ge=0, le=100)


class TopicScoreSchema(BaseModel):
    topic_index: int
    score: int
    question_type: str
    comment: str
    strengths: List[str]
    weaknesses: List[str]

class FeedbackSchema(BaseModel):
    overall_score: int
    recommendation: str
    summary: str
    top_strengths: List[str]
    top_weaknesses: List[str]
    topic_scores: List[TopicScoreSchema]
