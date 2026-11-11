"""Opt-in real PostgreSQL check; creates and removes only its own random schema."""
import os
import unittest
import uuid

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from voice_ai_service.app.repositories.sql_database.postgresql import PostgreSQL
from voice_ai_service.app.services.interview_storage import InterviewStorage


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL for an isolated PostgreSQL test")
class PostgreSQLLockTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = os.environ["TEST_DATABASE_URL"]
        if not url.startswith("postgresql+asyncpg://"):
            raise ValueError("TEST_DATABASE_URL must use PostgreSQL/asyncpg")
        self.schema = "maharych_test_" + uuid.uuid4().hex
        self.admin = create_async_engine(url)
        async with self.admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.engine = create_async_engine(url, connect_args={"server_settings": {"search_path": self.schema}})
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        await self.admin.dispose()

    async def test_independent_connections_cannot_transition_same_interview_together(self):
        interview_id = str(uuid.uuid4())
        async with self.factory() as first, self.factory() as second:
            db1, db2 = PostgreSQL(first), PostgreSQL(second)
            await InterviewStorage(db1).ensure_conversation(interview_id, "test@example.com", "Backend")
            await db1.lock_interview(interview_id)
            await second.exec(text("SET LOCAL lock_timeout = '100ms'"))
            with self.assertRaises(DBAPIError) as caught:
                await db2.lock_interview(interview_id)
            self.assertEqual(caught.exception.orig.sqlstate, "55P03")
            await second.rollback()
            await first.rollback()
            self.assertIsNotNone(await db2.lock_interview(interview_id))
