from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from voice_ai_service.app.schemas.db import Conversation, FeedbackOutbox, FeedbackReport, QuestionRecord, InterviewQuestionBank
from voice_ai_service.app.repositories.sql_database.feedback_outbox import FeedbackOutboxRepository


class PostgreSQL:
    """Persist interview state and feedback using a request-scoped session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.outbox = FeedbackOutboxRepository(session)

    async def list_question_bank(self, focus: str, language: str) -> list[dict]:
        """Read active question versions in the requested format and language."""
        query = select(InterviewQuestionBank).where(
            InterviewQuestionBank.focus == focus,
            InterviewQuestionBank.language == language,
            InterviewQuestionBank.active == True,  # noqa: E712 - SQL expression
        )
        rows = (await self.session.exec(query)).all()
        return [row.model_dump() for row in rows]

    async def rollback(self) -> None:
        """Release the current transaction without persisting changes."""
        await self.session.rollback()

    async def commit(self) -> None:
        await self.session.commit()

    async def lock_interview(self, interview_id: str) -> Conversation | None:
        """Serialize state transitions across streams/processes until commit or rollback."""
        query = select(Conversation).where(Conversation.interview_id == interview_id).with_for_update()
        return (await self.session.exec(query.execution_options(populate_existing=True))).one_or_none()

    async def add_conversation(self, **fields) -> Conversation:
        conversation = Conversation(**fields)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def find_conversation(self, interview_id: str) -> Conversation | None:
        query = select(Conversation).where(Conversation.interview_id == interview_id)
        return (await self.session.exec(query)).first()

    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def update_conversation(self, conversation: Conversation) -> None:
        self.session.add(conversation)

    async def get_outbox(self, interview_id: str) -> FeedbackOutbox | None:
        return await self.session.get(FeedbackOutbox, interview_id)

    async def add_outbox(self, interview_id: str) -> None:
        self.session.add(FeedbackOutbox(interview_id=interview_id))

    async def find_conversation_by_session_id(self, session_id: str) -> Conversation | None:
        query = select(Conversation).where(Conversation.session_id == session_id)
        return (await self.session.exec(query)).first()

    async def find_feedback_by_interview_id(self, interview_id: str) -> dict | None:
        query = select(Conversation).where(Conversation.interview_id == interview_id)
        conversation = (await self.session.exec(query)).first()
        return conversation.feedback_json if conversation else None

    async def build_feedback_event(self, interview_id: str) -> dict:
        """Self-contained export event so consumers never read this service's tables."""
        conversation = await self.find_conversation(interview_id)
        if conversation is None or conversation.feedback_json is None:
            raise LookupError(f"Committed feedback is unavailable for {interview_id}")
        query = (
            select(QuestionRecord)
            .where(QuestionRecord.conversation_id == conversation.id)
            .order_by(QuestionRecord.topic_index, QuestionRecord.id)
        )
        records = (await self.session.exec(query)).all()
        return {
            "interview_id": interview_id,
            "position": conversation.position_title,
            "feedback": conversation.feedback_json,
            "questions": [
                {"index": r.topic_index, "question": r.question, "answer": r.candidate_answer,
                 "score": r.score, "comment": r.comment}
                for r in records
            ],
        }

    async def find_report_pdf_by_interview_id(self, interview_id: str) -> bytes | None:
        report = await self.session.get(FeedbackReport, interview_id)
        return report.pdf_data if report else None

    async def add_question_record(
        self,
        conversation_id: int,
        topic_index: int,
        question: str,
        question_type: str,
        candidate_answer: str,
        score: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> QuestionRecord:
        record = QuestionRecord(
            conversation_id=conversation_id,
            topic_index=topic_index,
            question=question,
            question_type=question_type,
            candidate_answer=candidate_answer,
            score=score,
            comment=comment,
        )
        self.session.add(record)
        await self.session.flush()
        return record
