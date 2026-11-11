"""
InterviewState is the persisted dialogue memory passed into each graph turn.
"""
from __future__ import annotations

import operator
from typing import Annotated, Dict, List, Optional
from typing_extensions import TypedDict, NotRequired

from voice_ai_service.app.models.domain import Candidate, InterviewFeedback, InterviewTask, Position, QuestionEvaluation, Topic
from voice_ai_service.app.models.dto import EvaluationSchema


class InterviewState(TypedDict):
    scenario_version: NotRequired[int]
    language: NotRequired[str]
    focus: NotRequired[str]
    question_id: NotRequired[str]
    main_question: NotRequired[str]
    clarification: NotRequired[bool]
    first_answer: NotRequired[str]
    # Absent in sessions persisted before the 5x2 contract; readers default to 3 main questions and 1 follow-up.
    main_question_count: NotRequired[int]
    follow_up_limit: NotRequired[int]
    follow_up_count: NotRequired[int]
    topic_answers: NotRequired[List[str]]
    records: NotRequired[List[dict]]
    processed_answers: NotRequired[Dict[str, dict]]
    attempt_id: NotRequired[str]
    bank_questions: NotRequired[List[dict]]
    current_bank_question: NotRequired[Optional[dict]]
    session_id: str
    conversation_id: int                              # FK до conversations в БД

    stage: str                                        # InterviewStage value
    candidate: Candidate
    position: Position
    task: NotRequired[InterviewTask]

    current_topic: Optional[Topic]
    topic_index: int                                  # 0-based, below main_question_count

    completed_topics: Annotated[List[Topic], operator.add]
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    evaluations: Annotated[List[QuestionEvaluation], operator.add]

    warning_count: int
    input_message: Optional[str]
    audio_evaluation: Optional[EvaluationSchema]
    last_audio_sha256: Optional[str]
    last_transcript: Optional[str]
    eval_score: Optional[int]
    eval_comment: Optional[str]

    feedback: Optional[InterviewFeedback]
    error: Optional[str]
