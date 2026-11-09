import logging
import threading
from datetime import datetime, timezone

from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, repository: JobRepository, queue: Queue, batch_size: int = 100):
        self.repository = repository
        self.queue = queue
        self.batch_size = batch_size

    def enqueue_due_jobs(self):
        due_jobs = self.repository.enqueue_due_jobs(self.queue, limit=self.batch_size)
        for job in due_jobs:
            logger.info("Scheduled job %s for dispatch at %s", job.id, datetime.now(timezone.utc))
        return due_jobs


class SchedulerWorker:
    def __init__(
        self,
        queue: Queue,
        repository: JobRepository | None = None,
        session_factory=None,
        interval_seconds: int = 5,
        batch_size: int = 100,
    ):
        self.queue = queue
        self.repository = repository
        self.session_factory = session_factory
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        if self.queue is None:
            return
        self._thread = threading.Thread(
            target=self.run,
            daemon=True,
            name="flowforge-scheduler",
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 1)

    def run(self):
        while not self._stop_event.is_set():
            try:
                if self.repository is not None:
                    service = SchedulerService(self.repository, self.queue, batch_size=self.batch_size)
                    service.enqueue_due_jobs()
                elif self.session_factory is not None:
                    with self.session_factory() as db:
                        service = SchedulerService(JobRepository(db), self.queue, batch_size=self.batch_size)
                        service.enqueue_due_jobs()
            except Exception:
                logger.exception("Scheduler worker encountered an unexpected failure.")
            self._stop_event.wait(self.interval_seconds)
