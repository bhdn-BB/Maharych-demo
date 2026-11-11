from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class QuestionType(str, enum.Enum):
    GENERAL   = "general"
    PRACTICAL = "practical"


class InterviewQuestionBank(SQLModel, table=True):
    __tablename__ = "interview_question_bank"
    __table_args__ = (
        UniqueConstraint("key", "version", "language", name="uq_question_bank_version_language"),
        Index("ix_question_bank_selection", "focus", "language", "topic_index", "active"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(max_length=80)
    version: int = Field(default=1)
    language: str = Field(max_length=2)
    focus: str = Field(max_length=30)
    topic_index: int
    role: str = Field(default="*", max_length=100)
    level: str = Field(default="*", max_length=20)
    question: str = Field(sa_column=Column(Text, nullable=False))
    criteria: str = Field(sa_column=Column(Text, nullable=False))
    source_url: str = Field(default="", max_length=500)
    provenance: str = Field(default="", max_length=200)
    active: bool = Field(default=True)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int]  = Field(default=None, primary_key=True)
    interview_id: Optional[str] = Field(default=None, sa_column=Column(String(36), unique=True, nullable=True))
    session_id: Optional[str] = Field(default=None, sa_column=Column(String(36), unique=True, nullable=True))
    state_json: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    feedback_json: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    candidate_email: str
    position_title: str
    stage: str = "greeting"
    overall_score: Optional[float] = None
    recommendation: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class QuestionRecord(SQLModel, table=True):
    __tablename__ = "question_records"

    id: Optional[int]       = Field(default=None, primary_key=True)
    conversation_id: int    = Field(foreign_key="conversations.id")
    topic_index: int
    question: str           = Field(max_length=2000)
    question_type: str      = QuestionType.GENERAL.value
    candidate_answer: str   = Field(max_length=5000, default="")
    score: Optional[int]    = None
    comment: Optional[str]  = None


class FeedbackOutbox(SQLModel, table=True):
    __tablename__ = "feedback_outbox"

    interview_id: str = Field(primary_key=True, max_length=36)
    published: bool = False
    attempts: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class FeedbackReport(SQLModel, table=True):
    __tablename__ = "feedback_reports"

    interview_id: str = Field(primary_key=True, max_length=36)
    pdf_data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
