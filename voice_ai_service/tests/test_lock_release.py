"""All LLM work of an answer must run while the row lock and pooled connection are released."""
import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from voice_ai_service.app.services.interview_transition import DeferredRecords, InterviewTransition

ANSWER = "628b8e76-c5ab-4d67-854c-70c31b2eca16"
QUESTION = "q-1"
AUDIO = b"webm-bytes"
DONE = {ANSWER: {"transcript": "t", "sha256": hashlib.sha256(AUDIO).hexdigest(), "question_id": QUESTION}}


def recording_state(**overrides):
    state = {"scenario_version": 2, "stage": "recording", "attempt_id": ANSWER, "question_id": QUESTION,
             "conversation_id": 1, "topic_index": 0, "records": [], "processed_answers": {}}
    state.update(overrides)
    return state


class Harness:
    """Records the order of lock/rollback/plan/write/answer calls made by InterviewTransition."""

    def __init__(self, states):
        self.events = []
        self.states = list(states)
        self.loads = 0
        async def lock(_id):
            self.events.append("lock")
            return SimpleNamespace()

        async def rollback():
            self.events.append("rollback")

        async def write(*_a, **_k):
            self.events.append("write")

        self.db = SimpleNamespace(
            lock_interview=AsyncMock(side_effect=lock), rollback=AsyncMock(side_effect=rollback),
            add_question_record=AsyncMock(side_effect=write),
        )
        self.planner_state = None
        self.session = SimpleNamespace(with_db=self._with_db, answer=AsyncMock(side_effect=self._stored_answer))
        self.transition = InterviewTransition(self.db, self.session)
        self.transition.storage = SimpleNamespace(load=self._load, save=AsyncMock())

    def _with_db(self, deferred):
        async def plan(planned_state, **kwargs):
            self.events.append("plan")
            self.planner_state = planned_state
            planned_state["topic_index"] = 1  # the plan advances the interview
            await deferred.add_question_record(1, 1, "question", "general", "answer", 8, "comment")
            return "transcript", "next question"
        return SimpleNamespace(answer=plan)

    async def _stored_answer(self, state, **kwargs):
        self.events.append("answer")
        return "stored transcript", "stored text"

    def _load(self, _conversation):
        index = min(self.loads, len(self.states) - 1)
        self.loads += 1
        return self.states[index]

    async def apply(self):
        return await self.transition.apply("iv", "", QUESTION, ANSWER, AUDIO, "audio/webm")


class LockReleaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_whole_answer_is_planned_between_rollback_and_relock(self):
        h = Harness([recording_state(), recording_state()])
        state, transcript, text = await h.apply()

        # records are written only after the lock is re-acquired, never while planning
        self.assertEqual(h.events, ["lock", "rollback", "plan", "lock", "write"])
        self.assertEqual((transcript, text), ("transcript", "next question"))
        self.assertIs(state, h.planner_state)
        self.assertEqual(state["topic_index"], 1)
        h.transition.storage.save.assert_awaited_once_with(state)

    async def test_deferred_writes_are_replayed_in_order(self):
        h = Harness([recording_state(), recording_state()])
        await h.apply()
        self.assertEqual(h.db.add_question_record.await_args.args, (1, 1, "question", "general", "answer", 8, "comment"))

    async def test_state_changed_during_planning_is_rejected_without_writing(self):
        for changed in (recording_state(stage="skipped"), recording_state(topic_index=1),
                        recording_state(attempt_id="other"), recording_state(records=[{"x": 1}])):
            h = Harness([recording_state(), changed])
            with self.assertRaises(ValueError):
                await h.apply()
            self.assertNotIn("write", h.events)
            h.transition.storage.save.assert_not_awaited()

    async def test_replayed_answer_skips_planning_and_keeps_the_lock(self):
        h = Harness([recording_state(processed_answers=DONE)])
        await h.apply()
        self.assertEqual(h.events, ["lock", "answer"])

    async def test_answer_applied_by_a_concurrent_request_is_replayed_not_duplicated(self):
        h = Harness([recording_state(), recording_state(stage="questioning", processed_answers=DONE)])
        state, transcript, _ = await h.apply()

        self.assertEqual(h.events, ["lock", "rollback", "plan", "lock", "answer"])
        self.assertEqual(transcript, "stored transcript")
        self.assertNotIn("write", h.events)


class DeferredRecordsTest(unittest.IsolatedAsyncioTestCase):
    async def test_records_calls_and_forbids_any_other_database_access(self):
        deferred = DeferredRecords()
        await deferred.add_question_record(1, 2, "q", "general", "a", None, "c")
        self.assertEqual(deferred.calls, [((1, 2, "q", "general", "a", None, "c"), {})])
        with self.assertRaises(AssertionError):
            deferred.list_question_bank
