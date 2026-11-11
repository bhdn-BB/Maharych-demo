"""Servicer-level behaviour: transient failures must not corrupt the stream and must be reported."""
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2 as pb
from voice_ai_service.app.grpc import interview_servicer as servicer_module
from voice_ai_service.app.grpc.interview_servicer import AIServiceServicer

ID = "628b8e76-c5ab-4d67-854c-70c31b2eca16"


@asynccontextmanager
async def fake_session():
    yield SimpleNamespace()


async def fake_agent(_db):
    return SimpleNamespace()


def startup_request():
    options = pb.AudioStreamStartupOptions(interview_id=ID, scenario_version=2, language="en", focus="algorithms")
    return pb.AudioStreamRequest(options=options)


async def stream(*requests):
    for request in requests:
        yield request


async def collect(requests):
    return [item async for item in AIServiceServicer().StreamInterview(stream(*requests), None)]


class StubTransition:
    """Replace InterviewTransition with scripted outcomes keyed by command."""
    outcomes: dict = {}
    calls: list = []

    def __init__(self, _db, _agent):
        pass

    async def start(self, *args):
        return StubTransition.outcomes["start"]

    async def apply(self, interview_id, command, question_id, answer_id, audio, mime_type):
        StubTransition.calls.append(command if command else "answer")
        outcome = StubTransition.outcomes[command or "answer"]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class ServicerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        StubTransition.calls = []
        questioning = {"stage": "questioning", "scenario_version": 2, "question_id": "q1", "current_topic": None}
        StubTransition.outcomes = {"start": (questioning, "Question?"), "answer": RuntimeError("provider down"),
                                   "skip_recording": ({"stage": "finished", "scenario_version": 2}, "", "")}
        patches = [
            patch.object(servicer_module, "db_session", fake_session),
            patch.object(servicer_module, "get_agent", fake_agent),
            patch.object(servicer_module, "InterviewTransition", StubTransition),
            patch.object(servicer_module, "synthesize", AsyncMock(return_value=b"mp3")),
            patch.object(servicer_module, "options_to_candidate", lambda opts: SimpleNamespace(email="c@example.com")),
            patch.object(servicer_module, "options_to_position", lambda opts: SimpleNamespace(title="Backend")),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_failed_answer_advances_by_skipping_instead_of_wedging_the_stream(self):
        answer = pb.AudioStreamRequest(audio_data=b"webm", question_id="q1", answer_id=ID)
        events = await collect([startup_request(), answer])

        self.assertEqual(StubTransition.calls, ["answer", "skip_recording"])
        self.assertIn(pb.AudioStreamResponse.INTERVIEW_FINISHED, [e.type for e in events])

    async def test_failed_answer_tells_the_candidate_it_was_skipped(self):
        answer = pb.AudioStreamRequest(audio_data=b"webm", question_id="q1", answer_id=ID)
        events = await collect([startup_request(), answer])
        errors = [e.error for e in events if e.type == pb.AudioStreamResponse.ERROR]
        self.assertIn(servicer_module.ANSWER_NOT_UNDERSTOOD, errors)

    async def test_provider_quota_keeps_the_question_instead_of_skipping(self):
        from voice_ai_service.app.repositories.llm.gemini_client import LLMProviderError
        quota = LLMProviderError("Gemini API error 429: RESOURCE_EXHAUSTED", retryable=True)
        try:
            raise RuntimeError("evaluation failed") from quota
        except RuntimeError as wrapped:
            StubTransition.outcomes["answer"] = wrapped
        StubTransition.outcomes["release_recording"] = (
            {"stage": "questioning", "scenario_version": 2, "question_id": "q1", "current_topic": None}, "", "")
        answer = pb.AudioStreamRequest(audio_data=b"webm", question_id="q1", answer_id=ID)
        events = await collect([startup_request(), answer])

        self.assertEqual(StubTransition.calls, ["answer", "release_recording"])
        self.assertNotIn("skip_recording", StubTransition.calls)
        after = events[-2:]
        self.assertEqual([e.type for e in after], [pb.AudioStreamResponse.ERROR, pb.AudioStreamResponse.STAGE_UPDATE])
        self.assertEqual(after[0].error, servicer_module.PROVIDER_UNAVAILABLE)
        self.assertEqual((after[1].stage, after[1].question_id), ("questioning", "q1"))

    async def test_silent_recording_is_skipped_with_a_microphone_hint(self):
        from voice_ai_service.app.services.audio_validation import SilentAudioError
        StubTransition.outcomes["answer"] = SilentAudioError("No speech detected in the recording")
        answer = pb.AudioStreamRequest(audio_data=b"webm", question_id="q1", answer_id=ID)
        events = await collect([startup_request(), answer])
        self.assertEqual(StubTransition.calls, ["answer", "skip_recording"])
        self.assertIn(servicer_module.NO_SPEECH, [e.error for e in events])

    async def test_non_retryable_provider_error_still_skips(self):
        from voice_ai_service.app.repositories.llm.gemini_client import LLMProviderError
        StubTransition.outcomes["answer"] = LLMProviderError("Gemini API error 400", retryable=False)
        answer = pb.AudioStreamRequest(audio_data=b"webm", question_id="q1", answer_id=ID)
        await collect([startup_request(), answer])
        self.assertEqual(StubTransition.calls, ["answer", "skip_recording"])

    async def test_failed_start_reports_an_error_event(self):
        StubTransition.outcomes["start"] = ValueError("bad options")

        async def failing_start(self, *args):
            raise ValueError("bad options")

        with patch.object(StubTransition, "start", failing_start):
            events = await collect([startup_request()])
        self.assertEqual([e.type for e in events], [pb.AudioStreamResponse.ERROR])
        self.assertIn("failed", events[0].error)

    async def test_failure_without_audio_is_reported_and_not_skipped(self):
        StubTransition.outcomes["finish"] = RuntimeError("provider down")
        events = await collect([startup_request(), pb.AudioStreamRequest(command="finish")])

        self.assertNotIn("skip_recording", StubTransition.calls)
        self.assertEqual(events[-1].type, pb.AudioStreamResponse.ERROR)

    async def test_startup_must_come_first(self):
        events = await collect([pb.AudioStreamRequest(command="finish")])
        self.assertEqual([e.type for e in events], [pb.AudioStreamResponse.ERROR])
