"""add lease expiry tracking to jobs

Revision ID: 8b3d1ec3a5d3
Revises: 522668470244
Create Date: 2026-11-08 22:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b3d1ec3a5d3'
down_revision: Union[str, Sequence[str], None] = '522668470244'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_jobs_lease_expires_at', 'jobs', ['lease_expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobs_lease_expires_at', table_name='jobs')
    op.drop_column('jobs', 'lease_expires_at')
