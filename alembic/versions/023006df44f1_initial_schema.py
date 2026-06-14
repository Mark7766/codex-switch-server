"""initial_schema

Revision ID: 023006df44f1
Revises: 
Create Date: 2026-06-08 10:27:48.766356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '023006df44f1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create all tables via SQLAlchemy metadata
    from src.models.base import Base

    conn = op.get_bind()
    Base.metadata.create_all(bind=conn)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    Base = __import__('src.models.base', fromlist=['Base']).Base
    conn = op.get_bind()
    Base.metadata.drop_all(bind=conn)
    # ### end Alembic commands ###
