import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.models.job import Job
from app.models.worker import Worker
from app.models.enum import JOB_STATUS
from datetime import datetime, timedelta, timezone


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _commit_and_refresh(self):
        self.db.commit()
        self.db.expire_all()

    @staticmethod
    def normalize_worker_id(worker_id: uuid.UUID | int | str | None) -> uuid.UUID:
        if worker_id is None:
            return uuid.uuid4()
        if isinstance(worker_id, uuid.UUID):
            return worker_id
        if isinstance(worker_id, int):
            if worker_id < 0:
                return uuid.uuid4()
            try:
                return uuid.UUID(int=worker_id)
            except (ValueError, OverflowError):
                return uuid.uuid4()
        if isinstance(worker_id, str):
            try:
                return uuid.UUID(worker_id)
            except ValueError:
                return uuid.uuid4()
        try:
            return uuid.UUID(str(worker_id))
        except (ValueError, TypeError, AttributeError):
            return uuid.uuid4()

    def create_job(self, job: Job) -> Job:
        if job.idempotency_key:
            existing = self.db.execute(
                select(Job).where(Job.idempotency_key == job.idempotency_key)
            ).scalar_one_or_none()
            if existing is not None:
                return existing
        if job.status == JOB_STATUS.QUEUED and job.scheduled_at is None:
            job.scheduled_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.flush()
        self.db.refresh(job)
        self._commit_and_refresh()
        return job

    def register_worker(self, worker_id: uuid.UUID | int | str | None) -> Worker:
        worker_id = self.normalize_worker_id(worker_id)

        existing = self.db.get(Worker, worker_id)
        if existing is not None:
            return existing

        worker = Worker(id=worker_id)
        self.db.add(worker)
        self._commit_and_refresh()
        self.db.refresh(worker)
        return worker

    def claim_job(self, job_id: int, worker_id: uuid.UUID | int | str | None, lease_seconds: int = 60) -> Job | None:
        normalized_worker = self.normalize_worker_id(worker_id)

        if self.db.get(Worker, normalized_worker) is None:
            return None

        now = datetime.now(timezone.utc)
        lease_expires_at = now + timedelta(seconds=lease_seconds)

        update_stmt = (
            update(Job)
            .where(Job.id == job_id)
            .where(Job.status.in_([JOB_STATUS.QUEUED.value, JOB_STATUS.PENDING.value]))
            .where((Job.scheduled_at.is_(None)) | (Job.scheduled_at <= now))
            .where((Job.lease_expires_at.is_(None)) | (Job.lease_expires_at <= now))
            .values(
                status=JOB_STATUS.RUNNING.value,
                worker_id=normalized_worker,
                started_at=now,
                lease_expires_at=lease_expires_at,
                updated_at=now,
            )
        )
        result = self.db.execute(update_stmt)
        if result.rowcount == 0:
            return None
        self._commit_and_refresh()
        return self.get_job_by_id(job_id)

    def claim_next_ready_job(self, worker_id: uuid.UUID | int | str | None, lease_seconds: int = 60) -> Job | None:
        normalized_worker = self.normalize_worker_id(worker_id)
        if self.db.get(Worker, normalized_worker) is None:
            return None

        now = datetime.now(timezone.utc)
        ready_query = (
            select(Job)
            .where(Job.status.in_([JOB_STATUS.QUEUED.value, JOB_STATUS.PENDING.value]))
            .where((Job.scheduled_at.is_(None)) | (Job.scheduled_at <= now))
            .where((Job.lease_expires_at.is_(None)) | (Job.lease_expires_at <= now))
            .where(Job.cancellation_reason.is_(None))
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(1)
        )
        job = self.db.execute(ready_query).scalar_one_or_none()
        if job is None:
            return None

        return self.claim_job(job.id, normalized_worker, lease_seconds=lease_seconds)

    def enqueue_due_jobs(self, queue, limit: int = 100) -> list[Job]:
        now = datetime.now(timezone.utc)
        due_jobs = self.db.execute(
            select(Job)
            .where(Job.status == JOB_STATUS.QUEUED.value)
            .where((Job.scheduled_at.is_(None)) | (Job.scheduled_at <= now))
            .where(Job.cancellation_reason.is_(None))
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(limit)
        ).scalars().all()

        for job in due_jobs:
            queue.enqueue(job.id)
            job.status = JOB_STATUS.PENDING
            job.updated_at = now
            self.db.add(job)

        if due_jobs:
            self._commit_and_refresh()
        return due_jobs

    def release_job_lease(self, job_id: int, worker_id: uuid.UUID | None = None) -> Job | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None
        if worker_id is not None and job.worker_id != worker_id:
            return None
        job.lease_expires_at = None
        self.db.add(job)
        self._commit_and_refresh()
        self.db.refresh(job)
        return job

    def recover_expired_jobs(self, lease_seconds: int = 60) -> list[Job]:
        now = datetime.now(timezone.utc)
        expired_query = select(Job).where(
            Job.status == JOB_STATUS.RUNNING.value,
            Job.lease_expires_at.is_not(None),
            Job.lease_expires_at <= now,
        )
        expired_jobs = self.db.execute(expired_query).scalars().all()
        for job in expired_jobs:
            job.status = JOB_STATUS.QUEUED
            job.lease_expires_at = None
            job.worker_id = None
            job.updated_at = now
            if job.started_at is None:
                job.started_at = now
            self.db.add(job)
        self._commit_and_refresh()
        return expired_jobs

    def list_jobs(self, status: JOB_STATUS | str | None = None, limit: int = 50):
        query = select(Job).order_by(Job.created_at.desc())
        if status is not None:
            status_value = status.value if isinstance(status, JOB_STATUS) else status
            query = query.where(Job.status == status_value)
        return self.db.execute(query.limit(limit)).scalars().all()

    def cancel_job(self, job_id: int, reason: str | None = None) -> Job | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None
        if job.status in {JOB_STATUS.SUCCESS, JOB_STATUS.FAILED, JOB_STATUS.CANCELLED}:
            return job
        job.status = JOB_STATUS.CANCELLED
        job.cancellation_reason = reason or "Cancelled by request"
        job.cancelled_at = datetime.now(timezone.utc)
        job.completed_at = job.cancelled_at
        job.lease_expires_at = None
        self.db.add(job)
        self._commit_and_refresh()
        self.db.refresh(job)
        return job

    def get_job_by_id(self, job_id: int) -> Job | None:
        query = select(Job).where(Job.id == job_id)
        result = self.db.execute(query)
        job = result.scalar_one_or_none()
        return job

    def update_status(self, job_id: int, status: JOB_STATUS):
        job = self.get_job_by_id(job_id)
        if job is not None:
            job.status = status
            now = datetime.now(timezone.utc)
            if status == JOB_STATUS.QUEUED:
                if job.scheduled_at is None:
                    job.scheduled_at = now
                job.lease_expires_at = None
                job.worker_id = None
            if status == JOB_STATUS.RUNNING and job.started_at is None:
                job.started_at = now
            if status == JOB_STATUS.RUNNING:
                job.lease_expires_at = now + timedelta(minutes=1)
            if status in (JOB_STATUS.SUCCESS, JOB_STATUS.FAILED, JOB_STATUS.CANCELLED):
                job.completed_at = now
                job.lease_expires_at = None
                if status == JOB_STATUS.CANCELLED:
                    job.cancelled_at = now
                    job.cancellation_reason = job.cancellation_reason or "Cancelled"
            if status == JOB_STATUS.FAILED and job.error_message is None:
                job.error_message = "Job execution failed."
            if status == JOB_STATUS.SUCCESS and job.result is None:
                job.result = {}
            self.db.add(job)
            self._commit_and_refresh()
            self.db.refresh(job)

    def update_attempt_count(self, job_id: int) -> Job | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None
        job.attempt_count = job.attempt_count + 1

        self.db.add(job)
        self._commit_and_refresh()
        self.db.refresh(job)
        return job

    def update_worker(self, job_id: int, worker_id: uuid.UUID | int | str | None) -> Job | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None

        if worker_id is not None:
            worker_id = self.normalize_worker_id(worker_id)
            if self.db.get(Worker, worker_id) is None:
                return None

        job.worker_id = worker_id
        self.db.add(job)
        self._commit_and_refresh()
        self.db.refresh(job)
        return job

    def update_heartbeat(self, worker_id: uuid.UUID | int | str | None) -> None:
        normalized_worker = self.normalize_worker_id(worker_id)
        worker = self.db.get(Worker, normalized_worker)
        if worker is not None:
            worker.last_heartbeat = datetime.now(timezone.utc)
            self.db.add(worker)
            self._commit_and_refresh()