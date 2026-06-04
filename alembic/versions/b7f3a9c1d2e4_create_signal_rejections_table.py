"""create signal_rejections table

Rejection telemetry for strategy tuning (ui-dashboard Goal 9).

Revision ID: b7f3a9c1d2e4
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f3a9c1d2e4"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "signal_rejections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("asset_class", sa.String(length=20), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("confluence_score", sa.Float(precision=2), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signal_rejections_id", "signal_rejections", ["id"])
    op.create_index("ix_signal_rejections_created_at", "signal_rejections", ["created_at"])
    op.create_index("ix_signal_rejections_symbol", "signal_rejections", ["symbol"])
    op.create_index("ix_signal_rejections_asset_class", "signal_rejections", ["asset_class"])
    op.create_index("ix_signal_rejections_stage", "signal_rejections", ["stage"])
    op.create_index("idx_rejection_created", "signal_rejections", ["created_at"])
    op.create_index("idx_rejection_symbol_stage", "signal_rejections", ["symbol", "stage"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_rejection_symbol_stage", table_name="signal_rejections")
    op.drop_index("idx_rejection_created", table_name="signal_rejections")
    op.drop_index("ix_signal_rejections_stage", table_name="signal_rejections")
    op.drop_index("ix_signal_rejections_asset_class", table_name="signal_rejections")
    op.drop_index("ix_signal_rejections_symbol", table_name="signal_rejections")
    op.drop_index("ix_signal_rejections_created_at", table_name="signal_rejections")
    op.drop_index("ix_signal_rejections_id", table_name="signal_rejections")
    op.drop_table("signal_rejections")
