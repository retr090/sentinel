"""backfill ransomware feed posted timestamp from raw data

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE darkweb_mentions
        SET feed_posted_at = COALESCE(
            NULLIF(raw_data->>'published', '')::timestamp,
            NULLIF(raw_data->>'published_at', '')::timestamp,
            NULLIF(raw_data->>'posted_at', '')::timestamp,
            NULLIF(raw_data->>'post_date', '')::timestamp,
            NULLIF(raw_data->>'date', '')::timestamp,
            NULLIF(raw_data->>'attackdate', '')::timestamp,
            feed_posted_at,
            published_at,
            discovered_at
        )
        WHERE source = 'ransomware_live'
          AND keyword_matched != 'global_tracker'
        """
    )


def downgrade() -> None:
    pass
