from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, func, Enum
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
from app.models.enum import JOB_STATUS

class Job(Base):
    __tablename__ = "jobs"

    id:Mapped[int] = mapped_column(
        primary_key=True
    )
    type:Mapped[str] = mapped_column(
        nullable=False
    )
    payload:Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False
    )
    status:Mapped[JOB_STATUS] = mapped_column(
        Enum(JOB_STATUS),
        nullable=False,
        default=JOB_STATUS.PENDING
    )
    priority:Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    attempt_count:Mapped[int] = mapped_column(
        nullable=False,
        default=0
    )
    max_retries:Mapped[int] = mapped_column(
        nullable=False,
        default=5
    )
    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    scheduled_at:Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    started_at:Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at:Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )