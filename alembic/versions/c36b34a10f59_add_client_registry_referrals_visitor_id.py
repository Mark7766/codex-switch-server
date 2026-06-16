"""add_client_registry_referrals_visitor_id

Revision ID: c36b34a10f59
Revises: b32a1f982dc5
Create Date: 2026-06-16 23:27:52.356220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c36b34a10f59'
down_revision: Union[str, Sequence[str], None] = 'b32a1f982dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    try:
        op.create_table(
            'client_registry',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('client_id', sa.String(length=32), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('client_id'),
        )
    except Exception:
        pass
    try:
        op.create_table(
            'referrals',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('inviter_client_id', sa.String(length=32), nullable=False),
            sa.Column('invitee_client_id', sa.String(length=32), nullable=False),
            sa.Column('ip_hash', sa.String(length=64), nullable=False, server_default=''),
            sa.Column('matched_page_event_id', sa.Integer(), nullable=True),
            sa.Column('platform', sa.String(length=10), nullable=False, server_default=''),
            sa.Column('arch', sa.String(length=10), nullable=False, server_default=''),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('invitee_client_id'),
        )
        op.create_index('ix_referrals_inviter', 'referrals', ['inviter_client_id'], unique=False)
    except Exception:
        pass
    try:
        op.add_column('page_events', sa.Column('ref', sa.String(length=32), nullable=True))
        op.create_index('ix_page_events_ref', 'page_events', ['ref'], unique=False)
    except Exception:
        pass
    try:
        op.add_column('page_events', sa.Column('visitor_id', sa.String(length=16), nullable=False, server_default=''))
        op.create_index('ix_page_events_visitor_id', 'page_events', ['visitor_id'], unique=False)
    except Exception:
        pass
    try:
        op.add_column('telemetry_events', sa.Column('ip_hash', sa.String(length=64), nullable=False, server_default=''))
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_index('ix_referrals_inviter', table_name='referrals')
        op.drop_table('referrals')
    except Exception:
        pass
    try:
        op.drop_table('client_registry')
    except Exception:
        pass
    try:
        op.drop_index('ix_page_events_visitor_id', table_name='page_events')
        op.drop_column('page_events', 'visitor_id')
    except Exception:
        pass
    try:
        op.drop_column('telemetry_events', 'ip_hash')
    except Exception:
        pass
