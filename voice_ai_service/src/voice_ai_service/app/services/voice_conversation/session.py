"""Bounded adaptive oral interview. State and records commit in one transaction."""
import hashlib
import uuid

from voice_ai_service.app.interfaces.database import QuestionRecordWriter
from voice_ai_service.app.interfaces.llm import DialogueLLM
from voice_ai_service.app.models.domain import (
    Candidate, InterviewFeedback, InterviewStage, Position, QuestionType, Topic, TopicScore,
)
from voice_ai_service.app.models.state import InterviewState
from voice_ai_service.app.services.audio_validation import validate_audio
from voice_ai_service.app.services.question_bank import QuestionBankService
from voice_ai_service.app.services.prompts import load_prompt
from voice_ai_service.app.services.voice_conversation.generation import InterviewGeneration
from voice_ai_service.app.services.voice_conversation.policy import (
    SUPPORTED_FOCUSES, assessment_criteria, interview_policy, question_instruction,
)

MAIN_QUESTION_COUNT = 5
FOLLOW_UP_LIMIT = 2
# Sessions persisted before the 5x2 contract keep the bounds they started with.
LEGACY_MAIN_QUESTION_COUNT = 3
LEGACY_FOLLOW_UP_LIMIT = 1


def main_question_count(state) -> int:
    return state.get("main_question_count", LEGACY_MAIN_QUESTION_COUNT)


def follow_up_limit(state) -> int:
    return state.get("follow_up_limit", LEGACY_FOLLOW_UP_LIMIT)


def follow_up_count(state) -> int:
    return state.get("follow_up_count", 1 if state.get("clarification") else 0)


