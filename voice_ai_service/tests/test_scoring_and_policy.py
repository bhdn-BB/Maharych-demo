"""Unit tests for interview scoring, session bounds and prompt policy composition.

These cover rules that the live run (lab 6) showed to matter for users:
how a topic score is chosen when follow-ups exist, when a report is partial,
when a session is abandoned, and which instructions reach Gemini.
"""
import json
import unittest

from voice_ai_service.app.services.voice_conversation import policy
from voice_ai_service.app.services.voice_conversation.session import (
    FOLLOW_UP_LIMIT,
    LEGACY_FOLLOW_UP_LIMIT,
    LEGACY_MAIN_QUESTION_COUNT,
    follow_up_count,
    follow_up_limit,
    main_question_count,
)
from voice_ai_service.app.services.prompts import load_prompt

from tests.test_adaptive_dialogue import make_agent


def record(topic, score, clarification=False, skipped=False):
    return {"topic_index": topic, "question_id": f"q{topic}-{int(clarification)}", "answer_id": "a",
            "question": f"Question {topic}", "answer": "" if skipped else "answer",
            "score": None if skipped else score, "comment": "Skipped" if skipped else "ok",
            "clarification": clarification, **({"skipped": True} if skipped else {})}


class ScoringTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.llm, self.db, self.agent, candidate, position = make_agent()
        self.state = self.agent.create_state(candidate, position, "behavioral", "en", conversation_id=1)

    def summary_calls(self):
        return [c for c in self.llm.calls if "Summarize a training" in c.prompt.system_prompt]

    async def test_topic_score_is_final_cumulative_follow_up_score(self):
        # Topic 1: strong main answer re-assessed to 0 after a repeated follow-up (seen live).
        self.state["records"] = [record(1, 100), record(1, 0, clarification=True), record(2, 60)]
        self.state["topic_index"] = 2
        await self.agent.finish(self.state)
        feedback = self.state["feedback"]
        self.assertEqual([t.score for t in feedback.topic_scores], [0, 60])
        self.assertEqual(feedback.overall_score, 30.0)
        self.assertEqual(feedback.score_scale, 100)

    async def test_overall_score_rounded_to_one_decimal(self):
        self.state["records"] = [record(1, 70), record(2, 71), record(3, 71)]
        self.state["topic_index"] = 3
        await self.agent.finish(self.state)
        self.assertEqual(self.state["feedback"].overall_score, 70.7)

    async def test_ending_early_marks_report_partial(self):
        self.state["records"] = [record(1, 80)]
        self.state["topic_index"] = 1
        await self.agent.finish(self.state)
        self.assertTrue(self.state["feedback"].partial)
        self.assertEqual(self.state["stage"], "finished")

    async def test_complete_interview_is_not_partial(self):
        self.state["records"] = [record(i, 50 + i) for i in range(1, 6)]
        self.state["topic_index"] = 5
        await self.agent.finish(self.state)
        self.assertFalse(self.state["feedback"].partial)
        self.assertEqual(self.state["feedback"].overall_score, 53.0)

    async def test_skipped_question_makes_report_partial_and_is_not_scored(self):
        self.state["records"] = [record(1, 90), record(2, None, skipped=True), record(3, 70),
                                 record(4, 70), record(5, 70)]
        self.state["topic_index"] = 5
        await self.agent.finish(self.state)
        feedback = self.state["feedback"]
        self.assertTrue(feedback.partial)
        self.assertEqual([t.topic_index for t in feedback.topic_scores], [1, 3, 4, 5])
        self.assertEqual(feedback.overall_score, 75.0)

    async def test_no_scored_answers_abandons_without_report_or_model_call(self):
        self.state["records"] = [record(1, None, skipped=True)]
        text = await self.agent.finish(self.state)
        self.assertEqual(self.state["stage"], "abandoned")
        self.assertIsNone(self.state["feedback"])
        self.assertEqual(text, "Interview ended without answers.")
        self.assertEqual(self.summary_calls(), [])

    async def test_ukrainian_abandon_message(self):
        self.state["language"] = "uk"
        text = await self.agent.finish(self.state)
        self.assertEqual(self.state["stage"], "abandoned")
        self.assertEqual(text, "Співбесіду перервано без відповідей.")

    async def test_finish_is_idempotent(self):
        self.state["records"] = [record(1, 40)]
        self.state["topic_index"] = 1
        first = await self.agent.finish(self.state)
        second = await self.agent.finish(self.state)
        self.assertEqual(first, second)
        self.assertEqual(len(self.summary_calls()), 1, "a finished interview must not be summarised twice")

    async def test_summary_cannot_override_numeric_scores(self):
        self.state["records"] = [record(1, 42)]
        self.state["topic_index"] = 1
        await self.agent.finish(self.state)
        self.assertEqual(self.state["feedback"].overall_score, 42.0)
        self.assertEqual(self.state["feedback"].summary, "Evidence based summary")


