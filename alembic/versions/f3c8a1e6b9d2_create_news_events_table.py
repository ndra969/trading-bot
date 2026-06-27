"""create news_events table

Revision ID: f3c8a1e6b9d2
Revises: b7f3a9c1d2e4
Create Date: 2026-06-27

News / economic-calendar integration (Phase 1). Persists scheduled events
scraped from the calendar source; upserts key on ``source_id``.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3c8a1e6b9d2"
down_revision: str | Sequence[str] | None = "b7f3a9c1d2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "news_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=40), nullable=True),
        sa.Column("event_time_utc", sa.DateTime(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("impact", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("forecast", sa.String(length=50), nullable=True),
        sa.Column("previous", sa.String(length=50), nullable=True),
        sa.Column("actual", sa.String(length=50), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index(op.f("ix_news_events_id"), "news_events", ["id"], unique=False)
    op.create_index(op.f("ix_news_events_source_id"), "news_events", ["source_id"], unique=False)
    op.create_index(
        op.f("ix_news_events_event_time_utc"), "news_events", ["event_time_utc"], unique=False
    )
    op.create_index(op.f("ix_news_events_currency"), "news_events", ["currency"], unique=False)
    op.create_index(op.f("ix_news_events_impact"), "news_events", ["impact"], unique=False)
    op.create_index(
        "idx_news_currency_time", "news_events", ["currency", "event_time_utc"], unique=False
    )
    op.create_index(
        "idx_news_impact_time", "news_events", ["impact", "event_time_utc"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_news_impact_time", table_name="news_events")
    op.drop_index("idx_news_currency_time", table_name="news_events")
    op.drop_index(op.f("ix_news_events_impact"), table_name="news_events")
    op.drop_index(op.f("ix_news_events_currency"), table_name="news_events")
    op.drop_index(op.f("ix_news_events_event_time_utc"), table_name="news_events")
    op.drop_index(op.f("ix_news_events_source_id"), table_name="news_events")
    op.drop_index(op.f("ix_news_events_id"), table_name="news_events")
    op.drop_table("news_events")
