from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI, Response

from voice_ai_service.app.core.config import get_settings
from voice_ai_service.app.grpc.server import start_grpc_server, stop_grpc_server
from voice_ai_service.app.routers import interview, resume, voice
from voice_ai_service.app.services.feedback_publisher import publish_pending_feedback
from voice_ai_service.app.services.interview_events import consume_finish_requests

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting gRPC server on port %d", settings.grpc_port)
    await start_grpc_server(port=settings.grpc_port)
    stop = asyncio.Event()
    # The outbox relay normally runs as a separate process (voice_ai_service.relay); keep the
    # in-process task only as a single-container fallback.
    publisher = (
        asyncio.create_task(publish_pending_feedback(stop))
        if settings.run_outbox_relay
        else None
    )
    if publisher is not None:
        app.state.publisher = publisher
    finisher = asyncio.create_task(consume_finish_requests(stop))
    app.state.finisher = finisher
    try:
        yield
    finally:
        stop.set()
        for task in (t for t in (publisher, finisher) if t is not None):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Stopping gRPC server")
        await stop_grpc_server()


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# No CORS: this service is private to the Compose network (browsers reach it only via the Go API).

app.include_router(interview.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check(response: Response):
    """Unhealthy when a broker task (outbox relay or finish consumer) died, so Compose can restart it."""
    for name in ("publisher", "finisher"):
        task = getattr(app.state, name, None)
        if task is not None and task.done():
            response.status_code = 503
            return {"status": f"{name}_stopped", "version": settings.app_version}
    return {"status": "ok", "version": settings.app_version}
