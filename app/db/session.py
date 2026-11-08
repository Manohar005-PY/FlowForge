from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from collections.abc import Generator

from app.core.config import setting

engine = create_engine(setting.DATABASE_URL)


def ensure_job_schema() -> None:
    inspector = inspect(engine)
    if 'jobs' not in inspector.get_table_names():
        return
    columns = {column['name'] for column in inspector.get_columns('jobs')}
    with engine.begin() as connection:
        if connection.dialect.name == 'postgresql':
            if 'idempotency_key' not in columns:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN idempotency_key VARCHAR"))
                columns.add('idempotency_key')
            if 'result' not in columns:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN result JSONB"))
                columns.add('result')
            if 'error_message' not in columns:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN error_message TEXT"))
                columns.add('error_message')
            if 'cancellation_reason' not in columns:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN cancellation_reason TEXT"))
                columns.add('cancellation_reason')
            if 'cancelled_at' not in columns:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN cancelled_at TIMESTAMPTZ"))
                columns.add('cancelled_at')

            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_type t
                        JOIN pg_enum e ON e.enumtypid = t.oid
                        WHERE t.typname = 'job_status' AND e.enumlabel = 'CANCELLED'
                    ) THEN
                        ALTER TYPE job_status ADD VALUE 'CANCELLED';
                    END IF;
                END $$;
            """))

        indexes = inspector.get_indexes('jobs')
        index_names = {index['name'] for index in indexes}
        if 'ix_jobs_idempotency_key' not in index_names:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_idempotency_key ON jobs (idempotency_key)"))


ensure_job_schema()

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()