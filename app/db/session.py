from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from collections.abc import Generator

from app.core.config import setting

engine = create_engine(setting.DATABASE_URL)

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    bind=engine
)

def get_db() -> Generator[Session,None,None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()