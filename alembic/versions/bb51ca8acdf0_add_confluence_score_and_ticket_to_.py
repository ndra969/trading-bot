"""add_confluence_score_and_ticket_to_positions

Revision ID: bb51ca8acdf0
Revises: f5ee315d1247
Create Date: 2026-01-13 09:44:27.365185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb51ca8acdf0'
down_revision: Union[str, Sequence[str], None] = 'f5ee315d1247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add confluence_score and ticket fields to positions table."""
    # Add confluence_score column
    op.add_column(
        'positions',
        sa.Column('confluence_score', sa.Float(precision=2), nullable=False, server_default='0.0')
    )
    
    # Add ticket column
    op.add_column(
        'positions',
        sa.Column('ticket', sa.Integer(), nullable=True)
    )
    
    # Create indexes
    op.create_index('idx_position_confluence', 'positions', ['confluence_score'])
    op.create_index('idx_position_ticket', 'positions', ['ticket'], unique=True)
    
    # Add check constraint for confluence_score
    op.create_check_constraint(
        'check_position_confluence_range',
        'positions',
        'confluence_score >= 0 AND confluence_score <= 100'
    )


def downgrade() -> None:
    """Downgrade schema: Remove confluence_score and ticket fields from positions table."""
    # Drop check constraint
    op.drop_constraint('check_position_confluence_range', 'positions', type_='check')
    
    # Drop indexes
    op.drop_index('idx_position_ticket', 'positions')
    op.drop_index('idx_position_confluence', 'positions')
    
    # Drop columns
    op.drop_column('positions', 'ticket')
    op.drop_column('positions', 'confluence_score')
