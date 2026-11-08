# FlowForge

FlowForge is a distributed background job processing system built with Python, FastAPI, PostgreSQL, SQLAlchemy, and Redis. The project focuses on reliable job submission, queue-based delivery, distributed execution, retries, and worker lifecycle tracking.

## Current architecture

### API layer
- FastAPI app created in `app/main.py`
- Job routes in `app/api/routes/job.py`
- Pydantic schemas in `app/schemas/job.py`

### Service and repository layers
- `app/service/job_service.py` handles business operations for job creation and lookup.
- `app/repositroy/job_repository.py` persists job and worker state in PostgreSQL.

### Database model
- `app/models/job.py` defines job lifecycle and execution metadata.
- `app/models/worker.py` defines worker registration and heartbeat tracking.
- `app/models/enum.py` defines the job state enum.

### Queue layer
- Redis connection setup in `app/redis/redis.py`
- Queue implementation in `app/redis/queue.py`

### Worker runtime
- `app/worker/worker.py` registers workers, processes jobs from the queue, updates status, and runs heartbeats.
- `app/worker/executor.py` is the execution abstraction that current jobs call.

## Implemented features

- FastAPI API for creating and fetching jobs
- PostgreSQL persistence for jobs and workers
- Redis queue integration for job dispatch
- Worker registration and execution loop
- Status transitions for queued/running/success/failed jobs
- Job retries based on `max_retries`
- Worker heartbeat tracking using `last_heartbeat`
- Job ownership assignment to workers
- Basic retry/failure handling
- Docker Compose for PostgreSQL and Redis

## Confirmed gaps and risks

- Heartbeat thread was not correctly started previously; this was fixed.
- Worker registration must be idempotent and must not create duplicate rows for the same worker.
- The system is still not fully hardened for crash recovery, stale ownership, and retry lease semantics.
- Redis queue semantics are still best-effort delivery and do not yet include explicit ack/recovery guarantees.
- A handler registry and idempotency guard are now in place for example job types, but full production-grade external idempotency still requires downstream deduplication semantics.
- Worker shutdown behavior needs stronger operational safeguards before calling the system production-ready.

## Current milestone status

### Milestone 6: Job Handler Architecture
Status: implemented for the example registry pattern.

What is in place:
- `BaseJobHandler` interface for typed job execution
- `EmailJobHandler` and `ReportJobHandler` example implementations
- `JobExecutor` registry-based dispatch by `job.type`
- payload validation and structured result generation
- duplicate-delivery guard using an idempotency cache keyed by a stable payload key

### Milestone 5: Idempotency and Duplicate Execution Safety
Status: implemented at the executor level for at-least-once delivery scenarios.

What is in place:
- stable idempotency keys from job payload (`idempotency_key` when present)
- duplicate-delivery detection for repeated execution of the same logical job
- safe repeated execution result reuse for the in-process executor cache
- explicit distinction between duplicate database bookkeeping and duplicate external side effects

### Milestone 4: Multiple Workers and Concurrency
Status: implemented and validated for the core multi-worker claim path.

What is in place:
- 3-worker concurrency validation using a shared Redis queue
- atomic job claiming through PostgreSQL-backed ownership assignment
- successful execution of all queued jobs without duplicate ownership conflicts
- queue/database reconciliation checks for each job transition

### Milestone 1: Worker Lifecycle and Stability
Status: implemented and validated for the core lifecycle path.

What is in place:
- worker registration
- periodic heartbeat updates
- graceful shutdown support via `stop()`
- thread startup for heartbeat loop
- stable worker ID normalization
- idempotent worker registration in the repository

### Milestone 2: Reliable Job Delivery and Ownership
Status: implemented as an initial lease-based ownership step.

What is in place:
- `lease_expires_at` in the job model
- atomic job claiming through `JobRepository.claim_job()`
- lease reset during retry/requeue
- stale lease cleanup logic through `recover_expired_jobs()`
- worker assignment and lease reset on completion/failure

Key design choice:
- PostgreSQL is now the source of truth for job ownership and lease validity.
- Redis remains the delivery signal, but the system no longer assumes a Redis dequeue is sufficient proof that the job is safely owned and being processed.

## Next priority milestone

### Milestone 3: Lease Recovery and Crash Detection
The next step is a dedicated worker recovery process that scans for expired leases and reclaims jobs safely without conflicting with active workers.

Recommended direction:
- add a recovery service that periodically inspects `RUNNING` jobs with expired leases
- enforce fencing or ownership checks before releasing jobs back to the queue
- only allow recovery when the current job owner is stale and the lease has indeed expired
- keep retries and requeue logic consistent with the database as the single source of truth

## Validation

Relevant tests are run with:

```bash
cd /home/manohar/flowforge
. venv/bin/activate
python -m unittest tests.test_worker tests.test_worker_integration
```

Current status: passing.
