from app.models.enum import JOB_STATUS
import time




class JobExecutor():

    def execute(self,job):
        print(f"Executing the job{job.id}")
        time.sleep(30)
        print(f"Type: {job.type}")
        time.sleep(30)
        print(f"payload: {job.payload}")
        return{
            "status": JOB_STATUS.SUCCESS
        }