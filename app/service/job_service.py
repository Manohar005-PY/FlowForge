from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.repositroy.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.redis.queue import Queue

from sqlalchemy.orm import Session

class JobService():
    def __init__(self,db:Session, jobrepository:JobRepository):
        self.db = db
        self.jobrepository = jobrepository

    def create_job(self, job_data: JobCreate,queue:Queue) -> Job:
        self.queue = queue
        new_job = Job(
            type=job_data.type,
            payload=job_data.payload,
            status=JOB_STATUS.QUEUED,
        )
        with self.db.begin():
            new_job = self.jobrepository.create_job(new_job)
            self.queue.enqueue(new_job.id)

        return new_job

    def get_the_job_by_id(self,job_id:int) -> Job | None:
        job = self.jobrepository.get_job_by_id(job_id)
        return job