import logging
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call

from app.models.enum import JOB_STATUS
from app.worker.worker import Worker


class DeliberatelyFailingExecutor:
    def execute(self, job):
        raise RuntimeError("deliberate test failure")


def failing_job(max_retries=2):
    return SimpleNamespace(
        id=42,
        type="deliberate_failure",
        payload={"fail": True},
        attempt_count=0,
        max_retries=max_retries,
    )


class WorkerFailureTests(unittest.TestCase):
    def make_worker(self, job):
        repository = Mock()
        repository.get_job_by_id.return_value = job
        queue = Mock()
        return Worker(
            queue=queue,
            repository=repository,
            executor=DeliberatelyFailingExecutor(),
            worker_id=1,
        ), repository, queue

    def test_failure_logs_traceback_and_requeues_when_retries_remain(self):
        job = failing_job(max_retries=2)
        job.attempt_count = 1
        worker, repository, queue = self.make_worker(job)

        with self.assertLogs("app.worker.worker", level=logging.ERROR) as logs:
            worker.process_job(job.id)

        self.assertIn("Job 42 failed on attempt 1", logs.output[0])
        self.assertIn("RuntimeError: deliberate test failure", "\n".join(logs.output))
        repository.update_status.assert_has_calls([
            call(job.id, JOB_STATUS.RUNNING),
            call(job.id, JOB_STATUS.QUEUED),
        ])
        queue.enqueue.assert_called_once_with(job.id)

    def test_failure_is_marked_failed_when_retries_are_exhausted(self):
        job = failing_job(max_retries=2)
        job.attempt_count = 3
        worker, repository, queue = self.make_worker(job)

        worker.process_job(job.id)

        repository.update_status.assert_has_calls([
            call(job.id, JOB_STATUS.RUNNING),
            call(job.id, JOB_STATUS.FAILED),
        ])
        queue.enqueue.assert_not_called()

    def test_retry_count_allows_exactly_max_retries(self):
        job = failing_job(max_retries=2)
        worker, repository, queue = self.make_worker(job)

        for attempt in (1, 2):
            job.attempt_count = attempt
            worker.process_job(job.id)

        self.assertEqual(queue.enqueue.call_count, 2)
        self.assertEqual(
            repository.update_status.call_args_list,
            [
                call(job.id, JOB_STATUS.RUNNING),
                call(job.id, JOB_STATUS.QUEUED),
                call(job.id, JOB_STATUS.RUNNING),
                call(job.id, JOB_STATUS.QUEUED),
            ],
        )


if __name__ == "__main__":
    unittest.main()