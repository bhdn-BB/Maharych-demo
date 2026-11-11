import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from voice_ai_service.app.services import interview_events as ev

ID = "628b8e76-c5ab-4d67-854c-70c31b2eca16"


def message(body=None, headers=None):
    body = json.dumps({"interview_id": ID}).encode() if body is None else body
    return SimpleNamespace(body=body, headers=headers or {}, ack=AsyncMock(), reject=AsyncMock())


def broker():
    events = SimpleNamespace(publish=AsyncMock())
    channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=AsyncMock()))
    return channel, events


def published_event(events):
    return json.loads(events.publish.await_args.args[0].body)


class InterviewFinishConsumerTest(unittest.IsolatedAsyncioTestCase):
    async def test_success_publishes_finished_before_ack(self):
        channel, events = broker()
        msg = message()
        order = []
        events.publish.side_effect = lambda *a, **k: order.append("publish")
        msg.ack.side_effect = lambda *a, **k: order.append("ack")

        await ev.handle_message(channel, events, msg, finalizer=AsyncMock(return_value="finished"))

        self.assertEqual(order, ["publish", "ack"])
        self.assertEqual(published_event(events), {"interview_id": ID, "stage": "finished"})
        self.assertEqual(events.publish.await_args.kwargs["routing_key"], ev.FINISHED_KEY)

    async def test_abandoned_is_reported(self):
        channel, events = broker()
        await ev.handle_message(channel, events, message(), finalizer=AsyncMock(return_value="abandoned"))
        self.assertEqual(published_event(events)["stage"], "abandoned")

    async def test_transient_failure_goes_to_retry_queue_with_attempt_header(self):
        channel, events = broker()
        msg = message()
        await ev.handle_message(channel, events, msg, finalizer=AsyncMock(side_effect=RuntimeError("gemini 503")))

        sent = channel.default_exchange.publish.await_args
        self.assertEqual(sent.kwargs["routing_key"], ev.FINISH_RETRY_QUEUE)
        self.assertEqual(sent.args[0].headers["x-attempt"], 1)
        msg.ack.assert_awaited_once()
        events.publish.assert_not_awaited()

    async def test_non_terminal_stage_is_treated_as_failure(self):
        channel, events = broker()
        await ev.handle_message(channel, events, message(), finalizer=AsyncMock(return_value="questioning"))
        self.assertEqual(channel.default_exchange.publish.await_args.kwargs["routing_key"], ev.FINISH_RETRY_QUEUE)
        events.publish.assert_not_awaited()

    async def test_exhausted_attempts_park_in_dlq_and_report_failed(self):
        channel, events = broker()
        msg = message(headers={"x-attempt": ev.MAX_ATTEMPTS - 1})
        await ev.handle_message(channel, events, msg, finalizer=AsyncMock(side_effect=RuntimeError("boom")))

        self.assertEqual(channel.default_exchange.publish.await_args.kwargs["routing_key"], ev.FINISH_DLQ)
        self.assertEqual(published_event(events), {"interview_id": ID, "stage": "failed"})
        msg.ack.assert_awaited_once()

    async def test_invalid_request_is_rejected_without_finalizing(self):
        channel, events = broker()
        finalizer = AsyncMock()
        for body in (b"not-json", b'{"interview_id":"nope"}', b"{}"):
            msg = message(body=body)
            await ev.handle_message(channel, events, msg, finalizer=finalizer)
            msg.reject.assert_awaited_once_with(requeue=False)
        finalizer.assert_not_awaited()
        events.publish.assert_not_awaited()


class TopologyContractTest(unittest.TestCase):
    def test_names_match_the_go_side(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[2] / "backend/src/internal/broker/broker.go").read_text(encoding="utf-8")
        self.assertIn(f'EventsExchange     = "{ev.EVENTS_EXCHANGE}"', source)
        self.assertIn(f'FinishRequestedKey = "{ev.FINISH_REQUESTED_KEY}"', source)
        self.assertIn(f'FinishedKey        = "{ev.FINISHED_KEY}"', source)
