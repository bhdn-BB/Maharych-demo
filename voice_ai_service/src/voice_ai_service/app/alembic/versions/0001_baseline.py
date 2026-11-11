"""Baseline schema for the voice AI service, with the seeded interview-question bank.

This single revision replaces the former 0001-0008 chain. Its revision id stays "0008"
(the former head) so databases created by the old chain are already up to date and
need no `alembic stamp`; a new database gets the full schema in one step.

Revision ID: 0008
Revises:
"""
import sqlalchemy as sa
from alembic import op

from voice_ai_service.app.services.voice_conversation.question_bank_seed_v1 import starter_questions
from voice_ai_service.app.services.voice_conversation.question_bank_seed_v2 import additional_questions

revision = "0008"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("candidate_email", sa.String(255), nullable=False),
        sa.Column("position_title", sa.String(255), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False, server_default="greeting"),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("interview_id", sa.String(36), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("state_json", sa.JSON(), nullable=True),
        sa.Column("feedback_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("interview_id", name="uq_conversations_interview_id"),
    )
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"], unique=True)

    op.create_table(
        "question_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("topic_index", sa.Integer, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False, server_default="general"),
        sa.Column("candidate_answer", sa.Text, nullable=False, server_default=""),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
    )

    op.create_table(
        "feedback_outbox",
        sa.Column("interview_id", sa.String(36), primary_key=True),
        sa.Column("published", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_feedback_outbox_pending", "feedback_outbox", ["created_at"],
        postgresql_where=sa.text("published = false"),
    )

    op.create_table(
        "feedback_reports",
        sa.Column("interview_id", sa.String(36), primary_key=True),
        sa.Column("pdf_data", sa.LargeBinary, nullable=False),
    )

    bank = op.create_table(
        "interview_question_bank",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("focus", sa.String(30), nullable=False),
        sa.Column("topic_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("provenance", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("key", "version", "language", name="uq_question_bank_version_language"),
    )
    op.create_index(
        "ix_question_bank_selection", "interview_question_bank",
        ["focus", "language", "topic_index", "active"],
    )
    op.bulk_insert(bank, starter_questions() + additional_questions())


def downgrade():
    raise RuntimeError("The baseline holds interview data and the curated question bank; drop the schema manually")
