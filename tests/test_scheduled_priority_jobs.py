import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.db.session import SessionLocal
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.redis.queue import Queue
from app.redis.redis import redis_conn
from app.repositroy.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.service.job_service import JobService


class ScheduledPriorityTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.repository = JobRepository(self.db)
        self.repository.register_worker(1)

    def tearDown(self):
        self.db.query(Job).delete(synchronize_session=False)
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

    def test_scheduler_enqueues_only_due_jobs_once(self):
        now = datetime.now(timezone.utc)
        queue = Mock()
        due = Job(
            type="scheduled_job",
            payload={"value": "due"},
            status=JOB_STATUS.QUEUED,
            priority=2,
            scheduled_at=now - timedelta(minutes=1),
        )
        future = Job(
            type="scheduled_job",
            payload={"value": "future"},
            status=JOB_STATUS.QUEUED,
            priority=9,
            scheduled_at=now + timedelta(minutes=30),
        )
        due = self.repository.create_job(due)
        future = self.repository.create_job(future)

        enqueued = self.repository.enqueue_due_jobs(queue)

        self.assertEqual(len(enqueued), 1)
        self.assertEqual(enqueued[0].id, due.id)
        self.assertEqual(self.repository.get_job_by_id(due.id).status, JOB_STATUS.PENDING)
        self.assertEqual(self.repository.get_job_by_id(future.id).status, JOB_STATUS.QUEUED)
        queue.enqueue.assert_called_once_with(due.id)

    def test_queue_respects_timeout_when_waiting_for_work(self):
        queue = Queue(redis_conn, f"queue_timeout_{datetime.now(timezone.utc).timestamp()}")
        redis_conn.delete(queue.queue_name)

        start = datetime.now(timezone.utc)
        self.assertIsNone(queue.dequeue(timeout=1))
        self.assertGreaterEqual((datetime.now(timezone.utc) - start).total_seconds(), 0.9)


if __name__ == "__main__":
    unittest.main()
