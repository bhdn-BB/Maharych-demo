"""Exercise the producer payload against the worker's actual parser."""

import importlib.util
from pathlib import Path
import unittest

from voice_ai_service.app.services import feedback_publisher


worker_path = Path(__file__).resolve().parents[2] / "feedback_service" / "worker.py"
spec = importlib.util.spec_from_file_location("feedback_worker_contract", worker_path)
worker = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(worker)
except ModuleNotFoundError as exc:
    if exc.name not in {"pika", "psycopg", "reportlab"}:
        raise
    worker = None


@unittest.skipIf(worker is None, "PDF worker dependencies are not installed")
class FeedbackContractTest(unittest.TestCase):
    def test_queue_and_payload_match_worker(self):
        interview_id = "628b8e76-c5ab-4d67-854c-70c31b2eca16"
        for name in ("EVENTS_EXCHANGE", "DLX_EXCHANGE", "ROUTING_KEY", "DEAD_KEY",
                     "QUEUE_NAME", "RETRY_QUEUE", "DLQ_NAME", "RETRY_DELAY_MS"):
            self.assertEqual(getattr(feedback_publisher, name), getattr(worker, name), name)
        event = {"interview_id": interview_id, "position": "Backend", "feedback": {"overall_score": 7},
                 "questions": [{"index": 1, "question": "Q?", "answer": "A", "score": 7, "comment": None}]}
        parsed = worker.parse_event(feedback_publisher.encode_feedback_request(event))
        self.assertEqual(parsed, (interview_id, "Backend", {"overall_score": 7}, [(1, "Q?", "A", 7, None)]))
