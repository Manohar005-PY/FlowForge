import unittest
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.repositroy.job_repository import JobRepository
from app.service.recovery_service import RecoveryService


class RecoveryServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.repository = JobRepository(self.db)
        self.db.query(Job).filter(Job.type == "recovery_test").delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(Job).filter(Job.type == "recovery_test").delete()
        self.db.commit()
        self.db.close()

    def test_recover_expired_jobs_requeues_stale_runs(self):
        job = Job(
            type="recovery_test",
            payload={"value": 1},
            status=JOB_STATUS.RUNNING,
            max_retries=3,
            attempt_count=1,
            started_at=datetime.now(timezone.utc),
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        self.db.add(job)
        self.db.commit(); self.db.refresh(job)

        recovered = RecoveryService(self.repository, lease_seconds=60).recover_expired_jobs()

        self.db.expire_all()
        refreshed = self.repository.get_job_by_id(job.id)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(refreshed.status, JOB_STATUS.QUEUED)
        self.assertIsNone(refreshed.worker_id)
        self.assertIsNone(refreshed.lease_expires_at)
        self.db.delete(refreshed)
        self.db.commit()

    def test_recover_and_requeue_if_needed_marks_failed_after_retry_limit(self):
        job = Job(
            type="recovery_test",
            payload={"value": 2},
            status=JOB_STATUS.RUNNING,
            max_retries=2,
            attempt_count=2,
            started_at=datetime.now(timezone.utc),
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        self.db.add(job)
        self.db.commit(); self.db.refresh(job)

        recovered = RecoveryService(self.repository, lease_seconds=60).recover_and_requeue_if_needed()

        self.db.expire_all()
        refreshed = self.repository.get_job_by_id(job.id)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(refreshed.status, JOB_STATUS.FAILED)
        self.db.delete(refreshed)
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
