"""add updated_at to jobs

Revision ID: 8f2c1e7a9b6d
Revises: 41d94bdd87fe
Create Date: 2026-09-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f2c1e7a9b6d"
down_revision: Union[str, Sequence[str], None] = "41d94bdd87fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "updated_at")