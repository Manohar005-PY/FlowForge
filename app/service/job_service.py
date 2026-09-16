from app.models.job import Job
from app.repositroy.job_repository import JobRepository
from app.schemas.job import JobCreate

from sqlalchemy.orm import Session

class JobService():
    def __init__(self,db:Session, jobrepository:JobRepository):
        self.db = db
        self.jobrepository = jobrepository

    def create_job(self, job_data: JobCreate) -> Job:
        new_job = Job(
            type=job_data.type,
            payload=job_data.payload
        )
        with self.db.begin():
            new_job = self.jobrepository.create_job(new_job)

        return new_job