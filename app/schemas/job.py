from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any
from app.models.enum import JOB_STATUS

class JobCreate(BaseModel):
    type:str
    payload:dict[str, Any]

class JobResponse(BaseModel):
    id:int
    type:str
    payload:dict[str, Any]
    status:JOB_STATUS
    created_at:datetime
    updated_at:datetime
    scheduled_at:datetime | None
    started_at:datetime | None
    completed_at:datetime | None

    model_config = ConfigDict(from_attributes=True)

class JobGet(BaseModel):
    id:int
