"""add ransomware seen tracking

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('darkweb_mentions', sa.Column('analyst_seen_at', sa.DateTime(), nullable=True))
    op.execute(
        """
        UPDATE darkweb_mentions
        SET analyst_seen_at = COALESCE(discovered_at, CURRENT_TIMESTAMP)
        WHERE source = 'ransomware_live'
          AND keyword_matched != 'global_tracker'
          AND analyst_seen_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column('darkweb_mentions', 'analyst_seen_at')
