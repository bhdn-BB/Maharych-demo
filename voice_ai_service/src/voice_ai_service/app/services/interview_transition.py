"""Request-scoped dialogue transitions executed under the conversation row lock."""

import copy
import uuid

from voice_ai_service.app.interfaces.database import InterviewStore
from voice_ai_service.app.services.interview_storage import InterviewStorage
from voice_ai_service.app.services.voice_conversation.session import InterviewSession
from voice_ai_service.app.services.voice_conversation.policy import SUPPORTED_FOCUSES


class DeferredRecords:
    """Collects question-record writes made while planning, to replay them under the row lock.

    Any other database access while planning is a bug: nothing may touch the database
    between releasing the lock and re-acquiring it.
    """

    def __init__(self):
        self.calls = []

    async def add_question_record(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def __getattr__(self, name):
        raise AssertionError(f"{name} must not access the database outside the row lock")


class InterviewTransition:
    def __init__(self, db: InterviewStore, session: InterviewSession):
        self.db = db
        self.storage = InterviewStorage(db)
        self.session = session

    async def finish_state(self, state):
        if state.get("scenario_version") != 2:
            raise ValueError("Legacy interviews are no longer supported")
        text = await self.session.finish(state)
        await self.storage.save(state)
        return text

    async def start(self, interview_id, candidate, position, scenario_version, language, focus):
        await self.storage.ensure_conversation(interview_id, candidate.email, position.title)
        conversation = await self.db.lock_interview(interview_id)
        state = self.storage.load(conversation)
        if state is None and conversation.stage == "abandoned":
            await self.db.rollback()
            state = {"stage": "abandoned", "conversation_history": []}
        elif state is None:
            if scenario_version != 2 or language not in {"uk", "en"} or focus not in SUPPORTED_FOCUSES:
                raise ValueError("Unsupported interview scenario, language or focus")
            state = self.session.create_state(candidate, position, focus, language, conversation.id)
            await self.session.ask(state)
            await self.storage.save(state)
        else:
            if state.get("scenario_version") != 2:
                raise ValueError("Legacy interviews are no longer supported")
            if state.get("stage") == "recording":
                await self.session.skip(state)
                await self.storage.save(state)
            else:
                await self.db.rollback()
        return state, self.session.current_text(state)

    @staticmethod
    def _fingerprint(state):
        """The parts of the state an in-flight answer depends on; they must not change meanwhile."""
        return (state.get("stage"), state.get("attempt_id"), state.get("question_id"),
                state.get("topic_index"), len(state.get("records", ())), tuple(state.get("processed_answers", ())))

    async def apply(self, interview_id, command, question_id, answer_id, audio, mime_type):
        conversation = await self.db.lock_interview(interview_id)
        state = self.storage.load(conversation)
        transcript = ""
        if command == "replay_audio":
            if question_id != state.get("question_id", ""):
                raise ValueError("Question changed; reconnect to restore it")
            await self.db.rollback()
            text = ""
        elif command == "finish":
            text = await self.finish_state(state)
        elif command == "start_recording":
            answer_id = str(uuid.UUID(answer_id))
            if state.get("stage") != "questioning" or question_id != state.get("question_id"):
                raise ValueError("Recording attempt is unavailable")
            state["attempt_id"] = answer_id
            state["stage"] = "recording"
            await self.storage.save(state)
            text = ""
        elif command == "skip_recording":
            if state.get("stage") != "recording" or question_id != state.get("question_id") or answer_id != state.get("attempt_id"):
                raise ValueError("Recording attempt is unavailable")
            text = await self.session.skip(state)
            await self.storage.save(state)
        elif command == "release_recording":
            # Internal: the AI provider was unavailable (quota, outage), not the candidate's
            # recording. Return the reserved attempt so the same question can be answered again.
            if state.get("stage") != "recording" or question_id != state.get("question_id") or answer_id != state.get("attempt_id"):
                raise ValueError("Recording attempt is unavailable")
            state["stage"] = "questioning"
            state["attempt_id"] = ""
            await self.storage.save(state)
            text = ""
        elif audio:
            if state.get("scenario_version") == 2:
                answer_id = str(uuid.UUID(answer_id))
                if state.get("stage") != "recording" or answer_id != state.get("attempt_id") or question_id != state.get("question_id"):
                    raise ValueError("Recording attempt is unavailable")
                planned = None
                if answer_id not in state["processed_answers"]:
                    # Every LLM call (audio evaluation, next question or summary) must hold neither the
                    # row lock nor a pooled connection: release both, plan the whole answer on a copy
                    # of the state with record writes deferred, then re-lock and verify the stored
                    # state still matches before applying the plan.
                    base = self._fingerprint(state)
                    planned = copy.deepcopy(state)
                    await self.db.rollback()
                    deferred = DeferredRecords()
                    transcript, text = await self.session.with_db(deferred).answer(
                        planned, audio=audio, mime_type=mime_type,
                        answer_id=answer_id, question_id=question_id,
                    )
                    conversation = await self.db.lock_interview(interview_id)
                    state = self.storage.load(conversation)
                    if answer_id in state["processed_answers"]:
                        planned = None  # a concurrent request applied it first; replay through the stored state
                    elif self._fingerprint(state) != base:
                        raise ValueError("Recording attempt is unavailable")
                    else:
                        for args, kwargs in deferred.calls:
                            await self.db.add_question_record(*args, **kwargs)
                        state = planned
                if planned is None:
                    transcript, text = await self.session.answer(
                        state, audio=audio, mime_type=mime_type,
                        answer_id=answer_id, question_id=question_id,
                    )
            else:
                raise ValueError("Legacy interviews are no longer supported")
            await self.storage.save(state)
        else:
            raise ValueError("Expected audio or a supported command")
        return state, transcript, text
