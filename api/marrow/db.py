"""Database session factory."""

import os
from contextlib import contextmanager
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _database_url(override: str | None = None) -> str:
    if override:
        return override
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Build from discrete POSTGRES_* vars so passwords with special chars
    # (@, :, /, #, etc.) are safely URL-encoded.
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    if user and password and host:
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", user)
        return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{db}"
    raise RuntimeError("DATABASE_URL is not set (or POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_HOST)")


@contextmanager
def get_session(database_url: str | None = None):
    engine = create_engine(_database_url(database_url))
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()
