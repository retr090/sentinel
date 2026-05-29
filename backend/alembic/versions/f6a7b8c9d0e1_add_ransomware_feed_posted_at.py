"""add ransomware feed posted timestamp

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('darkweb_mentions', sa.Column('feed_posted_at', sa.DateTime(), nullable=True))
    op.execute(
        """
        UPDATE darkweb_mentions
        SET feed_posted_at = COALESCE(
            published_at,
            NULLIF(raw_data->>'published', '')::timestamp,
            NULLIF(raw_data->>'published_at', '')::timestamp,
            NULLIF(raw_data->>'posted_at', '')::timestamp,
            NULLIF(raw_data->>'post_date', '')::timestamp,
            NULLIF(raw_data->>'date', '')::timestamp,
            NULLIF(raw_data->>'attackdate', '')::timestamp,
            discovered_at
        )
        WHERE source = 'ransomware_live'
          AND keyword_matched != 'global_tracker'
          AND feed_posted_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column('darkweb_mentions', 'feed_posted_at')
