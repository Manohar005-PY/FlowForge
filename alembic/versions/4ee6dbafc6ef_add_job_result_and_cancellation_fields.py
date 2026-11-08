"""add idempotency/result/cancellation fields to jobs

Revision ID: 4ee6dbafc6ef
Revises: 8b3d1ec3a5d3
Create Date: 2026-11-08 22:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '4ee6dbafc6ef'
down_revision: Union[str, Sequence[str], None] = '8b3d1ec3a5d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('idempotency_key', sa.String(), nullable=True))
    op.add_column('jobs', sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('jobs', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_jobs_idempotency_key', 'jobs', ['idempotency_key'], unique=False)

    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    op.drop_index('ix_jobs_idempotency_key', table_name='jobs')
    op.drop_column('jobs', 'cancelled_at')
    op.drop_column('jobs', 'cancellation_reason')
    op.drop_column('jobs', 'error_message')
    op.drop_column('jobs', 'result')
    op.drop_column('jobs', 'idempotency_key')
