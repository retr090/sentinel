"""github onion feed metadata

Revision ID: 0a1b2c3d4e5f
Revises: f8b9c0d1e2f3
Create Date: 2026-05-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0a1b2c3d4e5f'
down_revision: Union[str, None] = 'f8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('darkweb_onion_targets', sa.Column('source_file', sa.String(length=300), nullable=True))
    op.add_column('darkweb_onion_targets', sa.Column('risk_type', sa.String(length=50), nullable=True))
    op.add_column('darkweb_onion_targets', sa.Column('onion_host', sa.String(length=300), nullable=True))
    op.add_column('darkweb_onion_targets', sa.Column('imported_at', sa.DateTime(), nullable=True))
    op.add_column('darkweb_target_scan_results', sa.Column('response_headers', sa.JSON(), nullable=True))
    op.create_index('idx_onion_target_repo', 'darkweb_onion_targets', ['source_repo'], unique=False)
    op.create_index('idx_onion_target_risk_type', 'darkweb_onion_targets', ['risk_type'], unique=False)
    op.execute("UPDATE darkweb_onion_targets SET imported_at = COALESCE(imported_at, created_at, last_seen)")
    op.execute("UPDATE darkweb_onion_targets SET risk_type = COALESCE(risk_type, 'unknown')")


def downgrade() -> None:
    op.drop_index('idx_onion_target_risk_type', table_name='darkweb_onion_targets')
    op.drop_index('idx_onion_target_repo', table_name='darkweb_onion_targets')
    op.drop_column('darkweb_target_scan_results', 'response_headers')
    op.drop_column('darkweb_onion_targets', 'imported_at')
    op.drop_column('darkweb_onion_targets', 'onion_host')
    op.drop_column('darkweb_onion_targets', 'risk_type')
    op.drop_column('darkweb_onion_targets', 'source_file')
