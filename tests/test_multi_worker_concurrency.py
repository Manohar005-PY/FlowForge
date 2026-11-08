import threading
import time
import unittest
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enum import JOB_STATUS
from app.models.job import Job
from app.redis.queue import Queue
from app.redis.redis import redis_conn
from app.repositroy.job_repository import JobRepository
from app.worker.worker import Worker


class FastExecutor:
    def execute(self, job):
        time.sleep(0.01)
        return {"ok": True}


class MultiWorkerConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.repository = JobRepository(self.db)
        self.queue = Queue(redis_conn, f"multi_worker_test_{uuid4().hex}")
        self.job_ids = []

        for index in range(30):
            job = Job(
                type="concurrency_test",
                payload={"index": index},
                status=JOB_STATUS.QUEUED,
                max_retries=2,
            )
            created = self.repository.create_job(job)
            self.queue.enqueue(created.id)
            self.job_ids.append(created.id)

    def tearDown(self):
        redis_conn.delete(self.queue.queue_name)
        for job_id in self.job_ids:
            self.db.query(Job).filter(Job.id == job_id).delete()
        self.db.commit()
        self.db.close()

    def _worker_loop(self, worker, jobs_to_claim):
        for _ in range(jobs_to_claim):
            job_id = self.queue.dequeue(timeout=1)
            if job_id is None:
                return
            worker.process_job(job_id)

    def test_three_workers_can_claim_jobs_without_conflicting_owners(self):
        workers = []
        for worker_index in range(3):
            worker_db = SessionLocal()
            worker_repo = JobRepository(worker_db)
            worker = Worker(
                queue=self.queue,
                repository=worker_repo,
                executor=FastExecutor(),
                worker_id=worker_index + 100,
            )
            workers.append((worker, worker_db))

        jobs_per_worker = len(self.job_ids) // len(workers)
        threads = []
        for worker, worker_db in workers:
            thread = threading.Thread(target=self._worker_loop, args=(worker, jobs_per_worker))
            thread.start()
            threads.append((thread, worker_db))

        for thread, worker_db in threads:
            thread.join()
            worker_db.close()

        rows = self.db.execute(
            select(Job).where(Job.id.in_(self.job_ids))
        ).scalars().all()

        self.assertEqual(len(rows), len(self.job_ids))
        self.assertEqual(
            len([job for job in rows if job.status == JOB_STATUS.SUCCESS]),
            len(self.job_ids),
        )
        self.assertEqual(redis_conn.llen(self.queue.queue_name), 0)


if __name__ == "__main__":
    unittest.main()
