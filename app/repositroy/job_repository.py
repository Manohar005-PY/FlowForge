from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.job import Job
from app.models.enum import JOB_STATUS
from datetime import datetime


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

    def update_status(self,job_id:int,status:JOB_STATUS):
        job = self.get_job_by_id(job_id)
        if job is not None:
            job.status = status
            if status is JOB_STATUS.QUEUED:
                job.scheduled_at = datetime.now()
            if status is JOB_STATUS.SUCCESS:
                job.completed_at = datetime.now()
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)