import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from voice_ai_service.app.models.domain import Candidate, Grade, Position
from voice_ai_service.app.models.dto import AudioEvaluationSchema
from voice_ai_service.app.services.voice_conversation.session import InterviewSession
from voice_ai_service.app.services.voice_conversation.question_bank_seed_v1 import starter_questions
from voice_ai_service.app.services.voice_conversation.question_bank_seed_v2 import additional_questions


def bank_rows():
    return starter_questions() + additional_questions()


class DialogueLLM:
    def __init__(self):
        self.calls = []
        self.audio_calls = 0
        self.audio_criteria = []
        self.transcript = "Use an index to avoid scanning every row."
        self.fail = False

    async def generate_response(self, args):
        self.calls.append(args)
        if self.fail:
            raise RuntimeError("Provider unavailable")
        if "Summarize a training" in args.prompt.system_prompt:
            return json.dumps({"summary": "Evidence based summary", "recommendation": "Study index tradeoffs",
                               "strengths": ["Reasoning"], "improvements": ["Completeness"]})
        return json.dumps({"question": f"Explain the tradeoffs of your previous answer, question {len(self.calls)}?"})

    async def evaluate_audio(self, *args):
        self.audio_calls += 1
        self.audio_criteria.append(args[3])
        return AudioEvaluationSchema(transcript=self.transcript, is_on_topic=True, score_percent=99,
                                     correctness=90, completeness=70, reasoning=80,
                                     comment="Correct reasoning with missing details")


def make_agent():
    llm = DialogueLLM()
    async def list_bank(focus, language):
        return [row.copy() for row in bank_rows() if row["focus"] == focus and row["language"] == language]
    db = type("DB", (), {"add_question_record": AsyncMock(), "list_question_bank": AsyncMock(side_effect=list_bank)})()
    agent = InterviewSession(llm, db)
    candidate = Candidate(name="Oksana", surname="Shevchenko", email="candidate@example.com",
                          phone_number="+380501234567", years_of_experience=3, tech_stack=["Python"], resume="")
    position = Position(title="Backend", description="Backend engineering", grade=Grade.MIDDLE,
                        department="Engineering", required_experience=2)
    return llm, db, agent, candidate, position


class AdaptiveDialogueTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.validator = patch("voice_ai_service.app.services.voice_conversation.session.validate_audio", AsyncMock())
        self.validator.start()
        self.addCleanup(self.validator.stop)

    async def test_graph_passes_restored_history_into_follow_up(self):
        llm, db, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "algorithms", "en", 42)
        await agent.ask(state)
        restored_agent = InterviewSession(llm, db)
        await restored_agent.answer(state, audio=b"audio", mime_type="audio/webm",
                                      answer_id=str(uuid.uuid4()), question_id=state["question_id"])
        history = json.loads(llm.calls[-1].prompt.user_prompt)["history"]
        self.assertEqual(history[-1], {"role": "user", "content": llm.transcript})
        self.assertEqual(history[0]["role"], "assistant")

    async def test_three_modes_two_languages_five_topics_with_two_follow_ups_and_duplicate(self):
        for focus in ("algorithms", "system-design", "behavioral"):
            for language in ("uk", "en"):
                with self.subTest(focus=focus, language=language):
                    llm, db, agent, candidate, position = make_agent()
                    state = agent.create_state(candidate, position, focus, language, 42)
                    await agent.ask(state)
                    self.assertEqual(len(state["bank_questions"]), 5)
                    self.assertEqual(len({q["key"] for q in state["bank_questions"]}), 5)
                    for i in range(15):
                        question_id, answer_id = state["question_id"], str(uuid.uuid4())
                        result = await agent.answer(state, b"valid-audio", "audio/webm", answer_id, question_id)
                        duplicate = await agent.answer(state, b"valid-audio", "audio/webm", answer_id, question_id)
                        self.assertEqual(duplicate, result)
                        if state["stage"] != "finished":
                            # After the main answer and the first follow-up comes a follow-up; then the next topic.
                            self.assertEqual(state["follow_up_count"], (i + 1) % 3)
                            self.assertEqual(state["clarification"], i % 3 != 2)
                            self.assertEqual(state["topic_index"], (i + 1) // 3)
                    self.assertEqual(state["stage"], "finished")
                    self.assertEqual(llm.audio_calls, 15)
                    self.assertEqual(db.add_question_record.await_count, 15)
                    feedback = state["feedback"]
                    self.assertEqual(feedback.overall_score, 80)
                    self.assertEqual(feedback.score_scale, 100)
                    self.assertFalse(feedback.partial)
                    self.assertEqual(len(feedback.questions), 15)
                    self.assertEqual([q["clarification"] for q in feedback.questions], [False, True, True] * 5)
                    self.assertEqual(len(feedback.topic_scores), 5)
                    self.assertIn(language == "uk" and "Ukrainian" or "English", llm.calls[0].prompt.user_prompt)

    async def test_second_follow_up_is_numbered_and_assessed_with_earlier_topic_answers(self):
        llm, _, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "algorithms", "en", 42)
        await agent.ask(state)
        llm.transcript = "Main answer with a hash set."
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        first_follow_up = llm.calls[-1].prompt.system_prompt
        self.assertIn("follow-up 1 of 2", first_follow_up)
        self.assertNotIn("Do not repeat an earlier follow-up", first_follow_up)
        llm.transcript = "First follow-up answer about memory."
        await agent.answer(state, b"b", "audio/webm", str(uuid.uuid4()), state["question_id"])
        second_follow_up = llm.calls[-1].prompt.system_prompt
        self.assertIn("follow-up 2 of 2", second_follow_up)
        self.assertIn("Do not repeat an earlier follow-up", second_follow_up)
        llm.transcript = "Second follow-up answer."
        await agent.answer(state, b"c", "audio/webm", str(uuid.uuid4()), state["question_id"])
        self.assertIn("Main answer with a hash set.", llm.audio_criteria[2])
        self.assertIn("First follow-up answer about memory.", llm.audio_criteria[2])
        self.assertEqual(state["topic_index"], 1)
        self.assertFalse(state["clarification"])
        self.assertIn("next main question", llm.calls[-1].prompt.system_prompt)

    async def test_session_persisted_under_three_by_one_contract_keeps_its_bounds(self):
        _, _, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "behavioral", "en", 42)
        for key in ("main_question_count", "follow_up_limit", "follow_up_count", "topic_answers"):
            del state[key]
        state["bank_questions"] = await agent.question_bank.select("behavioral", "en", "Backend", "middle", 3)
        await agent.ask(state)
        for _ in range(6):
            await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        self.assertEqual(state["stage"], "finished")
        self.assertFalse(state["feedback"].partial)
        self.assertEqual(len(state["feedback"].topic_scores), 3)

    async def test_skipping_a_follow_up_moves_to_the_next_main_question(self):
        _, _, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "system-design", "en", 42)
        await agent.ask(state)
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        state["attempt_id"], state["stage"] = str(uuid.uuid4()), "recording"
        await agent.skip(state)
        self.assertEqual(state["topic_index"], 1)
        self.assertFalse(state["clarification"])
        self.assertEqual(state["follow_up_count"], 0)

    async def test_stale_question_silence_and_reused_id_do_not_create_answer(self):
        llm, db, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "algorithms", "uk", 42)
        await agent.ask(state)
        with self.assertRaises(ValueError):
            await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), "stale")
        self.assertEqual(llm.audio_calls, 0)
        llm.transcript = ""
        with self.assertRaises(ValueError):
            await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        self.assertFalse(state["records"])
        self.assertEqual(db.add_question_record.await_count, 0)
        llm.transcript = "A real answer"
        question, answer = state["question_id"], str(uuid.uuid4())
        await agent.answer(state, b"a", "audio/webm", answer, question)
        with self.assertRaises(ValueError):
            await agent.answer(state, b"different", "audio/webm", answer, question)

    async def test_finish_without_answers_and_partial_finish_are_idempotent(self):
        _, _, agent, candidate, position = make_agent()
        empty = agent.create_state(candidate, position, "system-design", "uk", 42)
        await agent.finish(empty)
        self.assertEqual(empty["stage"], "abandoned")
        self.assertIsNone(empty["feedback"])
        state = agent.create_state(candidate, position, "system-design", "en", 43)
        await agent.ask(state)
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        await agent.finish(state)
        feedback = state["feedback"].model_dump()
        await agent.finish(state)
        self.assertEqual(state["feedback"].model_dump(), feedback)
        self.assertTrue(state["feedback"].partial)

    async def test_skipped_question_has_no_score_and_is_excluded_from_average(self):
        _, _, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "algorithms", "uk", 42)
        await agent.ask(state)
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        state["attempt_id"] = str(uuid.uuid4())
        state["stage"] = "recording"
        await agent.skip(state)
        await agent.finish(state)
        self.assertEqual(state["feedback"].overall_score, 80)
        self.assertIsNone(state["feedback"].questions[1]["score"])
        self.assertTrue(state["feedback"].questions[1]["skipped"])

    async def test_algorithms_require_oral_reasoning_and_both_complexities_in_questions_and_assessment(self):
        llm, _, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "algorithms", "uk", 42)
        await agent.ask(state)
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        for instruction in (llm.calls[0].prompt.system_prompt, llm.audio_criteria[0]):
            self.assertIn("time complexity", instruction)
            self.assertIn("space complexity", instruction)
            self.assertIn("Big O", instruction)
            self.assertIn("Do not require written code", instruction)

    async def test_system_design_passes_cv_and_role_to_questions_and_assessment(self):
        for title, stack, resume in (
            ("AI Engineer", ["Python", "PyTorch"], "Built an inference API for an image model."),
            ("Frontend", ["React", "TypeScript"], "Built browser applications with client-side caching."),
        ):
            with self.subTest(role=title):
                llm, _, agent, candidate, position = make_agent()
                candidate.tech_stack, candidate.resume = stack, resume
                position.title = title
                state = agent.create_state(candidate, position, "system-design", "en", 42)
                await agent.ask(state)
                payload = json.loads(llm.calls[0].prompt.user_prompt)
                self.assertEqual(payload["candidate"]["resume"], resume)
                self.assertEqual(payload["candidate"]["tech_stack"], stack)
                self.assertEqual(payload["position"]["title"], title)
                await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
                self.assertIn(resume, llm.audio_criteria[0])
                for instruction in (llm.calls[0].prompt.system_prompt, llm.audio_criteria[0]):
                    self.assertIn("budget", instruction)
                    self.assertIn("choice of services", instruction)
                    self.assertIn("frontend profile", instruction)
                    self.assertIn("AI or ML profile", instruction)

    async def test_new_dialogues_reject_removed_modes(self):
        llm, _, agent, candidate, position = make_agent()
        for focus in ("live-coding", "unknown"):
            with self.subTest(focus=focus), self.assertRaises(ValueError):
                agent.create_state(candidate, position, focus, "uk", 42)
        self.assertFalse(llm.calls)

    async def test_behavioral_questions_and_scoring_follow_the_candidate_context(self):
        llm, _, agent, candidate, position = make_agent()
        candidate.resume = "Built a small data project while studying."
        position.title = "Data Science"
        state = agent.create_state(candidate, position, "behavioral", "uk", 42)
        await agent.ask(state)
        first_prompt = llm.calls[-1].prompt.system_prompt
        self.assertIn("motivation", first_prompt)
        self.assertIn("teamwork", first_prompt)
        self.assertIn("personal projects", first_prompt)
        self.assertIn("Data Science", llm.calls[-1].prompt.user_prompt)
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        self.assertIn("clarification of the last answer", llm.calls[-1].prompt.system_prompt)
        self.assertIn("do not judge personality", llm.audio_criteria[0])
        self.assertIn(candidate.resume, llm.audio_criteria[0])

    async def test_main_question_uses_database_anchor_and_keeps_it_for_follow_up(self):
        llm, db, agent, candidate, position = make_agent()
        candidate.resume = "Built a model serving API."
        position.title = "Data Science"
        state = agent.create_state(candidate, position, "system-design", "en", 42)
        await agent.ask(state)
        db.list_question_bank.assert_awaited_once_with("system-design", "en")
        anchor = state["current_bank_question"].copy()
        prompt = json.loads(llm.calls[-1].prompt.user_prompt)
        self.assertEqual(prompt["question_bank_reference"]["question"], anchor["question"])
        self.assertIn(candidate.resume, llm.calls[-1].prompt.user_prompt)
        self.assertIn("without inventing their experience", llm.calls[-1].prompt.system_prompt)
        await agent.answer(state, b"a", "audio/webm", str(uuid.uuid4()), state["question_id"])
        self.assertEqual(state["records"][0]["bank_question"], anchor)
        self.assertEqual(json.loads(llm.calls[-1].prompt.user_prompt)["question_bank_reference"]["criteria"], anchor["criteria"])
        self.assertIn(anchor["criteria"], llm.audio_criteria[-1])
