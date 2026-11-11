import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from voice_ai_service.app.services.voice_conversation.session import InterviewSession

from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2 as pb
from voice_ai_service.app.grpc import interview_servicer


class FakeDatabase:
    restored_state = None
    session = SimpleNamespace(rollback=AsyncMock())

    async def rollback(self):
        await self.session.rollback()

    async def lock_interview(self, interview_id):
        return SimpleNamespace(id=42, stage="greeting")

    async def get_or_create_interview_conversation(self, interview_id, email, position):
        return SimpleNamespace(id=42, stage="greeting")

    async def load_interview_state(self, conversation):
        return self.restored_state

    async def save_interview_state(self, state):
        self.restored_state = state


class VoiceAudioTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_passes_selected_voice_to_synthesizer(self):
        state = {"stage": "questioning", "current_topic": SimpleNamespace(index=1, main_question="Hello"),
                 "language": "uk", "scenario_version": 2}
        synthesizer = AsyncMock(return_value=b"audio")
        with patch.object(interview_servicer, "synthesize", synthesizer):
            events = [message async for message in interview_servicer.audio_events(state, "daniel")]
        synthesizer.assert_awaited_once_with("Hello", "uk", "daniel")
        self.assertEqual(events[0].ai_audio_data, b"audio")


class FakeStorage:
    def __init__(self, db):
        self.db = db

    async def ensure_conversation(self, interview_id, email, position):
        return await self.db.get_or_create_interview_conversation(interview_id, email, position)

    def load(self, conversation):
        return self.db.restored_state

    async def save(self, state):
        await self.db.save_interview_state(state)


@asynccontextmanager
async def fake_db_session():
    yield shared_db


shared_db = FakeDatabase()


class FakeAgent:
    current_text = staticmethod(InterviewSession.current_text)
    def create_state(self, candidate, position, focus, language, conversation_id):
        state = self.make_initial_state(candidate, position, None, conversation_id)
        state.update(scenario_version=2, question_id="question-1", language=language)
        return state

    def make_initial_state(self, candidate, position, task, conversation_id):
        return {
            "session_id": "session-42",
            "conversation_id": conversation_id,
            "stage": "greeting",
            "topic_index": 0,
            "current_topic": None,
            "conversation_history": [],
        }

    async def ask(self, state):
        state["stage"] = "questioning"
        state["current_topic"] = SimpleNamespace(index=1, main_question="First backend question")
        state["conversation_history"].append(
            {"role": "assistant", "content": "First backend question"}
        )
        return "Hello Oksana"

    async def run_audio(self, state, audio, mime_type):
        assert audio == b"webm-data"
        assert mime_type == "audio/webm"
        state["current_topic"] = SimpleNamespace(index=2, main_question="Restored question")
        return "An index speeds up lookups", "Next question"


async def fake_get_agent(db):
    return FakeAgent()


async def startup_request():
    yield pb.AudioStreamRequest(options=pb.AudioStreamStartupOptions(
        interview_id="628b8e76-c5ab-4d67-854c-70c31b2eca16",
        candidate=pb.CandidateInfo(
            name="Oksana", surname="Shevchenko", email="candidate@example.com",
            phone_number="+380501234567", is_active=True,
        ),
        position=pb.PositionInfo(title="Backend", grade=pb.GRADE_MIDDLE),
        scenario_version=2, language="uk", focus="algorithms",
    ))


async def startup_and_audio_request():
    async for request in startup_request():
        yield request
    yield pb.AudioStreamRequest(audio_data=b"webm-data")


async def startup_without_task():
    async for request in startup_request():
        yield request


class GRPCStartupTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        shared_db.restored_state = None
        storage_patch = patch("voice_ai_service.app.services.interview_transition.InterviewStorage", FakeStorage)
        storage_patch.start()
        self.addCleanup(storage_patch.stop)

    async def test_adaptive_startup_rejects_removed_modes(self):
        for focus in ("live-coding", "unknown"):
            with self.subTest(focus=focus):
                async def request():
                    async for item in startup_request():
                        item.options.scenario_version = 2
                        item.options.language = "uk"
                        item.options.focus = focus
                        yield item
                with patch.object(interview_servicer, "db_session", fake_db_session), patch.object(interview_servicer, "get_agent", fake_get_agent):
                    events = [event async for event in interview_servicer.AIServiceServicer().StreamInterview(request(), None)]
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].type, pb.AudioStreamResponse.ERROR)
                self.assertIsNone(shared_db.restored_state)

    async def test_startup_rejects_legacy_scenario(self):
        async def legacy_request():
            async for request in startup_without_task():
                request.options.scenario_version = 0
                yield request
        with patch.object(interview_servicer, "db_session", fake_db_session), patch.object(interview_servicer, "get_agent", fake_get_agent):
            events = [event async for event in interview_servicer.AIServiceServicer().StreamInterview(legacy_request(), None)]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, pb.AudioStreamResponse.ERROR)
    async def test_startup_sends_greeting_and_first_question(self):
        with patch.object(interview_servicer, "db_session", fake_db_session), patch.object(
            interview_servicer, "get_agent", fake_get_agent
        ), patch.object(interview_servicer, "synthesize", AsyncMock(return_value=b"MP3")):
            events = [
                event async for event in interview_servicer.AIServiceServicer().StreamInterview(
                    startup_request(), None
                )
            ]

        self.assertEqual([event.type for event in events], [
            pb.AudioStreamResponse.AI_TEXT, pb.AudioStreamResponse.STAGE_UPDATE, pb.AudioStreamResponse.AI_AUDIO,
        ])
        self.assertEqual(events[1].current_question, 1)
        self.assertEqual(events[0].ai_text, "First backend question")

    async def test_audio_without_reservation_is_rejected(self):
        with patch.object(interview_servicer, "db_session", fake_db_session), patch.object(
            interview_servicer, "get_agent", fake_get_agent
        ), patch.object(interview_servicer, "synthesize", AsyncMock(return_value=b"MP3")):
            events = [
                event async for event in interview_servicer.AIServiceServicer().StreamInterview(
                    startup_and_audio_request(), None
                )
            ]
        self.assertEqual(events[3].type, pb.AudioStreamResponse.ERROR)

    async def test_reconnect_restores_question_without_new_greeting(self):
        restored = {
            "scenario_version": 2,
            "session_id": "restored-session",
            "conversation_id": 42,
            "stage": "questioning",
            "topic_index": 1,
            "current_topic": SimpleNamespace(index=2, main_question="Restored question"),
            "conversation_history": [{"role": "assistant", "content": "Restored question"}],
        }

        @asynccontextmanager
        async def restored_db_session():
            db = FakeDatabase()
            db.restored_state = restored
            yield db

        with patch.object(interview_servicer, "db_session", restored_db_session), patch.object(
            interview_servicer, "get_agent", fake_get_agent
        ), patch.object(interview_servicer, "synthesize", AsyncMock(return_value=b"MP3")):
            events = [
                event async for event in interview_servicer.AIServiceServicer().StreamInterview(
                    startup_request(), None
                )
            ]

        self.assertEqual([event.type for event in events], [
            pb.AudioStreamResponse.AI_TEXT, pb.AudioStreamResponse.STAGE_UPDATE, pb.AudioStreamResponse.AI_AUDIO,
        ])
        self.assertEqual(events[1].current_question, 2)
        self.assertEqual(events[0].ai_text, "Restored question")


if __name__ == "__main__":
    unittest.main()
