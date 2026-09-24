from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue
from app.redis.redis import redis_conn
from app.worker.executor import JobExecutor
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.db.session import SessionLocal

import logging
import uuid


logger = logging.getLogger(__name__)


class Worker():
    def __init__(
            self,
            queue:Queue, repository:JobRepository, executor:JobExecutor, 
            worker_id:int
    ):
        self.worker_id = uuid.uuid4()
        self.queue = queue
        self.repository = repository
        self.executor =  executor
        self.repository.register_worker(self.worker_id)

    def run(self):
        while True:
            job_id = self.queue.dequeue()
            if job_id is None:
                continue
            self.process_job(job_id)

    def process_job(self,job_id:int):
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            return
        self.repository.update_status(job_id,JOB_STATUS.RUNNING)
        self.repository.update_worker(job_id,self.worker_id)
        self.repository.update_attempt_count(job_id)

        try:
            self.executor.execute(job)
            self.repository.update_status(job.id,JOB_STATUS.SUCCESS)
        except Exception as exe:
            self.exception_handler(job, exe)

    def exception_handler(self, job:Job,exe: Exception):
        job_id = job.id
        max_retry = job.max_retries
        attempt = job.attempt_count
        logger.exception("Job %s failed on attempt %s", job_id, attempt)
        if attempt <= max_retry:
            self.repository.update_status(job_id, JOB_STATUS.QUEUED)
            self.queue.enqueue(job_id)
        else:
            self.repository.update_status(job_id,JOB_STATUS.FAILED)

def main() -> None:
    db = SessionLocal()
    try:
        worker = Worker(
            queue=Queue(redis_conn),
            repository=JobRepository(db),
            executor=JobExecutor(),
            worker_id=1,
        )
        worker.run()
    finally:
        db.close()


if __name__ == "__main__":
    main()
