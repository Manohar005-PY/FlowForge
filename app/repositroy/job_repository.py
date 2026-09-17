from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.job import Job


class JobRepository():
    def __init__(self,db:Session) -> None:
        self.db = db

    def create_job(self, job:Job) -> Job:
        self.db.add(job)
        self.db.flush()
        self.db.refresh(job)
        return job
    
    def get_job_by_id(self,job_id:int) -> Job | None:
        query = select(Job).where(Job.id == job_id)
        result = self.db.execute(query)
        job = result.scalar_one_or_none()
        return job