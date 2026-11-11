"""Coordinate interview finalization and retrieval of saved reports."""
import asyncio
import uuid

from voice_ai_service.app.services.interview_transition import InterviewTransition
from voice_ai_service.app.services.interview_storage import InterviewStorage


class InvalidInterviewID(ValueError):
    pass


class ReportNotFound(LookupError):
    pass


def normalize_interview_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise InvalidInterviewID("Invalid interview ID") from exc


class InterviewLifecycleService:
    def __init__(self, store, agent_factory):
        self.store = store
        self.storage = InterviewStorage(store)
        self.agent_factory = agent_factory

    async def finish(self, interview_id: str) -> str:
        interview_id = normalize_interview_id(interview_id)
        async with asyncio.timeout(60):
            conversation = await self.store.lock_interview(interview_id)
            if conversation is None:
                conversation = await self.storage.reserve_abandoned(interview_id)
            state = self.storage.load(conversation)
            if state is None:
                await self.storage.mark_abandoned(conversation)
                return "abandoned"
            agent = await self.agent_factory(self.store)
            await InterviewTransition(self.store, agent).finish_state(state)
            return state["stage"]

    async def feedback(self, interview_id: str):
        result = await self.store.find_feedback_by_interview_id(normalize_interview_id(interview_id))
        if result is None:
            raise ReportNotFound("Feedback not available")
        return result

    async def report_pdf(self, interview_id: str):
        result = await self.store.find_report_pdf_by_interview_id(normalize_interview_id(interview_id))
        if result is None:
            raise ReportNotFound("PDF report not ready")
        return result
