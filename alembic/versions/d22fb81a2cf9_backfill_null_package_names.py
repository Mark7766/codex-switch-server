"""backfill_null_package_names

Revision ID: d22fb81a2cf9
Revises: 023006df44f1
Create Date: 2026-06-08 10:28:27.047622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd22fb81a2cf9'
down_revision: Union[str, Sequence[str], None] = '023006df44f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill NULL package_name to 'codex-switch' for old download records."""
    op.execute(
        "UPDATE download_records SET package_name = 'codex-switch' "
        "WHERE package_name IS NULL OR package_name = ''"
    )


def downgrade() -> None:
    """No-op: backfill is not reversible."""
    pass
