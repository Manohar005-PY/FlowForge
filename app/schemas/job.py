from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Any
from app.models.enum import JOB_STATUS


class JobCreate(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    max_retries: int = 5
    scheduled_at: datetime | None = None
    idempotency_key: str | None = None


class JobResponse(BaseModel):
    id: int
    type: str
    payload: dict[str, Any]
    status: JOB_STATUS
    priority: int = 0
    attempt_count: int = 0
    max_retries: int = 5
    idempotency_key: str | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    scheduled_at: datetime | None
    started_at: datetime | None
    lease_expires_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    worker_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobGet(BaseModel):
    id: int
