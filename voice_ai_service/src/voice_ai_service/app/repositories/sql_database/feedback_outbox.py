"""Operations for publishing committed feedback export requests."""

from datetime import datetime, timezone
from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from voice_ai_service.app.schemas.db import FeedbackOutbox


class FeedbackOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def pending(self, limit: int = 25) -> Sequence[FeedbackOutbox]:
        """Lock unpublished rows (skipping rows locked by another relay) until commit()."""
        query = (
            select(FeedbackOutbox)
            .where(FeedbackOutbox.published == False)
            .order_by(FeedbackOutbox.created_at, FeedbackOutbox.interview_id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self._session.exec(query)).all()

    async def mark_published(self, request: FeedbackOutbox) -> None:
        """Stage the flag; the caller commits the batch (releasing the row locks)."""
        request.published = True
        request.published_at = datetime.now(timezone.utc)
        request.last_error = None
        self._session.add(request)
        await self._session.flush()

    async def mark_failed(self, request: FeedbackOutbox, error: str) -> None:
        """Record a publish failure so stuck rows are visible in the table."""
        request.attempts += 1
        request.last_error = error[:1000]
        self._session.add(request)
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
