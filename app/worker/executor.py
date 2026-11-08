from __future__ import annotations

from typing import Any

from app.models.enum import JOB_STATUS
from app.worker.handlers import BaseJobHandler, EmailJobHandler, ReportJobHandler


class JobExecutor:
    def __init__(self, handlers: list[BaseJobHandler] | None = None):
        self._handlers: dict[str, BaseJobHandler] = {}
        for handler in handlers or [EmailJobHandler(), ReportJobHandler()]:
            self.register(handler)
        self._idempotency_cache: dict[str, dict[str, Any]] = {}

    def register(self, handler: BaseJobHandler) -> None:
        self._handlers[handler.job_type] = handler

    def _resolve_handler(self, job_type: str) -> BaseJobHandler:
        handler = self._handlers.get(job_type)
        if handler is None:
            raise ValueError(f"No job handler registered for type '{job_type}'.")
        return handler

    def _idempotency_key(self, job: Any) -> str | None:
        payload = job.payload or {}
        if not isinstance(payload, dict):
            return None
        if "idempotency_key" in payload:
            return f"{job.type}:{payload['idempotency_key']}"
        return f"{job.type}:{job.id}"

    def execute(self, job):
        handler = self._resolve_handler(job.type)
        validated_payload = handler.validate_payload(job.payload)
        idempotency_key = self._idempotency_key(job)

        if idempotency_key is not None and idempotency_key in self._idempotency_cache:
            return {
                "status": JOB_STATUS.SUCCESS,
                "idempotent": True,
                **self._idempotency_cache[idempotency_key],
            }

        result = handler.execute(validated_payload)
        result["status"] = JOB_STATUS.SUCCESS
        if idempotency_key is not None:
            self._idempotency_cache[idempotency_key] = result
        return result