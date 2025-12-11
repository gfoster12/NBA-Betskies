"""Database helpers for ParlayLab NBA."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from parlaylab.db.models import Base

from parlaylab.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)


@contextmanager
def get_session() -> Session:
    """Provide a transactional scope around a series of operations."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - defensive rollback
        session.rollback()
        raise
    finally:
        session.close()

def init_db() -> None:
    """
    Create all database tables if they do not already exist.

    This imports parlaylab.db.models to ensure all ORM models
    are registered on Base.metadata before create_all() is called.
    """
    import parlaylab.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
