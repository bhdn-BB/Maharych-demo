import unittest
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from voice_ai_service.app.services.feedback_publisher import (
    FeedbackPublisher, ROUTING_KEY, publish_request,
)

MODULE = "voice_ai_service.app.services.feedback_publisher"


def make_db(pending):
    return SimpleNamespace(build_feedback_event=AsyncMock(side_effect=lambda i: {"interview_id": i, "feedback": {}, "questions": []}),
                           outbox=SimpleNamespace(
        pending=AsyncMock(return_value=pending), mark_published=AsyncMock(),
        mark_failed=AsyncMock(), commit=AsyncMock(),
    ))


class FeedbackPublisherTest(unittest.IsolatedAsyncioTestCase):
    async def test_marks_only_after_successful_publication(self):
        request = SimpleNamespace(interview_id="628b8e76-c5ab-4d67-854c-70c31b2eca16")
        publish = AsyncMock(side_effect=RuntimeError("broker unavailable"))
        db = make_db([])
        exchange = SimpleNamespace(publish=publish)

        with self.assertRaises(RuntimeError):
            await publish_request(exchange, db, request)
        db.outbox.mark_published.assert_not_awaited()

        publish.side_effect = None
        await publish_request(exchange, db, request)
        self.assertEqual(publish.await_args.kwargs["routing_key"], ROUTING_KEY)
        db.outbox.mark_published.assert_awaited_once_with(request)

    async def test_failing_row_does_not_block_rest_of_batch(self):
        bad, good = SimpleNamespace(interview_id="bad"), SimpleNamespace(interview_id="good")
        db = make_db([bad, good])
        publish = AsyncMock(side_effect=[RuntimeError("nack"), None])

        @asynccontextmanager
        async def session():
            yield db

        with patch(f"{MODULE}.db_session", session):
            await FeedbackPublisher()._publish_batch(SimpleNamespace(publish=publish))

        db.outbox.mark_published.assert_awaited_once_with(good)
        self.assertEqual(db.outbox.mark_failed.await_args.args[0], bad)
        db.outbox.commit.assert_awaited_once()

    async def test_publishes_pending_batch_and_closes_connection_on_stop(self):
        stop = asyncio.Event()
        request = SimpleNamespace(interview_id="interview-id")
        db = make_db([request])

        async def publish(*args, **kwargs):
            stop.set()

        exchange = SimpleNamespace(publish=AsyncMock(side_effect=publish))
        channel = SimpleNamespace()
        connection = SimpleNamespace(channel=AsyncMock(return_value=channel), close=AsyncMock())

        @asynccontextmanager
        async def session():
            yield db

        topology = AsyncMock(return_value=exchange)
        with patch(f"{MODULE}.db_session", session), patch(
            f"{MODULE}.get_settings", return_value=SimpleNamespace(rabbitmq_url="amqp://example"),
        ), patch(f"{MODULE}.aio_pika.connect_robust", AsyncMock(return_value=connection)), patch(
            f"{MODULE}.declare_topology", topology,
        ):
            await FeedbackPublisher().run(stop)

        topology.assert_awaited_once_with(channel)
        db.outbox.mark_published.assert_awaited_once_with(request)
        connection.close.assert_awaited_once()


class HealthEndpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_health_reports_a_dead_relay(self):
        from fastapi import Response
        from voice_ai_service.main import app, health_check

        async def stopped():
            return None

        task = asyncio.ensure_future(stopped())
        await task
        app.state.publisher = task
        response = Response()
        body = await health_check(response)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["status"], "publisher_stopped")

        app.state.publisher = asyncio.ensure_future(asyncio.sleep(10))
        try:
            response = Response()
            self.assertEqual((await health_check(response))["status"], "ok")
            self.assertNotEqual(response.status_code, 503)
        finally:
            app.state.publisher.cancel()
            del app.state.publisher


class RelayProcessTest(unittest.IsolatedAsyncioTestCase):
    async def test_relay_exits_nonzero_when_publisher_dies_and_zero_on_clean_stop(self):
        from voice_ai_service import relay

        with patch.object(relay, "publish_pending_feedback", AsyncMock(side_effect=RuntimeError("boom"))):
            self.assertEqual(await relay.run(), 1)

        async def until_stopped(stop):
            asyncio.get_running_loop().call_later(0.05, stop.set)
            await stop.wait()

        with patch.object(relay, "publish_pending_feedback", until_stopped):
            self.assertEqual(await relay.run(), 0)

    def test_heartbeat_touches_file(self):
        import os, tempfile
        from voice_ai_service import relay

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "hb")
            relay.touch(path)
            self.assertTrue(os.path.exists(path))
