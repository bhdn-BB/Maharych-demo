"""Compose the prompt policies for questions and answer assessment."""

import json

from voice_ai_service.app.services.prompts import load_prompt

SUPPORTED_FOCUSES = frozenset({"algorithms", "system-design", "behavioral"})
TOPIC_GOAL_COUNT = 5


def interview_policy(focus: str) -> str:
    if focus not in SUPPORTED_FOCUSES:
        raise ValueError("Unsupported interview focus")
    return load_prompt("policy_" + focus.replace("-", "_")) + " "


def question_goal(focus: str, topic_index: int) -> str:
    interview_policy(focus)
    prompt_focus = focus.replace("-", "_")
    return load_prompt(f"goal_{prompt_focus}_{min(max(topic_index, 0), TOPIC_GOAL_COUNT - 1)}")


def question_instruction(
    focus: str, topic_index: int, clarification: bool, has_reference: bool,
    follow_up: int = 1, follow_up_limit: int = 1,
) -> str:
    instruction = load_prompt("question_base") + interview_policy(focus)
    if clarification:
        instruction += load_prompt("question_clarification").format(number=follow_up, limit=follow_up_limit)
        if follow_up > 1:
            instruction += load_prompt("question_clarification_next")
    else:
        instruction += load_prompt("question_main") + question_goal(focus, topic_index)
    if has_reference:
        instruction += load_prompt("question_anchor")
    return instruction


def assessment_criteria(state: dict, context: dict) -> str:
    criteria = load_prompt("behavioral_assessment") if state["focus"] == "behavioral" else ""
    criteria += load_prompt("assessment") + interview_policy(state["focus"])
    criteria += load_prompt("assessment_context") + json.dumps(context, ensure_ascii=False, default=str)
    if state["clarification"]:
        earlier = state.get("topic_answers") or [state["first_answer"]]
        criteria += load_prompt("assessment_clarification") + json.dumps(earlier, ensure_ascii=False)
    reference = state.get("current_bank_question")
    if reference:
        criteria += load_prompt("assessment_anchor") + json.dumps(reference["criteria"], ensure_ascii=False)
    return criteria
