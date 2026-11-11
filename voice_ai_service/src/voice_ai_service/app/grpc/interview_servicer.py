"""Durable interview stream: reload under a row lock for every state transition."""
import asyncio
import logging
import uuid
import time

from voice_ai_service.app.core.dependencies import db_session, get_agent
from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2 as pb
from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2_grpc
from voice_ai_service.app.grpc.mappers import options_to_candidate, options_to_position
from voice_ai_service.app.repositories.llm.gemini_client import LLMProviderError
from voice_ai_service.app.services.audio_validation import SilentAudioError
from voice_ai_service.app.services.tts import synthesize
from voice_ai_service.app.services.interview_transition import InterviewTransition
from voice_ai_service.app.services.voice_conversation.session import main_question_count

logger = logging.getLogger(__name__)

PROVIDER_UNAVAILABLE = ("The AI service is temporarily unavailable (rate limit or outage), so your answer "
                        "was not evaluated. The question is kept — record your answer again in a minute.")
ANSWER_NOT_UNDERSTOOD = ("Your answer could not be processed (no clear speech was detected), "
                         "so this question was skipped without a score.")


NO_SPEECH = ("We could not hear you — the recording was silent (is the microphone muted or the wrong one "
             "selected?). This question was skipped without a score.")


def _causes(exc: BaseException):
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def provider_outage(exc: BaseException) -> bool:
    """True when a retryable Gemini failure (429, 5xx, timeout) is anywhere in the cause chain."""
    return any(isinstance(e, LLMProviderError) and e.retryable for e in _causes(exc))


def retry_message(exc: BaseException) -> str | None:
    """Failures that are not the candidate's answer (AI outage): keep the question and say why."""
    return PROVIDER_UNAVAILABLE if provider_outage(exc) else None


def skip_message(exc: BaseException) -> str:
    """Why an answer was skipped: a silent recording, or speech that could not be processed."""
    return NO_SPEECH if any(isinstance(e, SilentAudioError) for e in _causes(exc)) else ANSWER_NOT_UNDERSTOOD


def event(kind, state, answer_id="", **kwargs):
    topic = state.get("current_topic")
    return pb.AudioStreamResponse(type=kind, stage=state["stage"],
        current_question=topic.index if topic else 0,
        total_questions=main_question_count(state) if state.get("scenario_version") == 2 else 1,
        question_id=state.get("question_id", ""), answer_id=answer_id,
        event_id=str(uuid.uuid4()), **kwargs)


async def audio_events(state, voice_id=""):
    if state["stage"] != "questioning":
        return
    try:
        audio = await synthesize(state["current_topic"].main_question, state.get("language", "en"), voice_id)
        yield event(pb.AudioStreamResponse.AI_AUDIO, state, ai_audio_data=audio, audio_mime_type="audio/mpeg")
    except Exception:
        logger.warning("Question speech synthesis unavailable")
        yield event(pb.AudioStreamResponse.ERROR, state,
                    error="Could not generate speech. Read the question or retry audio.")


class AIServiceServicer(ai_service_pb2_grpc.AIServiceServicer):
    async def StreamInterview(self, request_iterator, context):
        interview_id, state = None, None
        voice_id = ""
        mime_type = "audio/webm"
        async for request in request_iterator:
            starting = state is None
            started_at = time.monotonic()
            try:
                async with asyncio.timeout(60):
                    async with db_session() as db:
                        agent = await get_agent(db)
                        transcript = ""
                        transition = InterviewTransition(db, agent)
                        if starting:
                            if not request.HasField("options"):
                                raise ValueError("First message must contain startup options")
                            opts = request.options
                            voice_id = opts.voice_id
                            interview_id = str(uuid.UUID(opts.interview_id))
                            mime_type = opts.metadata.mime_type or "audio/webm"
                            candidate, position = options_to_candidate(opts), options_to_position(opts)
                            state, text = await transition.start(
                                interview_id, candidate, position, opts.scenario_version,
                                opts.language, opts.focus,
                            )
                        else:
                            state, transcript, text = await transition.apply(
                                interview_id, request.command, request.question_id, request.answer_id,
                                bytes(request.audio_data), mime_type,
                            )
                logger.info("Interview transition committed interview_id=%s answer_id=%s processing_ms=%d",
                            interview_id, request.answer_id, round((time.monotonic() - started_at) * 1000))
                if transcript:
                    transcription_event = event(pb.AudioStreamResponse.TRANSCRIPTION, state, request.answer_id, transcription=transcript)
                    transcription_event.question_id = request.question_id
                    yield transcription_event
                if text:
                    yield event(pb.AudioStreamResponse.AI_TEXT, state, request.answer_id, ai_text=text)
                if state["stage"] in {"finished", "abandoned"}:
                    yield event(pb.AudioStreamResponse.INTERVIEW_FINISHED, state, request.answer_id)
                elif state["stage"] == "questioning":
                    yield event(pb.AudioStreamResponse.STAGE_UPDATE, state, request.answer_id)
                    async for message in audio_events(state, voice_id):
                        yield message
                else:
                    yield event(pb.AudioStreamResponse.STAGE_UPDATE, state, request.answer_id)
            except Exception as exc:
                logger.warning("Interview processing failed for interview_id=%s", interview_id, exc_info=True)
                if not starting and request.audio_data and retry_message(exc):
                    try:
                        async with asyncio.timeout(60), db_session() as db:
                            transition = InterviewTransition(db, await get_agent(db))
                            state, _, _ = await transition.apply(interview_id, "release_recording", request.question_id, request.answer_id, b"", mime_type)
                        yield pb.AudioStreamResponse(type=pb.AudioStreamResponse.ERROR, answer_id=request.answer_id,
                                                     error=retry_message(exc))
                        yield event(pb.AudioStreamResponse.STAGE_UPDATE, state)
                        continue
                    except Exception:
                        logger.warning("Could not release attempt after provider outage interview_id=%s", interview_id, exc_info=True)
                elif not starting and request.audio_data:
                    try:
                        async with asyncio.timeout(60), db_session() as db:
                            transition = InterviewTransition(db, await get_agent(db))
                            state, _, text = await transition.apply(interview_id, "skip_recording", request.question_id, request.answer_id, b"", mime_type)
                        yield pb.AudioStreamResponse(type=pb.AudioStreamResponse.ERROR, answer_id=request.answer_id,
                                                     error=skip_message(exc))
                        if text:
                            yield event(pb.AudioStreamResponse.AI_TEXT, state, ai_text=text)
                        if state["stage"] in {"finished", "abandoned"}:
                            yield event(pb.AudioStreamResponse.INTERVIEW_FINISHED, state)
                        else:
                            yield event(pb.AudioStreamResponse.STAGE_UPDATE, state)
                            async for message in audio_events(state, voice_id):
                                yield message
                        continue
                    except Exception:
                        logger.warning("Could not advance after failed recording interview_id=%s", interview_id, exc_info=True)
                yield pb.AudioStreamResponse(type=pb.AudioStreamResponse.ERROR, answer_id=request.answer_id,
                    error="Recording or processing failed. Reconnect to skip this question.")
                if starting:
                    state = None
