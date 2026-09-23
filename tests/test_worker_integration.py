import unittest
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.redis.redis import redis_conn
from app.redis.queue import Queue
from app.repositroy.job_repository import JobRepository
from app.worker.worker import Worker


class DeliberatelyFailingExecutor:
    def execute(self, job):
        raise RuntimeError("integration deliberate failure")


class WorkerDatabaseRedisTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.repository = JobRepository(self.db)
        self.queue = Queue(redis_conn, f"worker_test_{uuid4().hex}")
        self.job = Job(
            type="deliberate_failure",
            payload={"fail": True},
            status=JOB_STATUS.QUEUED,
            max_retries=1,
        )
        self.job = self.repository.create_job(self.job)
        self.queue.enqueue(self.job.id)
        self.worker = Worker(
            queue=self.queue,
            repository=self.repository,
            executor=DeliberatelyFailingExecutor(),
            worker_id=1,
        )

    def tearDown(self):
        redis_conn.delete(self.queue.queue_name)
        self.db.query(Job).filter(Job.id == self.job.id).delete()
        self.db.commit()
        self.db.close()

    def read_job(self):
        self.db.expire_all()
        return self.db.execute(
            select(Job).where(Job.id == self.job.id)
        ).scalar_one()

    def test_retry_is_persisted_and_exhaustion_marks_job_failed(self):
        first_job_id = self.queue.dequeue()
        self.worker.process_job(first_job_id)

        retry_job = self.read_job()
        first_updated_at = retry_job.updated_at
        self.assertEqual(retry_job.status, JOB_STATUS.QUEUED)
        self.assertEqual(retry_job.attempt_count, 1)
        self.assertIsNone(retry_job.completed_at)
        self.assertEqual(self.queue.dequeue(), self.job.id)

        self.worker.process_job(self.job.id)

        failed_job = self.read_job()
        self.assertEqual(failed_job.status, JOB_STATUS.FAILED)
        self.assertEqual(failed_job.attempt_count, 2)
        self.assertIsNotNone(failed_job.completed_at)
        self.assertGreaterEqual(failed_job.updated_at, first_updated_at)
        self.assertEqual(redis_conn.llen(self.queue.queue_name), 0)


if __name__ == "__main__":
    unittest.main()