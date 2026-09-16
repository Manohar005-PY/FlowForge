from sqlalchemy.orm import Session

from app.models.job import Job


class JobRepository():
    def __init__(self,db:Session) -> None:
        self.db = db

    def create_job(self, job:Job) -> Job:
        self.db.add(job)
        self.db.flush()
        self.db.refresh(job)
        return job
    