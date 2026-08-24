"""Database engine and session setup.

The default database is a local SQLite file so the service runs offline with no
extra infrastructure. Set DATABASE_URL to override it, for example a PostgreSQL
connection string of the form postgresql+psycopg://user:pass@host/dbname.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_DATABASE_URL = "sqlite:///griffin.db"


def get_database_url() -> str:
    """Return the configured database URL, defaulting to local SQLite."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _make_engine(url: str):
    """Create the SQLAlchemy engine, with SQLite friendly connect args."""
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        # Allow the connection to be shared across the request loop and the
        # background pipeline thread.
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, future=True)


DATABASE_URL = get_database_url()
engine = _make_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session and closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