class SessionBoundsTest(unittest.TestCase):
    def test_legacy_sessions_keep_three_by_one(self):
        self.assertEqual(main_question_count({}), LEGACY_MAIN_QUESTION_COUNT)
        self.assertEqual(follow_up_limit({}), LEGACY_FOLLOW_UP_LIMIT)

    def test_new_sessions_use_five_by_two(self):
        _, _, agent, candidate, position = make_agent()
        state = agent.create_state(candidate, position, "algorithms", "uk", conversation_id=7)
        self.assertEqual((main_question_count(state), follow_up_limit(state)), (5, FOLLOW_UP_LIMIT))
        self.assertEqual(main_question_count(state) * (1 + follow_up_limit(state)), 15,
                         "the v2 contract bounds a session to fifteen answers")

    def test_follow_up_count_inferred_for_legacy_state(self):
        self.assertEqual(follow_up_count({"clarification": True}), 1)
        self.assertEqual(follow_up_count({"clarification": False}), 0)
        self.assertEqual(follow_up_count({"clarification": True, "follow_up_count": 2}), 2)

    def test_create_state_rejects_unknown_focus_or_language(self):
        _, _, agent, candidate, position = make_agent()
        for focus, language in (("frontend", "en"), ("behavioral", "de")):
            with self.subTest(focus=focus, language=language):
                with self.assertRaises(ValueError):
                    agent.create_state(candidate, position, focus, language, conversation_id=1)


class PolicyCompositionTest(unittest.TestCase):
    def test_unknown_focus_rejected(self):
        with self.assertRaises(ValueError):
            policy.interview_policy("frontend")

    def test_goal_index_is_clamped_to_available_goals(self):
        for focus in policy.SUPPORTED_FOCUSES:
            key = focus.replace("-", "_")
            with self.subTest(focus=focus):
                self.assertEqual(policy.question_goal(focus, -3), load_prompt(f"goal_{key}_0"))
                self.assertEqual(policy.question_goal(focus, 99),
                                 load_prompt(f"goal_{key}_{policy.TOPIC_GOAL_COUNT - 1}"))

    def test_main_question_uses_goal_not_follow_up_text(self):
        text = policy.question_instruction("algorithms", 2, clarification=False, has_reference=False)
        self.assertIn(policy.question_goal("algorithms", 2), text)
        self.assertNotIn(load_prompt("question_clarification").split("{")[0].strip(), text)
        self.assertNotIn(load_prompt("question_anchor"), text)

    def test_second_follow_up_adds_no_repeat_rule_and_anchor(self):
        first = policy.question_instruction("behavioral", 0, True, False, follow_up=1, follow_up_limit=2)
        second = policy.question_instruction("behavioral", 0, True, True, follow_up=2, follow_up_limit=2)
        self.assertNotIn(load_prompt("question_clarification_next"), first)
        self.assertIn(load_prompt("question_clarification_next"), second)
        self.assertIn(load_prompt("question_anchor"), second)

    def test_assessment_includes_earlier_answers_without_ascii_escaping(self):
        state = {"focus": "behavioral", "clarification": True,
                 "topic_answers": ["Я розв'язав конфлікт у команді"], "current_bank_question": None}
        text = policy.assessment_criteria(state, {"language": "uk"})
        self.assertTrue(text.startswith(load_prompt("behavioral_assessment")))
        self.assertIn(load_prompt("assessment_clarification"), text)
        self.assertIn("Я розв'язав конфлікт у команді", text, "Ukrainian answers must reach the model readable")

    def test_assessment_adds_bank_criteria_only_when_anchored(self):
        base = {"focus": "algorithms", "clarification": False, "first_answer": ""}
        plain = policy.assessment_criteria(dict(base), {})
        anchored = policy.assessment_criteria({**base, "current_bank_question": {"criteria": ["O(n log n)"]}}, {})
        self.assertNotIn(load_prompt("behavioral_assessment"), plain)
        self.assertNotIn(load_prompt("assessment_anchor"), plain)
        self.assertIn(load_prompt("assessment_anchor") + json.dumps(["O(n log n)"]), anchored)


if __name__ == "__main__":
    unittest.main()
