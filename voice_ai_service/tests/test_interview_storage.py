import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy.exc import IntegrityError

from voice_ai_service.app.services.interview_storage import InterviewStorage


class InterviewStorageRaceTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_start_reloads_and_checks_the_winner(self):
        winner = SimpleNamespace(candidate_email="candidate@example.com", position_title="Backend")
        repository = SimpleNamespace(
            find_conversation=AsyncMock(side_effect=[None, winner]),
            add_conversation=AsyncMock(side_effect=IntegrityError("insert", {}, Exception("unique"))),
            rollback=AsyncMock(), commit=AsyncMock(),
        )
        result = await InterviewStorage(repository).ensure_conversation("id", "candidate@example.com", "Backend")
        self.assertIs(result, winner)
        repository.rollback.assert_awaited_once()
        repository.commit.assert_not_awaited()

    async def test_concurrent_finish_locks_the_winning_start(self):
        winner = SimpleNamespace(stage="greeting")
        repository = SimpleNamespace(
            add_conversation=AsyncMock(side_effect=IntegrityError("insert", {}, Exception("unique"))),
            rollback=AsyncMock(), commit=AsyncMock(), lock_interview=AsyncMock(return_value=winner),
        )
        self.assertIs(await InterviewStorage(repository).reserve_abandoned("id"), winner)
        repository.rollback.assert_awaited_once()
        repository.lock_interview.assert_awaited_once_with("id")

    async def test_concurrent_start_rejects_a_different_context(self):
        winner = SimpleNamespace(candidate_email="other@example.com", position_title="Backend")
        repository = SimpleNamespace(
            find_conversation=AsyncMock(side_effect=[None, winner]),
            add_conversation=AsyncMock(side_effect=IntegrityError("insert", {}, Exception("unique"))),
            rollback=AsyncMock(), commit=AsyncMock(),
        )
        with self.assertRaisesRegex(ValueError, "context"):
            await InterviewStorage(repository).ensure_conversation("id", "candidate@example.com", "Backend")

    async def test_unrelated_integrity_failure_is_not_treated_as_a_race(self):
        error = IntegrityError("insert", {}, Exception("other constraint"))
        repository = SimpleNamespace(
            add_conversation=AsyncMock(side_effect=error), rollback=AsyncMock(),
            lock_interview=AsyncMock(return_value=None), commit=AsyncMock(),
        )
        with self.assertRaises(IntegrityError) as caught:
            await InterviewStorage(repository).reserve_abandoned("id")
        self.assertIs(caught.exception, error)