class InterviewSession:
    """Apply interview rules to the state held by the transaction owner."""

    def __init__(self, llm: DialogueLLM, db: QuestionRecordWriter) -> None:
        self.llm = llm
        self.db = db
        self.question_bank = QuestionBankService(db)
        self.generation = InterviewGeneration(llm)

    def with_db(self, db: QuestionRecordWriter) -> "InterviewSession":
        """Same rules and LLM, different record writer (used to plan an answer outside the row lock)."""
        return InterviewSession(self.llm, db)

    @staticmethod
    def _initial_state(
        candidate: Candidate,
        position: Position,
        conversation_id: int,
    ) -> InterviewState:
        return InterviewState(
            session_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            stage=InterviewStage.GREETING.value,
            candidate=candidate,
            position=position,
            current_topic=None,
            topic_index=0,
            completed_topics=[],
            warning_count=0,
            input_message=None,
            audio_evaluation=None,
            last_audio_sha256=None,
            last_transcript=None,
            eval_score=None,
            eval_comment=None,
            conversation_history=[],
            evaluations=[],
            feedback=None,
            error=None,
        )

    def create_state(
        self, candidate: Candidate, position: Position, focus: str, language: str, conversation_id: int,
    ) -> InterviewState:
        if focus not in SUPPORTED_FOCUSES or language not in {"uk", "en"}:
            raise ValueError("Invalid dialogue language or focus")
        state = self._initial_state(candidate, position, conversation_id)
        state.update(
            scenario_version=2, language=language, focus=focus, records=[], processed_answers={},
            clarification=False, first_answer="", main_question="", question_id="", attempt_id="",
            main_question_count=MAIN_QUESTION_COUNT, follow_up_limit=FOLLOW_UP_LIMIT,
            follow_up_count=0, topic_answers=[],
        )
        return state

    @staticmethod
    def context(state: InterviewState) -> dict:
        return {
            "language": "Ukrainian" if state["language"] == "uk" else "English",
            "focus": state["focus"], "position": state["position"].model_dump(mode="json"),
            "candidate": {k: v for k, v in state["candidate"].model_dump(mode="json").items()
                          if k in {"years_of_experience", "tech_stack", "resume"}},
            "history": state["conversation_history"],
        }

    async def ask(self, state: InterviewState, clarification: bool = False) -> str:
        if not clarification:
            if not state.get("bank_questions"):
                level = state["position"].grade.value
                state["bank_questions"] = await self.question_bank.select(
                    state["focus"], state["language"], state["position"].title, level,
                    main_question_count(state),
                )
            state["current_bank_question"] = state["bank_questions"][state["topic_index"]]
        follow_up = follow_up_count(state) + 1 if clarification else 0
        reference = state.get("current_bank_question")
        instruction = question_instruction(state["focus"], state["topic_index"], clarification, bool(reference),
                                           follow_up, follow_up_limit(state))
        context = self.context(state)
        if reference:
            context["question_bank_reference"] = {"question": reference["question"], "criteria": reference["criteria"]}
        result = await self.generation.question(instruction, context)
        state["question_id"] = str(uuid.uuid4())
        state["attempt_id"] = ""
        state["clarification"] = clarification
        state["follow_up_count"] = follow_up
        if not clarification:
            state["main_question"] = result.question
            state["first_answer"] = ""
            state["topic_answers"] = []
        state["current_topic"] = Topic(index=state["topic_index"] + 1, main_question=result.question)
        state["stage"] = "questioning"
        state["conversation_history"].append({"role": "assistant", "content": result.question})
        return result.question

    async def evaluate(self, state: InterviewState, audio: bytes, mime_type: str):
        """Transcribe and score one answer. Read-only: needs no database access or row lock."""
        await validate_audio(audio, mime_type)
        criteria = assessment_criteria(state, self.context(state))
        return await self.llm.evaluate_audio(audio, mime_type, state["current_topic"].main_question, criteria)

    async def answer(
        self, state: InterviewState, audio: bytes, mime_type: str, answer_id: str, question_id: str,
        evaluation=None,
    ) -> tuple[str, str]:
        """Apply an answer; ``evaluation`` may be precomputed by ``evaluate`` outside the row lock."""
        previous = state["processed_answers"].get(answer_id)
        if previous:
            if previous["sha256"] != hashlib.sha256(audio).hexdigest() or previous["question_id"] != question_id:
                raise ValueError("Answer ID was already used for different input")
            return previous["transcript"], self.current_text(state)
        if state["stage"] in {"finished", "abandoned"}:
            raise ValueError("Interview already ended")
        if not answer_id or question_id != state["question_id"]:
            raise ValueError("Answer does not match the current question")
        reference = state.get("current_bank_question")
        result = evaluation if evaluation is not None else await self.evaluate(state, audio, mime_type)
        transcript = result.transcript.strip()
        if not transcript:
            raise ValueError("No intelligible speech detected")
        dimensions = (result.correctness, result.completeness, result.reasoning)
        if any(value is None for value in dimensions):
            raise RuntimeError("AI did not return the required scoring dimensions")
        score = round(sum(dimensions) / 3)
        index = state["topic_index"] + 1
        record = {
            "topic_index": index, "question_id": question_id, "answer_id": answer_id,
            "question": state["current_topic"].main_question, "answer": transcript,
            "score": score if result.is_on_topic else 0, "correctness": result.correctness,
            "completeness": result.completeness, "reasoning": result.reasoning,
            "comment": result.comment, "clarification": state["clarification"],
        }
        if reference:
            record["bank_question"] = reference.copy()
        state["records"].append(record)
        state["conversation_history"].append({"role": "user", "content": transcript})
        await self.db.add_question_record(
            state["conversation_id"], index, record["question"], "general", transcript,
            record["score"], result.comment,
        )
        # A fixed number of follow-ups per main question, including after off-topic answers.
        if not state["clarification"]:
            state["first_answer"] = transcript
        state["topic_answers"] = [*state.get("topic_answers", []), transcript]
        if follow_up_count(state) < follow_up_limit(state):
            response = await self.ask(state, clarification=True)
        else:
            state["topic_index"] += 1
            response = await self.finish(state) if state["topic_index"] >= main_question_count(state) else await self.ask(state)
        state["processed_answers"][answer_id] = {
            "transcript": transcript, "sha256": hashlib.sha256(audio).hexdigest(), "question_id": question_id,
        }
        return transcript, response

    async def skip(self, state: InterviewState) -> str:
        """Record a consumed attempt without assigning a score."""
        if state["stage"] != "skipped":
            record = {"topic_index": state["topic_index"] + 1,
                      "question_id": state["question_id"], "answer_id": state.get("attempt_id", ""),
                      "question": state["current_topic"].main_question, "answer": "",
                      "score": None, "comment": "Skipped", "clarification": state["clarification"],
                      "skipped": True}
            if state.get("current_bank_question"):
                record["bank_question"] = state["current_bank_question"].copy()
            state["records"].append(record)
            await self.db.add_question_record(state["conversation_id"], record["topic_index"],
                                              record["question"], "general", "", None, "Skipped")
            state["stage"] = "skipped"
        state["topic_index"] += 1
        return await self.finish(state) if state["topic_index"] >= main_question_count(state) else await self.ask(state)

    async def finish(self, state: InterviewState) -> str:
        if state["stage"] in {"finished", "abandoned"}:
            return self.current_text(state)
        scored = [record for record in state["records"] if record.get("score") is not None]
        if not scored:
            state["stage"] = "abandoned"
            return "Співбесіду перервано без відповідей." if state["language"] == "uk" else "Interview ended without answers."
        summary = await self.generation.summary(
            load_prompt("summary")
            + interview_policy(state["focus"]),
            {**self.context(state), "records": state["records"]})
        latest = {r["topic_index"]: r for r in scored}
        state["feedback"] = InterviewFeedback(
            score_scale=100, partial=state["topic_index"] < main_question_count(state) or len(scored) != len(state["records"]), language=state["language"],
            overall_score=round(sum(r["score"] for r in latest.values()) / len(latest), 1),
            summary=summary.summary, recommendation=summary.recommendation,
            top_strengths=summary.strengths, top_weaknesses=summary.improvements,
            questions=state["records"],
            topic_scores=[TopicScore(topic_index=i, score=r["score"], question_type=QuestionType.GENERAL,
                                     comment=r["comment"]) for i, r in sorted(latest.items())],
        )
        state["stage"] = "finished"
        state["conversation_history"].append({"role": "assistant", "content": summary.summary})
        return summary.summary

    @staticmethod
    def current_text(state: InterviewState) -> str:
        return next((m["content"] for m in reversed(state["conversation_history"])
                     if m["role"] == "assistant"), "")
