"""add news article relevance fields

Revision ID: b3c4d5e6f7a8
Revises: 0ffde9f96c48
Create Date: 2026-05-18 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = '0ffde9f96c48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('news_articles', sa.Column('relevance_score', sa.Float(), nullable=True))
    op.add_column('news_articles', sa.Column('relevance_label', sa.String(16), nullable=True))
    op.create_index('ix_news_articles_relevance_label', 'news_articles', ['relevance_label'])


def downgrade() -> None:
    op.drop_index('ix_news_articles_relevance_label', table_name='news_articles')
    op.drop_column('news_articles', 'relevance_label')
    op.drop_column('news_articles', 'relevance_score')
