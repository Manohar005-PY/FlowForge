from typing import Optional

class Queue:
    def __init__(self, redis_conn, queue_name: str = "job_queue") -> None:
        self.redis_conn = redis_conn
        self.queue_name = queue_name

    def enqueue(self, job_id: int) -> bool:
        self.redis_conn.rpush(self.queue_name, job_id)
        return True

    def dequeue(self, timeout:int = 0) -> Optional[int]:
        result = self.redis_conn.blpop(self.queue_name, timeout=timeout)

        if result is not None:
            _, job_id = result
            return int(job_id) 
        
        return None