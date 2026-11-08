import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.db.session import SessionLocal
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.repositroy.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.service.job_service import JobService


class ScheduledPriorityTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.repository = JobRepository(self.db)
        self.repository.register_worker(1)

    def tearDown(self):
        self.db.query(Job).filter(Job.type.in_(["priority_job", "scheduled_job"])) .delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_next_ready_job_prefers_highest_priority_due_jobs(self):
        now = datetime.now(timezone.utc)
        low = Job(
            type="priority_job",
            payload={"value": "low"},
            status=JOB_STATUS.QUEUED,
            priority=1,
            scheduled_at=now - timedelta(minutes=5),
        )
        high = Job(
            type="priority_job",
            payload={"value": "high"},
            status=JOB_STATUS.QUEUED,
            priority=7,
            scheduled_at=now - timedelta(minutes=2),
        )
        future = Job(
            type="priority_job",
            payload={"value": "future"},
            status=JOB_STATUS.QUEUED,
            priority=999,
            scheduled_at=now + timedelta(minutes=30),
        )
        low = self.repository.create_job(low)
        high = self.repository.create_job(high)
        future = self.repository.create_job(future)

        claimed = self.repository.claim_next_ready_job(worker_id=1)

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.id, high.id)
        self.assertEqual(claimed.status, JOB_STATUS.RUNNING)
        self.assertNotEqual(claimed.id, future.id)
        self.assertNotEqual(claimed.id, low.id)

    def test_future_scheduled_jobs_are_not_enqueued_until_due(self):
        queue = Mock()
        service = JobService(self.db, self.repository)
        scheduled = JobCreate(
            type="scheduled_job",
            payload={"value": "later"},
            scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            priority=5,
        )

        saved = service.create_job(scheduled, queue)

        self.assertEqual(saved.status, JOB_STATUS.QUEUED)
        queue.enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
