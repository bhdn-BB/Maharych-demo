import unittest

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from voice_ai_service.app.repositories.sql_database.postgresql import PostgreSQL
from voice_ai_service.app.models.domain import Candidate, Grade, InterviewFeedback, InterviewTask, Position, Topic
from voice_ai_service.app.schemas.db import Conversation, FeedbackOutbox
from voice_ai_service.app.services.interview_storage import InterviewStorage


class ConversationRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_published_outbox_request_is_not_returned_again(self) -> None:
        interview_id = "628b8e76-c5ab-4d67-854c-70c31b2eca16"
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            session.add(FeedbackOutbox(interview_id=interview_id))
            await session.commit()
            repository = PostgreSQL(session)
            pending = await repository.outbox.pending()
            self.assertEqual([request.interview_id for request in pending], [interview_id])
            await repository.outbox.mark_published(pending[0])
            await repository.outbox.commit()

        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            self.assertEqual(await PostgreSQL(session).outbox.pending(), [])

    async def test_rollback_discards_uncommitted_conversation_changes(self) -> None:
        interview_id = "628b8e76-c5ab-4d67-854c-70c31b2eca16"
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            conversation = await InterviewStorage(repository).ensure_conversation(
                interview_id, "candidate@example.com", "Backend",
            )
            conversation.stage = "abandoned"
            session.add(conversation)
            await session.flush()
            await repository.rollback()

        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            restored = await PostgreSQL(session).lock_interview(interview_id)
            self.assertEqual(restored.stage, "greeting")

    async def test_interview_reconnect_reuses_conversation(self) -> None:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            first = await InterviewStorage(repository).ensure_conversation(
                "628b8e76-c5ab-4d67-854c-70c31b2eca16",
                "candidate@example.com",
                "Backend",
            )
            second = await InterviewStorage(repository).ensure_conversation(
                "628b8e76-c5ab-4d67-854c-70c31b2eca16",
                "candidate@example.com",
                "Backend",
            )
            conversations = (await session.exec(select(Conversation))).all()

        self.assertEqual(first.id, second.id)
        self.assertEqual(len(conversations), 1)

    async def test_interview_id_cannot_be_reused_with_different_context(self) -> None:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            await InterviewStorage(repository).ensure_conversation(
                "628b8e76-c5ab-4d67-854c-70c31b2eca16",
                "candidate@example.com",
                "Backend",
            )
            with self.assertRaises(ValueError):
                await InterviewStorage(repository).ensure_conversation(
                    "628b8e76-c5ab-4d67-854c-70c31b2eca16",
                    "another@example.com",
                    "Backend",
                )

    async def test_state_and_feedback_survive_new_database_session(self) -> None:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            conversation = await InterviewStorage(repository).ensure_conversation(
                "628b8e76-c5ab-4d67-854c-70c31b2eca16",
                "candidate@example.com", "Backend",
            )
            state = {
                "session_id": "2b54a812-c290-477b-a816-93a6550e487f",
                "conversation_id": conversation.id,
                "stage": "questioning",
                "candidate": Candidate(
                    name="Oksana", surname="Shevchenko", email="candidate@example.com",
                    phone_number="+380501234567", years_of_experience=3,
                    resume="Backend developer",
                ),
                "position": Position(
                    title="Backend Developer", description="Backend work",
                    grade=Grade.MIDDLE, department="Engineering", required_experience=2,
                ),
                "task": InterviewTask(
                    title="Two Sum", description="Find two distinct indices whose values add up to a target.",
                    evaluation_criteria="Correctness and complexity",
                ),
                "current_topic": Topic(index=1, main_question="What is an index?"),
                "topic_index": 0,
                "completed_topics": [],
                "conversation_history": [{"role": "assistant", "content": "What is an index?"}],
                "evaluations": [],
                "warning_count": 0,
                "input_message": None,
                "audio_evaluation": None,
                "last_audio_sha256": None,
                "last_transcript": None,
                "eval_score": None,
                "eval_comment": None,
                "feedback": None,
                "error": None,
            }
            await InterviewStorage(repository).save(state)
            self.assertEqual((await session.exec(select(FeedbackOutbox))).all(), [])

        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            restored = InterviewStorage(repository).load(await repository.find_conversation_by_session_id(state["session_id"]))
            self.assertEqual(restored["current_topic"].main_question, "What is an index?")
            self.assertEqual(restored["candidate"].name, "Oksana")

        state["stage"] = "finished"
        state["feedback"] = InterviewFeedback(
            overall_score=8.2, recommendation="consider", summary="Good fundamentals",
        )
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            await InterviewStorage(repository).save(state)
            await InterviewStorage(repository).save(state)
            requests = (await session.exec(select(FeedbackOutbox))).all()
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0].interview_id, "628b8e76-c5ab-4d67-854c-70c31b2eca16")
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            repository = PostgreSQL(session)
            report = await repository.find_feedback_by_interview_id(
                "628b8e76-c5ab-4d67-854c-70c31b2eca16"
            )
            self.assertEqual(report["overall_score"], 8.2)


if __name__ == "__main__":
    unittest.main()
