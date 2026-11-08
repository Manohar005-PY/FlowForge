from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseJobHandler(ABC):
    job_type: str

    def validate_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError(f"Job payload for {self.job_type} must be a dictionary.")
        return payload

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class EmailJobHandler(BaseJobHandler):
    job_type = "email"

    def validate_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = super().validate_payload(payload)
        missing = [field for field in ("to", "subject", "body") if field not in payload]
        if missing:
            raise ValueError(f"Email job payload missing required fields: {', '.join(missing)}")
        return payload

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "sent",
            "recipient": payload["to"],
            "subject": payload["subject"],
            "message_id": f"email:{payload['to']}:{payload['subject']}",
        }


class ReportJobHandler(BaseJobHandler):
    job_type = "report"

    def validate_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = super().validate_payload(payload)
        if "report_name" not in payload:
            raise ValueError("Report job payload must include 'report_name'.")
        return payload

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "generated",
            "report_name": payload["report_name"],
            "rows": payload.get("rows", 0),
        }
