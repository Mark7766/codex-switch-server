"""add_delivery_to_download_records

Revision ID: b32a1f982dc5
Revises: d22fb81a2cf9
Create Date: 2026-06-16 13:52:49.509980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b32a1f982dc5'
down_revision: Union[str, Sequence[str], None] = 'd22fb81a2cf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    try:
        op.add_column('download_records', sa.Column('delivery', sa.String(length=16), nullable=False, server_default=''))
    except Exception:
        pass  # column already exists (new DBs via create_all)


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_column('download_records', 'delivery')
    except Exception:
        pass
