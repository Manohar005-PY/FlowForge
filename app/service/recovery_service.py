import logging
import threading
from time import sleep

from app.models.enum import JOB_STATUS
from app.repositroy.job_repository import JobRepository

logger = logging.getLogger(__name__)


class RecoveryService:
    def __init__(self, repository: JobRepository, lease_seconds: int = 60):
        self.repository = repository
        self.lease_seconds = lease_seconds

    def recover_expired_jobs(self):
        expired = self.repository.recover_expired_jobs(self.lease_seconds)
        for job in expired:
            logger.warning(
                "Recovered expired job %s from stale lease; requeued for retry.",
                job.id,
            )
        return expired

    def recover_and_requeue_if_needed(self):
        expired = self.repository.recover_expired_jobs(self.lease_seconds)
        for job in expired:
            if job.attempt_count >= job.max_retries:
                self.repository.update_status(job.id, JOB_STATUS.FAILED)
            else:
                self.repository.update_status(job.id, JOB_STATUS.QUEUED)
        return expired


class RecoveryWorker:
    def __init__(
        self,
        repository: JobRepository | None = None,
        session_factory=None,
        lease_seconds: int = 60,
        interval_seconds: int = 15,
    ):
        self.repository = repository
        self.session_factory = session_factory
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        if self.repository is None and self.session_factory is None:
            return
        self._thread = threading.Thread(target=self.run, daemon=True, name="flowforge-recovery")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 1)

    def run(self):
        while not self._stop_event.is_set():
            try:
                if self.repository is not None:
                    service = RecoveryService(self.repository, lease_seconds=self.lease_seconds)
                    service.recover_expired_jobs()
                elif self.session_factory is not None:
                    with self.session_factory() as db:
                        service = RecoveryService(JobRepository(db), lease_seconds=self.lease_seconds)
                        service.recover_expired_jobs()
            except Exception:
                logger.exception("Recovery worker encountered an unexpected failure.")
            self._stop_event.wait(self.interval_seconds)
