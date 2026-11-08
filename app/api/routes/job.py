from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.job import Job
from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.service.job_service import JobService
from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue
from app.redis.redis import redis_conn
from app.models.enum import JOB_STATUS

job = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@job.get("/", response_model=list[JobResponse])
def list_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    repository = JobRepository(db)
    service = JobService(db, repository)
    status_value = None if status is None else JOB_STATUS[status.upper()] if status.upper() in {s.name for s in JOB_STATUS} else status
    return service.list_jobs(status=status_value, limit=limit)


@job.post("/", response_model=JobResponse)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)) -> Job:
    repository = JobRepository(db)
    queue = Queue(redis_conn)
    service = JobService(db, repository)
    return service.create_job(job_data, queue)


@job.get("/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)) -> Job | None:
    repository = JobRepository(db)
    service = JobService(db, repository)
    job = service.get_the_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@job.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    repository = JobRepository(db)
    service = JobService(db, repository)
    job = service.cancel_job(job_id, reason="Cancelled via API")
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
