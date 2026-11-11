"""Publish committed feedback export requests without blocking interviews."""

import asyncio
import json
import logging

import aio_pika
from voice_ai_service.app.core.config import get_settings
from voice_ai_service.app.core.dependencies import db_session

logger = logging.getLogger(__name__)

# Broker topology: keep in sync with feedback_service/worker.py (see test_feedback_contract).
EVENTS_EXCHANGE = "maharych.events"
DLX_EXCHANGE = "maharych.dlx"
ROUTING_KEY = "feedback.ready"
DEAD_KEY = "feedback.pdf.dead"
QUEUE_NAME = "feedback.pdf"
RETRY_QUEUE = "feedback.pdf.retry"
DLQ_NAME = "feedback.pdf.dlq"
RETRY_DELAY_MS = 10000


def encode_feedback_request(event: dict | str) -> bytes:
    """Serialize the export event (a bare interview id yields an id-only event)."""
    if isinstance(event, str):
        event = {"interview_id": event}
    return json.dumps(event, ensure_ascii=False, default=str).encode()


async def declare_topology(channel):
    """Declare the same topology as the worker so events are never dropped before it starts."""
    events = await channel.declare_exchange(EVENTS_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
    dlx = await channel.declare_exchange(DLX_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(DLQ_NAME, durable=True)
    await dlq.bind(dlx, routing_key=DEAD_KEY)
    await channel.declare_queue(RETRY_QUEUE, durable=True, arguments={
        "x-message-ttl": RETRY_DELAY_MS,
        "x-dead-letter-exchange": EVENTS_EXCHANGE,
        "x-dead-letter-routing-key": ROUTING_KEY,
    })
    queue = await channel.declare_queue(QUEUE_NAME, durable=True, arguments={
        "x-dead-letter-exchange": DLX_EXCHANGE,
        "x-dead-letter-routing-key": DEAD_KEY,
    })
    await queue.bind(events, routing_key=ROUTING_KEY)
    return events


async def publish_request(exchange, db, request) -> None:
    payload = encode_feedback_request(await db.build_feedback_event(request.interview_id))
    await exchange.publish(
        aio_pika.Message(body=payload, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=ROUTING_KEY,
    )
    await db.outbox.mark_published(request)


class FeedbackPublisher:
    """Own the broker connection and periodically drain the transactional outbox."""

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self._publish_until_stopped(stop)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("PDF request publication failed; retrying")
                await self._wait(stop, 5)

    async def _publish_until_stopped(self, stop: asyncio.Event) -> None:
        connection = await aio_pika.connect_robust(get_settings().rabbitmq_url, timeout=5)
        try:
            channel = await connection.channel(publisher_confirms=True)
            exchange = await declare_topology(channel)
            while not stop.is_set():
                await self._publish_batch(exchange)
                await self._wait(stop, 2)
        finally:
            await connection.close()

    async def _publish_batch(self, exchange) -> None:
        # pending() locks rows with FOR UPDATE SKIP LOCKED, so replicas never share a row;
        # the locks are released by the single commit below. A failing row is skipped,
        # not allowed to block the rest of the batch.
        async with db_session() as db:
            for request in await db.outbox.pending():
                try:
                    await publish_request(exchange, db, request)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception("Failed to publish feedback request %s", request.interview_id)
                    await db.outbox.mark_failed(request, repr(exc))
            await db.outbox.commit()

    @staticmethod
    async def _wait(stop: asyncio.Event, timeout: float) -> None:
        try:
            await asyncio.wait_for(stop.wait(), timeout=timeout)
        except TimeoutError:
            pass


async def publish_pending_feedback(stop: asyncio.Event) -> None:
    await FeedbackPublisher().run(stop)
