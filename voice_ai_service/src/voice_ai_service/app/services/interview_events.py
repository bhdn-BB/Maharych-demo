"""Consume interview finalization requests and report the outcome as an event.

Flow: Go publishes ``interview.finish.requested`` -> this consumer runs the (idempotent)
finalization -> publishes ``interview.finished`` {interview_id, stage} for Go to persist.
Transient failures are retried through a TTL queue; after ``MAX_ATTEMPTS`` the request is parked
in a DLQ and ``stage="failed"`` is reported so the candidate can try again.
"""

import asyncio
import json
import logging
import uuid

import aio_pika
from voice_ai_service.app.core.config import get_settings
from voice_ai_service.app.core.dependencies import db_session, get_agent
from voice_ai_service.app.services.interview_lifecycle import InterviewLifecycleService

logger = logging.getLogger(__name__)

# Broker topology: the Go side (backend/src/internal/broker) must use the same names.
EVENTS_EXCHANGE = "maharych.events"
DLX_EXCHANGE = "maharych.dlx"
FINISH_REQUESTED_KEY = "interview.finish.requested"
FINISHED_KEY = "interview.finished"
FINISH_DEAD_KEY = "interview.finish.dead"
FINISH_QUEUE = "interview.finish"
FINISH_RETRY_QUEUE = "interview.finish.retry"
FINISH_DLQ = "interview.finish.dlq"
RETRY_DELAY_MS = 10000
MAX_ATTEMPTS = 5


def parse_finish_request(body: bytes) -> str:
    """Return the normalized interview id; raises ValueError/KeyError/JSONDecodeError if invalid."""
    return str(uuid.UUID(json.loads(body)["interview_id"]))


def encode_finished(interview_id: str, stage: str) -> bytes:
    return json.dumps({"interview_id": interview_id, "stage": stage}).encode()


def attempt_of(message) -> int:
    try:
        return int((message.headers or {}).get("x-attempt", 0))
    except (TypeError, ValueError):
        return 0


async def declare_topology(channel):
    events = await channel.declare_exchange(EVENTS_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
    dlx = await channel.declare_exchange(DLX_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(FINISH_DLQ, durable=True)
    await dlq.bind(dlx, routing_key=FINISH_DEAD_KEY)
    await channel.declare_queue(FINISH_RETRY_QUEUE, durable=True, arguments={
        "x-message-ttl": RETRY_DELAY_MS,
        "x-dead-letter-exchange": EVENTS_EXCHANGE,
        "x-dead-letter-routing-key": FINISH_REQUESTED_KEY,
    })
    queue = await channel.declare_queue(FINISH_QUEUE, durable=True, arguments={
        "x-dead-letter-exchange": DLX_EXCHANGE,
        "x-dead-letter-routing-key": FINISH_DEAD_KEY,
    })
    await queue.bind(events, routing_key=FINISH_REQUESTED_KEY)
    return events, queue


async def finalize(interview_id: str) -> str:
    """Run the idempotent finalization in its own DB session and return the terminal stage."""
    async with db_session() as db:
        return await InterviewLifecycleService(db, get_agent).finish(interview_id)


async def publish_finished(events, interview_id: str, stage: str) -> None:
    await events.publish(
        aio_pika.Message(body=encode_finished(interview_id, stage), delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                         content_type="application/json"),
        routing_key=FINISHED_KEY, mandatory=False,
    )


async def handle_message(channel, events, message: aio_pika.IncomingMessage, finalizer=finalize) -> None:
    """Process one request. Always settles the message: ack on success/retry/park, reject on bad input."""
    try:
        interview_id = parse_finish_request(message.body)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        logger.warning("Invalid interview finish request; dead-lettering")
        await message.reject(requeue=False)  # -> DLX -> DLQ
        return

    try:
        stage = await finalizer(interview_id)
        if stage not in ("finished", "abandoned"):
            raise RuntimeError(f"finalization returned non-terminal stage {stage!r}")
    except Exception:
        attempt = attempt_of(message) + 1
        logger.exception("Finalizing interview %s failed (attempt %s)", interview_id, attempt)
        if attempt < MAX_ATTEMPTS:
            await channel.default_exchange.publish(
                aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                                 headers={"x-attempt": attempt}),
                routing_key=FINISH_RETRY_QUEUE,
            )
        else:  # exhausted: park for inspection and let the candidate retry
            await channel.default_exchange.publish(
                aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=FINISH_DLQ,
            )
            await publish_finished(events, interview_id, "failed")
        await message.ack()
        return

    # Publish before ack: a crash in between redelivers the request, and finalization is idempotent.
    await publish_finished(events, interview_id, stage)
    await message.ack()


class InterviewFinishConsumer:
    """Own a broker connection and process finalization requests until stopped."""

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self._consume_until_stopped(stop)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Interview finish consumer failed; retrying")
                await self._wait(stop, 5)

    async def _consume_until_stopped(self, stop: asyncio.Event) -> None:
        connection = await aio_pika.connect_robust(get_settings().rabbitmq_url, timeout=5)
        try:
            channel = await connection.channel(publisher_confirms=True)
            await channel.set_qos(prefetch_count=2)
            events, queue = await declare_topology(channel)

            async def on_message(message: aio_pika.IncomingMessage) -> None:
                await handle_message(channel, events, message)

            await queue.consume(on_message)
            await stop.wait()
        finally:
            await connection.close()

    @staticmethod
    async def _wait(stop: asyncio.Event, timeout: float) -> None:
        try:
            await asyncio.wait_for(stop.wait(), timeout=timeout)
        except TimeoutError:
            pass


async def consume_finish_requests(stop: asyncio.Event) -> None:
    await InterviewFinishConsumer().run(stop)
