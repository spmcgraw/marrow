"""FastAPI dependency providers for database sessions, storage, and auth.

Kept separate from db.py so the CLI context-manager pattern is undisturbed.
The engine here is module-level (shared connection pool) — correct for a
long-running server process.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from fastapi import Header, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .storage import StorageAdapter, get_default_adapter

# Load .env so the module works when run directly (uvicorn main:app) without
# an externally-set DATABASE_URL environment variable.
load_dotenv()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _require_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set — copy api/.env.example to api/.env")
    return url


# pool_pre_ping tests the connection on checkout — handles DB restarts cleanly.
_engine = create_engine(_require_database_url(), pool_pre_ping=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session; rollback on unhandled exception."""
    with Session(_engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

# One adapter instance for the lifetime of the process.
_storage: StorageAdapter = get_default_adapter()


def get_storage() -> StorageAdapter:
    return _storage


# ---------------------------------------------------------------------------
# API key auth
# ---------------------------------------------------------------------------

def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key header when API_KEY env var is set.

    If API_KEY is not configured, all requests are allowed (dev mode).
    """
    required = os.getenv("API_KEY")
    if required and x_api_key != required:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
