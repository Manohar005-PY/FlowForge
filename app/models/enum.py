from enum import Enum

class JOB_STATUS(Enum):
    PENDING = "PENDING"
    QUEUED= "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"