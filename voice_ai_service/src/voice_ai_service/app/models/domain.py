"""Domain models for interview state and scoring."""
from __future__ import annotations

import enum
from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class Grade(str, enum.Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD   = "lead"


class InterviewStage(str, enum.Enum):
    GREETING    = "greeting"
    QUESTIONING = "questioning"
    EVALUATING  = "evaluating"
    FINISHED    = "finished"
    ERROR       = "error"


class QuestionType(str, enum.Enum):
    GENERAL   = "general"
    PRACTICAL = "practical"


class Candidate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    surname: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=20)
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    years_of_experience: int = Field(..., ge=0, le=50)
    tech_stack: List[str] = Field(default_factory=list)
    resume: str = Field(..., description="Raw resume text")
    applied_at: date = Field(default_factory=date.today)
    is_active: bool = True


class Position(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=3, max_length=500)
    grade: Grade
    department: str = Field(..., min_length=2, max_length=100)
    required_experience: int = Field(..., ge=0, le=30)
    required_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    is_remote: bool = True
    location: Optional[str] = None


class InterviewTask(BaseModel):
    title: str = Field(min_length=5)
    description: str = Field(min_length=30)
    evaluation_criteria: str = Field(min_length=10)


class SubTopic(BaseModel):
    text: str
    answered: bool = False


class Topic(BaseModel):
    index: int = Field(..., description="1-based topic index")
    main_question: str
    sub_topics: List[SubTopic] = Field(default_factory=list)
    candidate_answer: Optional[str] = None
    question_type: QuestionType = QuestionType.GENERAL
    answered: bool = False


class TopicScore(BaseModel):
    topic_index: int
    score: int = Field(..., ge=0, le=100)
    question_type: QuestionType
    comment: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class InterviewFeedback(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    score_scale: int = 10
    partial: bool = False
    language: str = "en"
    questions: List[Dict] = Field(default_factory=list)
    recommendation: str = Field(..., description="hire / consider / reject")
    summary: str
    topic_scores: List[TopicScore] = Field(default_factory=list)
    top_strengths: List[str] = Field(default_factory=list)
    top_weaknesses: List[str] = Field(default_factory=list)


class QuestionEvaluation(BaseModel):
    topic_index: int
    question_type: QuestionType
    score_percent: int = Field(ge=0, le=100)
    comment: str

