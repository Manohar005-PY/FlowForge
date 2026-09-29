from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue
from app.redis.redis import redis_conn
from app.worker.executor import JobExecutor
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.db.session import SessionLocal

import logging
import uuid
import threading


logger = logging.getLogger(__name__)


class Worker():
    def __init__(
            self,
            queue:Queue,  
            executor:JobExecutor, 
            session_factory,
            heartbeat_interval:int = 20
    ):
        self.queue = queue
        self.executor =  executor
        self.worker_id = uuid.uuid4()
        self.session_factory = session_factory
        self.heartbeat_interval = heartbeat_interval
        self._stop_event = threading.Event()

        with self.session_factory() as db:
            repo = JobRepository(db)
            repo.register_worker(self.worker_id)

    def run(self):
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"heartbeat-{self.worker_id}"
        )
        while True:
            job_id = self.queue.dequeue()
            if job_id is None:
                continue
            self.process_job(job_id)

    def process_job(self,job_id:int):
        with self.session_factory() as db:
            repository = JobRepository(db)
            job = repository.get_job_by_id(job_id)
            if job is None:
                return
            repository.update_status(job_id,JOB_STATUS.RUNNING)
            repository.update_worker(job_id,self.worker_id)
            repository.update_attempt_count(job_id)

            try:
                self.executor.execute(job)
                repository.update_status(job.id,JOB_STATUS.SUCCESS)
            except Exception as exe:
                self.exception_handler(job, exe,repository)

    def exception_handler(self, job:Job,exe: Exception,repository:JobRepository):
        job_id = job.id
        max_retry = job.max_retries
        attempt = job.attempt_count
        logger.exception("Job %s failed on attempt %s", job_id, attempt)
        if attempt <= max_retry:
            repository.update_status(job_id, JOB_STATUS.QUEUED)
            self.queue.enqueue(job_id)
        else:
            repository.update_status(job_id,JOB_STATUS.FAILED)

    def _heartbeat_loop(self):
        while not self._stop_event.is_set():
            try:
                with self.session_factory() as db:
                    JobRepository(db).update_heartbeat(self.worker_id)
                    logger.debug("heartbeat sent for worker %s", self.worker_id)
            except Exception:
                logger.exception("Heartbeat failed for worker %s", self.worker_id)
            self._stop_event.wait(self.heartbeat_interval)


def main() -> None:
        worker = Worker(
            queue=Queue(redis_conn),
            executor=JobExecutor(),
            session_factory=SessionLocal
        )
        worker.run()


if __name__ == "__main__":
    main()
