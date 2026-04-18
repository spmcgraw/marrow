"""Database session factory."""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _database_url(override: str | None = None) -> str:
    url = override or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


@contextmanager
def get_session(database_url: str | None = None):
    engine = create_engine(_database_url(database_url))
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()
