import unittest
from types import SimpleNamespace

from app.models.enum import JOB_STATUS
from app.worker.executor import JobExecutor


class ExecutorHandlerTests(unittest.TestCase):
    def test_executor_selects_registered_handler_by_job_type(self):
        executor = JobExecutor()

        email_job = SimpleNamespace(
            id=1,
            type="email",
            payload={"to": "ops@example.com", "subject": "welcome", "body": "hello"},
        )
        report_job = SimpleNamespace(
            id=2,
            type="report",
            payload={"report_name": "daily-summary", "rows": 20},
        )

        email_result = executor.execute(email_job)
        report_result = executor.execute(report_job)

        self.assertEqual(email_result["status"], JOB_STATUS.SUCCESS)
        self.assertEqual(report_result["status"], JOB_STATUS.SUCCESS)
        self.assertEqual(email_result["recipient"], "ops@example.com")
        self.assertEqual(report_result["report_name"], "daily-summary")

    def test_executor_reuses_cached_idempotent_result_for_duplicate_delivery(self):
        executor = JobExecutor()
        job = SimpleNamespace(
            id=99,
            type="email",
            payload={
                "idempotency_key": "welcome-email-42",
                "to": "user@example.com",
                "subject": "welcome",
                "body": "hi",
            },
        )

        first = executor.execute(job)
        second = executor.execute(job)

        self.assertEqual(first["status"], JOB_STATUS.SUCCESS)
        self.assertEqual(second["status"], JOB_STATUS.SUCCESS)
        self.assertTrue(second.get("idempotent", False))
        self.assertEqual(first["message_id"], second["message_id"])

    def test_executor_rejects_unknown_job_type(self):
        executor = JobExecutor()
        job = SimpleNamespace(id=3, type="missing", payload={})

        with self.assertRaises(ValueError):
            executor.execute(job)


if __name__ == "__main__":
    unittest.main()
