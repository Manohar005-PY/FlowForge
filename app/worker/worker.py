from app.repositroy.job_repository import JobRepository
from app.redis.queue import Queue
from app.worker.executor import JobExecutor
from app.models.enum import JOB_STATUS
from sqlalchemy.orm import Session


class Worker():
    def __init__(
            self,
            queue:Queue, repository:JobRepository, executor:JobExecutor, 
            worker_id:int
    ):
        self.worker_id = worker_id
        self.queue = queue
        self.repository = repository
        self.executor =  executor

    def run(self):
        while True:
            job_id = self.queue.dequeue()
            self.process_job(job_id)

    def process_job(self,job_id):
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            return
        self.repository.update_status(job_id,JOB_STATUS.RUNNING)

        try:
            status = self.executor.execute(job)

            self.repository.update_status(job.id,JOB_STATUS.SUCCESS)
        except Exception:
            self.repository.update_status(job.id,JOB_STATUS.FAILED)
