"""Database helpers for ParlayLab NBA."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from parlaylab.config import get_settings
from parlaylab.db.models import Base

settings = get_settings()
engine = create_engine(settings.database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)


def init_db() -> None:
    """Create all database tables if they do not already exist."""

    import parlaylab.db.models  # noqa: F401 - ensure model registration

    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    print("DB init, tables:", inspector.get_table_names())


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
