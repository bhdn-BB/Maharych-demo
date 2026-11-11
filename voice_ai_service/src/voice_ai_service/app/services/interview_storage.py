"""Interview persistence policy around a request-scoped repository."""
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError

from voice_ai_service.app.models.state import InterviewState


class InterviewStorage:
    _state_adapter = TypeAdapter(InterviewState)

    def __init__(self, repository):
        self.repository = repository

    async def ensure_conversation(self, interview_id, candidate_email, position_title):
        conversation = await self.repository.find_conversation(interview_id)
        if conversation is None:
            try:
                conversation = await self.repository.add_conversation(
                    interview_id=interview_id, candidate_email=candidate_email,
                    position_title=position_title,
                )
                await self.repository.commit()
            except IntegrityError:
                await self.repository.rollback()
                conversation = await self.repository.find_conversation(interview_id)
                if conversation is None:
                    raise
        if conversation.candidate_email != candidate_email or conversation.position_title != position_title:
            raise ValueError("interview context does not match its existing conversation")
        return conversation

    async def reserve_abandoned(self, interview_id):
        # The unique interview ID arbitrates a concurrent start or finish.
        conflict = None
        try:
            await self.repository.add_conversation(interview_id=interview_id, candidate_email="",
                                                   position_title="", stage="abandoned")
            await self.repository.commit()
        except IntegrityError as exc:
            conflict = exc
            await self.repository.rollback()
        conversation = await self.repository.lock_interview(interview_id)
        if conversation is None:
            if conflict is not None:
                raise conflict
            raise RuntimeError("Unable to reserve the interview")
        return conversation

    async def mark_abandoned(self, conversation):
        conversation.stage = "abandoned"
        await self.repository.update_conversation(conversation)
        await self.repository.commit()

    def load(self, conversation):
        if conversation.state_json is None:
            return None
        return self._state_adapter.validate_python(conversation.state_json)

    async def save(self, state):
        conversation = await self.repository.get_conversation(state["conversation_id"])
        if conversation is None:
            raise ValueError("AI conversation no longer exists")
        conversation.session_id = state["session_id"]
        conversation.stage = state["stage"]
        conversation.state_json = self._state_adapter.dump_python(state, mode="json")
        feedback = state.get("feedback")
        if feedback is not None:
            conversation.feedback_json = feedback.model_dump(mode="json")
            conversation.overall_score = feedback.overall_score
            conversation.recommendation = feedback.recommendation
            if conversation.interview_id and not await self.repository.get_outbox(conversation.interview_id):
                await self.repository.add_outbox(conversation.interview_id)
        await self.repository.update_conversation(conversation)
        await self.repository.commit()
