"""Standalone outbox relay: drains ``feedback_outbox`` into RabbitMQ.

Run as ``python -m voice_ai_service.relay``. Any number of replicas can run side by side
(rows are claimed with ``FOR UPDATE SKIP LOCKED``). A heartbeat file lets the container
healthcheck notice a stuck loop, and the process exits non-zero if the loop dies so the
orchestrator restarts it.
"""

import asyncio
import logging
import os
import signal
import sys

from voice_ai_service.app.core.config import get_settings
from voice_ai_service.app.services.feedback_publisher import publish_pending_feedback

logger = logging.getLogger(__name__)
HEARTBEAT_INTERVAL = 15


def touch(path: str) -> None:
    if not path:
        return
    try:
        with open(path, "a"):
            os.utime(path, None)
    except OSError:
        logger.warning("Cannot update heartbeat file %s", path)


async def beat(stop: asyncio.Event, path: str) -> None:
    while not stop.is_set():
        touch(path)
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_INTERVAL)
        except TimeoutError:
            pass


async def run() -> int:
    logging.basicConfig(level=get_settings().log_level)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows event loops
            pass
    heartbeat = asyncio.create_task(beat(stop, os.environ.get("HEARTBEAT_FILE", "")))
    relay = asyncio.create_task(publish_pending_feedback(stop))
    done, _ = await asyncio.wait({relay, heartbeat}, return_when=asyncio.FIRST_COMPLETED)
    stop.set()
    for task in (relay, heartbeat):
        task.cancel()
    await asyncio.gather(relay, heartbeat, return_exceptions=True)
    failed = relay in done and relay.exception() is not None
    if failed:
        logger.error("Outbox relay stopped unexpectedly: %r", relay.exception())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
