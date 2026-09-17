from app.models.enum import JOB_STATUS




class JobExecutor():

    def execute(self,job):
        print(f"Executing the job{job.id}")
        print(f"Type: {job.type}")
        print(f"payload: {job.payload}")

        return{
            "status": JOB_STATUS.SUCCESS
        }