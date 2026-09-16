from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.job import Job
from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.service.job_service import JobService
from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue
from app.redis.redis import redis_conn

job = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)

@job.post("/", response_model=JobResponse)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)) -> Job:
    repository = JobRepository(db)
    queue = Queue(redis_conn)
    service = JobService(db, repository,queue)
    return service.create_job(job_data)