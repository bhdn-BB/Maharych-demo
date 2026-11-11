"""Selection invariants independent of database and model providers."""
import unittest
from unittest.mock import AsyncMock, patch

from voice_ai_service.app.services.question_bank import QuestionBankService, QuestionBankUnavailable
from voice_ai_service.app.services.voice_conversation.question_bank_seed_v1 import starter_questions
from voice_ai_service.app.services.voice_conversation.question_bank_seed_v2 import additional_questions


def bank_rows():
    return starter_questions() + additional_questions()


class QuestionBankServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_seeded_bank_has_about_200_distinct_questions_covering_every_topic(self):
        rows = bank_rows()
        self.assertGreaterEqual(len({row["key"] for row in rows}), 195)
        self.assertEqual(len({row["question"] for row in rows}), len(rows))
        for focus in ("behavioral", "algorithms", "system-design"):
            for language in ("en", "uk"):
                for topic in range(5):
                    with self.subTest(focus=focus, language=language, topic=topic):
                        general = [row for row in rows if (row["focus"], row["language"], row["topic_index"], row["role"])
                                   == (focus, language, topic, "*")]
                        self.assertGreaterEqual(len(general), 10)

    async def test_latest_version_and_specific_role_are_selected_without_changing_source(self):
        rows = [row.copy() for row in bank_rows()
                if row["focus"] == "system-design" and row["language"] == "en"]
        specific = next(row for row in rows if row["key"] == "design-data")
        revision = {**specific, "version": 2, "question": "Updated model-serving question"}
        rows.append(revision)
        store = type("Store", (), {"list_question_bank": AsyncMock(return_value=rows)})()
        with patch("voice_ai_service.app.services.question_bank.secrets.choice",
                   side_effect=lambda options: next((r for r in options if r["role"] == "Data Science"), options[0])):
            selected = await QuestionBankService(store).select("system-design", "en", "data science", "middle")
        self.assertEqual(selected[0]["version"], 2)
        self.assertEqual(selected[0]["question"], revision["question"])
        self.assertEqual(selected[0]["source_url"], revision["source_url"])
        self.assertEqual(len({item["key"] for item in selected}), 5)
        self.assertEqual([item["key"].split("-")[1] for item in selected[1:]], ["components", "change", "storage", "ops"])
        store.list_question_bank.assert_awaited_once_with("system-design", "en")

    async def test_missing_topic_fails_without_returning_partial_selection(self):
        rows = [row for row in bank_rows() if row["focus"] == "algorithms"
                and row["language"] == "uk" and row["topic_index"] != 3]
        store = type("Store", (), {"list_question_bank": AsyncMock(return_value=rows)})()
        with self.assertRaisesRegex(QuestionBankUnavailable, "topic 4"):
            await QuestionBankService(store).select("algorithms", "uk", "Backend", "junior")
