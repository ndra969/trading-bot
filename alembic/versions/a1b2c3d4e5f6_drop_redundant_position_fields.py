"""drop redundant position fields

Removes three columns that were always stored as default 0.0 because nothing
populated them — they polluted analytics with noise.

- signal_confidence: duplicated confluence_score
- quality_score: never derived from anywhere
- execution_duration_ms: never measured at execution time

Revision ID: a1b2c3d4e5f6
Revises: 0bf7b67bd264
Create Date: 2026-05-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "0bf7b67bd264"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop redundant columns + their constraints + indexes.

    Defensive: skip drops that target objects which never got created in
    older deployments. PostgreSQL won't drop a column that still has a
    check constraint, but we want this migration to be idempotent across
    schemas that differ in history.
    """
    bind = op.get_bind()

    def _has_constraint(name: str) -> bool:
        result = bind.execute(
            sa.text(
                "SELECT 1 FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'positions' AND c.conname = :name"
            ),
            {"name": name},
        )
        return result.scalar() is not None

    def _has_index(name: str) -> bool:
        result = bind.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
            {"name": name},
        )
        return result.scalar() is not None

    def _has_column(name: str) -> bool:
        result = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'positions' AND column_name = :name"
            ),
            {"name": name},
        )
        return result.scalar() is not None

    if _has_constraint("check_position_quality_range"):
        op.drop_constraint("check_position_quality_range", "positions", type_="check")
    if _has_constraint("check_signal_confidence_range"):
        op.drop_constraint("check_signal_confidence_range", "positions", type_="check")
    if _has_index("idx_position_quality"):
        op.drop_index("idx_position_quality", table_name="positions")

    for col in ("quality_score", "signal_confidence", "execution_duration_ms"):
        if _has_column(col):
            op.drop_column("positions", col)


def downgrade() -> None:
    """Recreate the dropped columns (with their original defaults/constraints)."""
    op.add_column(
        "positions",
        sa.Column(
            "quality_score",
            sa.Float(precision=2),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "positions",
        sa.Column(
            "signal_confidence",
            sa.Float(precision=2),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "positions",
        sa.Column(
            "execution_duration_ms",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_check_constraint(
        "check_position_quality_range",
        "positions",
        "quality_score >= 0 AND quality_score <= 100",
    )
    op.create_check_constraint(
        "check_signal_confidence_range",
        "positions",
        "signal_confidence >= 0 AND signal_confidence <= 100",
    )
    op.create_index("idx_position_quality", "positions", ["quality_score"])
