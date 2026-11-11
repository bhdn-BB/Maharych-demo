from contextlib import asynccontextmanager
from functools import lru_cache
from fastapi import Depends

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from voice_ai_service.app.core.config import get_settings
from voice_ai_service.app.repositories.llm.gemini_client import GeminiClient
from voice_ai_service.app.repositories.sql_database.postgresql import PostgreSQL
from voice_ai_service.app.services.voice_conversation.session import InterviewSession
from voice_ai_service.app.repositories.resume_documents import ResumeDocumentRepository
from voice_ai_service.app.services.resume import ResumeService
from voice_ai_service.app.services.interview_lifecycle import InterviewLifecycleService
from voice_ai_service.app.services.dialogue_llm import DialogueModel


@lru_cache
def get_gemini_client() -> GeminiClient:
    s = get_settings()
    return GeminiClient(api_key=s.gemini_api_key, model_name=s.gemini_model)


@lru_cache
def _session_factory():
    # Each in-flight answer holds a connection for the duration of its Gemini calls, so size the
    # pool for concurrent interviews, drop dead connections and fail fast instead of hanging.
    engine = create_async_engine(
        get_settings().DATABASE_URL, echo=False,
        pool_size=10, max_overflow=10, pool_timeout=30, pool_pre_ping=True, pool_recycle=1800,
    )
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def db_session():
    """Standalone async context manager for DB sessions.

    Can be used by both FastAPI dependencies and gRPC servicers.
    """
    async with _session_factory()() as session:
        yield PostgreSQL(session)


async def get_db() -> PostgreSQL:
    """FastAPI dependency — yields a PostgreSQL wrapper for a single request."""
    async with db_session() as db:
        yield db


async def get_agent(db: PostgreSQL = None) -> InterviewSession:
    """Return an agent wired with the given DB session.

    The Gemini client is shared; the agent is created per-request
    because dialogue transitions use the request-scoped DB session.
    """
    return InterviewSession(
        llm=DialogueModel(get_gemini_client()),
        db=db,
    )


def get_resume_service() -> ResumeService:
    return ResumeService(ResumeDocumentRepository())


def get_interview_lifecycle(db: PostgreSQL = Depends(get_db)) -> InterviewLifecycleService:
    return InterviewLifecycleService(db, get_agent)
