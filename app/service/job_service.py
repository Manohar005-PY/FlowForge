from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.repositroy.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.redis.queue import Queue

from sqlalchemy.orm import Session


class JobService:
    def __init__(self, db: Session, jobrepository: JobRepository):
        self.db = db
        self.jobrepository = jobrepository

    def create_job(self, job_data: JobCreate, queue: Queue) -> Job:
        self.queue = queue
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        new_job = Job(
            type=job_data.type,
            payload=job_data.payload,
            status=JOB_STATUS.QUEUED,
            priority=job_data.priority,
            max_retries=job_data.max_retries,
            scheduled_at=job_data.scheduled_at,
            idempotency_key=job_data.idempotency_key,
        )
        new_job = self.jobrepository.create_job(new_job)
        if (
            new_job.status == JOB_STATUS.QUEUED
            and (new_job.scheduled_at is None or new_job.scheduled_at <= now)
        ):
            self.queue.enqueue(new_job.id)

        return new_job

    def get_the_job_by_id(self, job_id: int) -> Job | None:
        return self.jobrepository.get_job_by_id(job_id)

    def list_jobs(self, status: JOB_STATUS | str | None = None, limit: int = 50):
        return self.jobrepository.list_jobs(status=status, limit=limit)

    def cancel_job(self, job_id: int, reason: str | None = None) -> Job | None:
        return self.jobrepository.cancel_job(job_id, reason=reason)