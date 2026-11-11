"""
gRPC server lifecycle management.

Provides start_grpc_server() / stop_grpc_server() for use alongside FastAPI.
"""
from __future__ import annotations

import logging

import grpc.aio

from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2_grpc
from voice_ai_service.app.grpc.interview_servicer import AIServiceServicer

logger = logging.getLogger(__name__)

_server: grpc.aio.Server | None = None

MAX_MESSAGE_LENGTH = 10 * 1024 * 1024  # 10 MB for audio chunks


async def start_grpc_server(port: int = 50051) -> grpc.aio.Server:
    """Create and start the async gRPC server."""
    global _server

    _server = grpc.aio.server(
        options=[
            ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
            ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
        ],
    )

    ai_service_pb2_grpc.add_AIServiceServicer_to_server(
        AIServiceServicer(), _server,
    )

    listen_addr = f"[::]:{port}"
    _server.add_insecure_port(listen_addr)
    await _server.start()

    logger.info("gRPC server started on %s", listen_addr)
    return _server


async def stop_grpc_server(grace: float = 5.0) -> None:
    """Gracefully stop the gRPC server."""
    global _server

    if _server is not None:
        logger.info("Stopping gRPC server (grace=%.1fs)…", grace)
        await _server.stop(grace)
        _server = None
        logger.info("gRPC server stopped")
