from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue
from app.redis.redis import redis_conn
from app.worker.executor import JobExecutor
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.db.session import SessionLocal
from app.service.recovery_service import RecoveryWorker

import logging
import uuid
import threading
import time


logger = logging.getLogger(__name__)


class Worker():
    def __init__(
            self,
            queue:Queue,
            executor:JobExecutor | None = None,
            session_factory=None,
            heartbeat_interval:int = 20,
            repository:JobRepository | None = None,
            worker_id:uuid.UUID | int | str | None = None
    ):
        self.queue = queue
        self.executor = executor or JobExecutor()
        self.session_factory = session_factory
        self.heartbeat_interval = heartbeat_interval
        self._stop_event = threading.Event()
        self.repository = repository
        self.worker_id = self._normalize_worker_id(worker_id)
        self._heartbeat_thread = None
        self.recovery_worker = RecoveryWorker(
            repository=self.repository,
            session_factory=self.session_factory,
        )

        if self.repository is not None:
            self.repository.register_worker(self.worker_id)
        elif self.session_factory is not None:
            with self.session_factory() as db:
                repo = JobRepository(db)
                repo.register_worker(self.worker_id)

    @staticmethod
    def _normalize_worker_id(worker_id):
        if worker_id is None:
            return uuid.uuid4()
        if isinstance(worker_id, uuid.UUID):
            return worker_id
        if isinstance(worker_id, int):
            if worker_id < 0:
                return uuid.uuid4()
            try:
                return uuid.UUID(int=worker_id)
            except (ValueError, OverflowError):
                return uuid.uuid4()
        if isinstance(worker_id, str):
            try:
                return uuid.UUID(worker_id)
            except ValueError:
                return uuid.uuid4()
        try:
            return uuid.UUID(str(worker_id))
        except (ValueError, TypeError, AttributeError):
            return uuid.uuid4()

    def start_heartbeat(self):
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        if self.session_factory is None and self.repository is None:
            return
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"heartbeat-{self.worker_id}"
        )
        self._heartbeat_thread.start()

    def run(self):
        self.start_heartbeat()
        self.recovery_worker.start()

        while not self._stop_event.is_set():
            job_id = self.queue.dequeue()
            if job_id is None:
                if self.repository is not None:
                    next_job = self.repository.claim_next_ready_job(self.worker_id)
                    if next_job is not None:
                        self.process_job(next_job.id)
                        continue
                elif self.session_factory is not None:
                    with self.session_factory() as db:
                        next_job = JobRepository(db).claim_next_ready_job(self.worker_id)
                        if next_job is not None:
                            self.process_job(next_job.id)
                            continue
                time.sleep(0.25)
                continue
            self.process_job(job_id)

    def stop(self):
        self._stop_event.set()
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=self.heartbeat_interval + 1)
        self.recovery_worker.stop()

    def process_job(self,job_id:int):
        repository = self.repository
        if repository is None and self.session_factory is not None:
            with self.session_factory() as db:
                repository = JobRepository(db)
                job = repository.claim_job(job_id, self.worker_id) if isinstance(repository, JobRepository) else repository.get_job_by_id(job_id)
                if job is None:
                    return
                if isinstance(repository, JobRepository):
                    repository.update_attempt_count(job_id)
                else:
                    repository.update_status(job_id,JOB_STATUS.RUNNING)
                    repository.update_worker(job_id,self.worker_id)
                    repository.update_attempt_count(job_id)

                try:
                    self.executor.execute(job)
                    repository.update_status(job.id,JOB_STATUS.SUCCESS)
                    if isinstance(repository, JobRepository):
                        repository.release_job_lease(job.id, self.worker_id)
                except Exception as exe:
                    self.exception_handler(job, exe,repository)
                return

        if repository is None:
            return

        if isinstance(repository, JobRepository):
            job = repository.claim_job(job_id, self.worker_id)
            if job is None:
                return
            repository.update_attempt_count(job_id)
        else:
            job = repository.get_job_by_id(job_id)
            if job is None:
                return
            repository.update_status(job_id,JOB_STATUS.RUNNING)
            repository.update_worker(job_id,self.worker_id)
            repository.update_attempt_count(job_id)

        try:
            self.executor.execute(job)
            repository.update_status(job.id,JOB_STATUS.SUCCESS)
            if isinstance(repository, JobRepository):
                repository.release_job_lease(job.id, self.worker_id)
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
                if self.repository is not None:
                    self.repository.update_heartbeat(self.worker_id)
                elif self.session_factory is not None:
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
