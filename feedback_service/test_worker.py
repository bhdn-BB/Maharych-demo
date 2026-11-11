import json
import os
import unittest
from unittest.mock import patch, MagicMock

from worker import handle_message, render_report_pdf, settle_failure, FONT, MAX_ATTEMPTS, RETRY_QUEUE


class PDFWorkerTest(unittest.TestCase):
    @unittest.skipUnless(os.path.isfile(FONT), "Set PDF_FONT_PATH to a Unicode TTF font")
    def test_unicode_report_with_explicit_score_scale(self):
        pdf = render_report_pdf("Backend", {"overall_score": 80, "score_scale": 100,
            "summary": "Навчальна співбесіда", "recommendation": "Повторити індекси", "top_strengths": ["Аргументація"]},
            [(1, "Як працює індекс?", "Прискорює пошук", 80, "Правильно")])
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1000)

    EVENT = json.dumps({
        "interview_id": "628b8e76-c5ab-4d67-854c-70c31b2eca16", "position": "Backend",
        "feedback": {"overall_score": 80, "score_scale": 100},
        "questions": [{"index": 1, "question": "Question", "answer": "Answer", "score": 80, "comment": "Comment"}],
    }).encode()

    @staticmethod
    def mock_cursor(exists):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,) if exists else None
        return connection, cursor

    def test_duplicate_delivery_does_not_render_or_insert(self):
        connection, cursor = self.mock_cursor(exists=True)
        with patch("worker.psycopg.connect", return_value=connection), patch("worker.render_report_pdf") as render:
            handle_message("test-only", self.EVENT)
            render.assert_not_called()
            self.assertEqual(cursor.execute.call_count, 1)

    def test_invalid_event_is_rejected_before_database_access(self):
        for body in (b'{"interview_id":"invalid"}', b'{"interview_id":"628b8e76-c5ab-4d67-854c-70c31b2eca16"}', b"not-json"):
            with patch("worker.psycopg.connect") as connect:
                with self.assertRaises((ValueError, KeyError)):
                    handle_message("test-only", body)
                connect.assert_not_called()

    def test_valid_event_renders_from_payload_without_reading_foreign_tables(self):
        connection, cursor = self.mock_cursor(exists=False)
        with patch("worker.psycopg.connect", return_value=connection), patch("worker.render_report_pdf", return_value=b"pdf") as render:
            handle_message("test-only", self.EVENT)
            render.assert_called_once_with("Backend", {"overall_score": 80, "score_scale": 100},
                                           [(1, "Question", "Answer", 80, "Comment")])
            statements = " ".join(call.args[0] for call in cursor.execute.call_args_list)
            self.assertNotIn("conversations", statements)
            self.assertNotIn("question_records", statements)
            self.assertIn("ON CONFLICT", cursor.execute.call_args.args[0])


class RetryPolicyTest(unittest.TestCase):
    @staticmethod
    def props(attempt=None):
        return MagicMock(headers=None if attempt is None else {"x-attempt": attempt})

    def test_transient_failure_goes_to_retry_queue_and_acks(self):
        channel, method = MagicMock(), MagicMock(delivery_tag=7)
        settle_failure(channel, method, self.props(), b"{}", permanent=False)
        kwargs = channel.basic_publish.call_args.kwargs
        self.assertEqual(kwargs["routing_key"], RETRY_QUEUE)
        self.assertEqual(kwargs["properties"].headers["x-attempt"], 1)
        channel.basic_ack.assert_called_once_with(delivery_tag=7)
        channel.basic_reject.assert_not_called()

    def test_exhausted_attempts_are_dead_lettered(self):
        channel, method = MagicMock(), MagicMock(delivery_tag=7)
        settle_failure(channel, method, self.props(MAX_ATTEMPTS - 1), b"{}", permanent=False)
        channel.basic_reject.assert_called_once_with(delivery_tag=7, requeue=False)
        channel.basic_publish.assert_not_called()

    def test_invalid_event_is_dead_lettered_immediately(self):
        channel, method = MagicMock(), MagicMock(delivery_tag=7)
        settle_failure(channel, method, self.props(), b"x", permanent=True)
        channel.basic_reject.assert_called_once_with(delivery_tag=7, requeue=False)


class HeartbeatTest(unittest.TestCase):
    def test_heartbeat_touches_file_and_reschedules(self):
        import tempfile
        from worker import schedule_heartbeat
        connection = MagicMock()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "hb")
            schedule_heartbeat(connection, path)
            self.assertTrue(os.path.exists(path))
            connection.call_later.assert_called_once()
            self.assertEqual(connection.call_later.call_args.args[0], 30)
