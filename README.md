# FlowForge

FlowForge is a Python background job processing system for scheduling, dispatching, and executing asynchronous work across multiple workers. It combines FastAPI, PostgreSQL, Redis, and SQLAlchemy to provide a reliable foundation for queued workloads with retry logic, worker ownership tracking, and scheduled job execution.

## Why FlowForge

FlowForge is designed for systems that need dependable background processing without depending on a single worker process. The architecture separates durable job state from transient queue delivery, which makes it easier to reason about retries, lease-based ownership, and recovery from failed or stalled workers.

## Key features

- API-driven job submission and retrieval
- Persistent job records in PostgreSQL
- Redis-backed queue dispatch
- Multi-worker execution with ownership tracking
- Lease-based processing to prevent duplicate work
- Retry and failure handling based on configured limits
- Scheduled and priority-aware job selection
- Typed job handlers for extensible execution behavior
- Worker heartbeat tracking and lifecycle management

## System design

### API layer
- `app/main.py` initializes the application
- `app/api/routes/job.py` exposes job endpoints
- `app/schemas/job.py` defines request and response models

### Application services
- `app/service/job_service.py` manages job lifecycle operations
- `app/service/recovery_service.py` handles expired lease recovery
- `app/service/scheduler_service.py` dispatches due jobs

### Persistence and data model
- `app/models/job.py` defines the job entity and execution metadata
- `app/models/worker.py` tracks worker registration and heartbeat behavior
- `app/models/enum.py` defines the job status state machine
- `app/repositroy/job_repository.py` implements repository-level job and worker operations

### Queue and execution runtime
- `app/redis/queue.py` defines the Redis queue wrapper
- `app/redis/redis.py` provides the Redis connection configuration
- `app/worker/worker.py` runs worker loops and manages processing lifecycle
- `app/worker/executor.py` dispatches jobs to registered handlers
- `app/worker/handlers.py` contains example typed job handlers

## Job lifecycle

Jobs move through a state model designed to support retries and worker recovery:

- queued
- pending
- running
- succeeded
- failed
- cancelled

A job can be scheduled for future execution, prioritized when ready, claimed by a worker, and retried after failure or lease expiration. The repository layer coordinates these transitions with PostgreSQL as the source of truth while Redis handles dispatch signals.

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis
- Docker Compose (optional, for local infrastructure)

### Local setup

```bash
cd /home/manohar/flowforge
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

Start the supporting services:

```bash
docker-compose up -d
```

Then run the application or validation suite as needed.

## Validation

The project includes focused regression tests covering worker execution, retry behavior, scheduled priorities, concurrency, and lease recovery.

```bash
cd /home/manohar/flowforge
. venv/bin/activate
python -m unittest \
  tests.test_worker \
  tests.test_worker_integration \
  tests.test_recovery_service \
  tests.test_multi_worker_concurrency \
  tests.test_scheduled_priority_jobs
```

These checks are currently passing.

## Current status

FlowForge is in active development as a background job processing foundation. The current implementation covers the core responsibilities of job registration, worker ownership, retries, priority scheduling, and distributed execution. The next areas of focus are operational hardening, more advanced retry policy controls, and stronger recovery semantics for expired leases.

## License

This project is provided as-is for development and extension.
