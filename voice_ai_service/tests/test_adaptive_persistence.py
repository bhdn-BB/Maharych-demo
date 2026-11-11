import unittest
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from voice_ai_service.app.core import dependencies
from voice_ai_service.app.repositories.sql_database.postgresql import PostgreSQL
from voice_ai_service.app.schemas.db import Conversation, QuestionRecord, FeedbackOutbox, InterviewQuestionBank
from voice_ai_service.app.services.voice_conversation.session import InterviewSession
from voice_ai_service.app.services.interview_transition import InterviewTransition
from voice_ai_service.app.services.interview_storage import InterviewStorage
from test_adaptive_dialogue import bank_rows, make_agent


class AdaptivePersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.factory() as session:
            session.add_all([InterviewQuestionBank(**row) for row in bank_rows()])
            await session.commit()
        self.factory_patch = patch.object(dependencies, "_session_factory", return_value=self.factory)
        self.factory_patch.start()
        self.audio_patch = patch("voice_ai_service.app.services.voice_conversation.session.validate_audio", AsyncMock())
        self.audio_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.addCleanup(self.audio_patch.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_rollback_reload_partial_report_and_outbox_are_atomic(self):
        llm, _, _, candidate, position = make_agent()
        interview_id = str(uuid.uuid4())
        async with dependencies.db_session() as db:
            self.assertIsInstance(db.session, AsyncSession)
            conv = await InterviewStorage(db).ensure_conversation(interview_id, candidate.email, position.title)
            agent = InterviewSession(llm, db)
            state = agent.create_state(candidate, position, "algorithms", "uk", conv.id)
            await agent.ask(state)
            original_question = state["question_id"]
            await InterviewStorage(db).save(state)
        llm.fail = True
        with self.assertRaises(RuntimeError):
            async with dependencies.db_session() as db:
                state = InterviewStorage(db).load(await db.lock_interview(interview_id))
                await InterviewSession(llm, db).answer(state, b"audio", "audio/webm", str(uuid.uuid4()), original_question)
                await InterviewStorage(db).save(state)
        async with dependencies.db_session() as db:
            state = InterviewStorage(db).load(await db.lock_interview(interview_id))
            self.assertEqual(state["question_id"], original_question)
            self.assertFalse(state["records"])
            self.assertEqual(list((await db.session.exec(select(QuestionRecord))).all()), [])
        llm.fail = False
        answer_id = str(uuid.uuid4())
        async with dependencies.db_session() as db:
            state = InterviewStorage(db).load(await db.lock_interview(interview_id))
            await InterviewSession(llm, db).answer(state, b"audio", "audio/webm", answer_id, original_question)
            await InterviewStorage(db).save(state)
        async with dependencies.db_session() as db:
            state = InterviewStorage(db).load(await db.lock_interview(interview_id))
            agent = InterviewSession(llm, db)
            await agent.answer(state, b"audio", "audio/webm", answer_id, original_question)
            await agent.finish(state)
            await InterviewStorage(db).save(state)
        async with dependencies.db_session() as db:
            state = InterviewStorage(db).load(await db.lock_interview(interview_id))
            self.assertEqual(state["stage"], "finished")
            self.assertTrue(state["feedback"].partial)
            self.assertEqual(len((await db.session.exec(select(QuestionRecord))).all()), 1)
            self.assertEqual(len((await db.session.exec(select(FeedbackOutbox))).all()), 1)
            self.assertEqual(llm.audio_calls, 2)  # failed transaction plus committed answer; no duplicate call

    async def test_finishing_before_start_creates_terminal_placeholder(self):
        from voice_ai_service.app.services.interview_lifecycle import InterviewLifecycleService
        interview_id = str(uuid.uuid4())
        async with dependencies.db_session() as db:
            result = await InterviewLifecycleService(db, dependencies.get_agent).finish(interview_id)
            self.assertEqual(result, "abandoned")
        async with dependencies.db_session() as db:
            conversation = await db.lock_interview(interview_id)
            self.assertEqual(conversation.stage, "abandoned")
            self.assertIsNone(conversation.state_json)
        async with dependencies.db_session() as db:
            with self.assertRaises(ValueError):
                await InterviewStorage(db).ensure_conversation(interview_id, "late@example.com", "Backend")

    async def test_failure_to_add_outbox_rolls_back_feedback_and_state(self):
        llm, _, _, candidate, position = make_agent()
        interview_id = str(uuid.uuid4())
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            state, _ = await transition.start(interview_id, candidate, position, 2, "en", "algorithms")
            question_id = state["question_id"]
        async with dependencies.db_session() as db:
            state = InterviewStorage(db).load(await db.lock_interview(interview_id))
            agent = InterviewSession(llm, db)
            await agent.answer(state, audio=b"audio", mime_type="audio/webm",
                                 answer_id=str(uuid.uuid4()), question_id=question_id)
            await agent.finish(state)
            with patch.object(db, "add_outbox", AsyncMock(side_effect=RuntimeError("outbox unavailable"))):
                with self.assertRaisesRegex(RuntimeError, "outbox unavailable"):
                    await InterviewStorage(db).save(state)
        async with dependencies.db_session() as db:
            conversation = await db.lock_interview(interview_id)
            self.assertEqual(conversation.stage, "questioning")
            self.assertIsNone(conversation.feedback_json)
            self.assertEqual((await db.session.exec(select(QuestionRecord))).all(), [])
            self.assertEqual((await db.session.exec(select(FeedbackOutbox))).all(), [])

    async def test_transition_consumes_attempt_and_rejects_duplicate(self):
        llm, _, _, candidate, position = make_agent()
        interview_id, answer_id = str(uuid.uuid4()), str(uuid.uuid4())
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            state, _ = await transition.start(interview_id, candidate, position, 2, "uk", "algorithms")
            question_id = state["question_id"]
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            reserved, _, _ = await transition.apply(interview_id, "start_recording", question_id, answer_id, b"", "audio/webm")
            self.assertEqual(reserved["stage"], "recording")
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            state, transcript, text = await transition.apply(interview_id, "", question_id, answer_id, b"audio", "audio/webm")
            self.assertTrue(transcript)
            self.assertTrue(text)
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            with self.assertRaises(ValueError):
                await transition.apply(interview_id, "", question_id, answer_id, b"audio", "audio/webm")
            self.assertEqual(len((await db.session.exec(select(QuestionRecord))).all()), 1)
            self.assertEqual(llm.audio_calls, 1)

    async def test_graph_receives_history_restored_from_database(self):
        import json
        llm, _, _, candidate, position = make_agent()
        interview_id, answer_id = str(uuid.uuid4()), str(uuid.uuid4())
        async with dependencies.db_session() as db:
            state, _ = await InterviewTransition(db, InterviewSession(llm, db)).start(
                interview_id, candidate, position, 2, "en", "algorithms")
            question_id = state["question_id"]
            first_question = state["current_topic"].main_question
        async with dependencies.db_session() as db:
            await InterviewTransition(db, InterviewSession(llm, db)).apply(
                interview_id, "start_recording", question_id, answer_id, b"", "audio/webm")
        async with dependencies.db_session() as db:
            await InterviewTransition(db, InterviewSession(llm, db)).apply(
                interview_id, "", question_id, answer_id, b"audio", "audio/webm")
        history = json.loads(llm.calls[-1].prompt.user_prompt)["history"]
        self.assertEqual(history[0], {"role": "assistant", "content": first_question})
        self.assertEqual(history[1], {"role": "user", "content": llm.transcript})

    async def test_released_attempt_keeps_question_and_allows_a_new_recording(self):
        llm, _, _, candidate, position = make_agent()
        interview_id, failed_id, retry_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        async with dependencies.db_session() as db:
            state, _ = await InterviewTransition(db, InterviewSession(llm, db)).start(
                interview_id, candidate, position, 2, "en", "behavioral")
            question_id = state["question_id"]
        async with dependencies.db_session() as db:
            await InterviewTransition(db, InterviewSession(llm, db)).apply(
                interview_id, "start_recording", question_id, failed_id, b"", "audio/webm")
        async with dependencies.db_session() as db:
            released, _, _ = await InterviewTransition(db, InterviewSession(llm, db)).apply(
                interview_id, "release_recording", question_id, failed_id, b"", "audio/webm")
            self.assertEqual((released["stage"], released["question_id"]), ("questioning", question_id))
            self.assertEqual(released["records"], [])
        async with dependencies.db_session() as db:
            with self.assertRaises(ValueError):  # a released attempt cannot be released twice
                await InterviewTransition(db, InterviewSession(llm, db)).apply(
                    interview_id, "release_recording", question_id, failed_id, b"", "audio/webm")
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            await transition.apply(interview_id, "start_recording", question_id, retry_id, b"", "audio/webm")
        async with dependencies.db_session() as db:
            state, transcript, _ = await InterviewTransition(db, InterviewSession(llm, db)).apply(
                interview_id, "", question_id, retry_id, b"audio", "audio/webm")
            self.assertTrue(transcript)
            self.assertTrue(state["clarification"], "a scored answer leads to a follow-up on the same topic")
            self.assertEqual(len((await db.session.exec(select(QuestionRecord))).all()), 1)

    async def test_reconnect_skips_a_reserved_attempt(self):
        llm, _, _, candidate, position = make_agent()
        interview_id, answer_id = str(uuid.uuid4()), str(uuid.uuid4())
        async with dependencies.db_session() as db:
            transition = InterviewTransition(db, InterviewSession(llm, db))
            state, _ = await transition.start(interview_id, candidate, position, 2, "uk", "algorithms")
            question_id = state["question_id"]
        async with dependencies.db_session() as db:
            await InterviewTransition(db, InterviewSession(llm, db)).apply(interview_id, "start_recording", question_id, answer_id, b"", "audio/webm")
        async with dependencies.db_session() as db:
            state, _ = await InterviewTransition(db, InterviewSession(llm, db)).start(interview_id, candidate, position, 2, "uk", "algorithms")
            self.assertNotEqual(state["question_id"], question_id)
            self.assertTrue(state["records"][0]["skipped"])
            self.assertIsNone(state["records"][0]["score"])

    async def test_bank_filters_languages_and_roles_and_fails_closed_if_incomplete(self):
        async with dependencies.db_session() as db:
            from voice_ai_service.app.services.question_bank import QuestionBankService
            with patch("voice_ai_service.app.services.question_bank.secrets.choice", side_effect=lambda rows: next((r for r in rows if r["role"] == "Data Science"), rows[0])):
                selected = await QuestionBankService(db).select("system-design", "uk", "Data Science", "middle")
            self.assertEqual(len(selected), 5)
            self.assertEqual(len({row["key"] for row in selected}), 5)
            self.assertEqual(selected[0]["key"], "design-data")
            self.assertTrue(all(row["language"] == "uk" and row["source_url"].startswith("https://") for row in selected))
            await db.session.exec(delete(InterviewQuestionBank).where(
                InterviewQuestionBank.focus == "system-design", InterviewQuestionBank.language == "uk",
                InterviewQuestionBank.topic_index == 4,
            ))
            with self.assertRaisesRegex(ValueError, "Question bank has no"):
                await QuestionBankService(db).select("system-design", "uk", "Data Science", "middle")

    async def test_question_snapshot_survives_a_later_bank_edit(self):
        llm, _, _, candidate, position = make_agent()
        interview_id = str(uuid.uuid4())
        async with dependencies.db_session() as db:
            state, _ = await InterviewTransition(db, InterviewSession(llm, db)).start(
                interview_id, candidate, position, 2, "en", "algorithms")
            original = state["bank_questions"][0].copy()
        async with dependencies.db_session() as db:
            row = (await db.session.exec(select(InterviewQuestionBank).where(
                InterviewQuestionBank.key == original["key"], InterviewQuestionBank.language == "en"))).one()
            row.question = "Changed after interview started"
            db.session.add(row)
            await db.session.commit()
        async with dependencies.db_session() as db:
            restored = InterviewStorage(db).load(await db.lock_interview(interview_id))
            self.assertEqual(restored["bank_questions"][0], original)
            self.assertEqual(restored["current_bank_question"], original)
