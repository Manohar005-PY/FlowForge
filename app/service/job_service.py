from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.repositroy.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.redis.queue import Queue

from sqlalchemy.orm import Session

class JobService():
    def __init__(self,db:Session, jobrepository:JobRepository,queue:Queue):
        self.db = db
        self.jobrepository = jobrepository
        self.queue = queue

    def create_job(self, job_data: JobCreate) -> Job:
        new_job = Job(
            type=job_data.type,
            payload=job_data.payload,
            status=JOB_STATUS.QUEUED,
        )
        with self.db.begin():
            new_job = self.jobrepository.create_job(new_job)
            self.queue.enqueue(new_job.id)

        return new_job