import uuid
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import DateTime, UUID

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import Job

class Worker(Base):
    __tablename__ = "workers"

    id:Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="worker"
    )
    last_heartbeat:Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )