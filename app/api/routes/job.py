from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.job import Job
from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.service.job_service import JobService
from app.repositroy.job_repository import JobRepository

job = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)

@job.post("/", response_model=JobResponse)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)) -> Job:
    repository = JobRepository(db)
    service = JobService(db, repository)
    return service.create_job(job_data)