"""FastAPI dependency providers for database sessions, storage, and auth.

Kept separate from db.py so the CLI context-manager pattern is undisturbed.
The engine here is module-level (shared connection pool) — correct for a
long-running server process.
"""

import os
import uuid
from dataclasses import dataclass
from typing import Generator

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import create_engine, select, text as sa_text
from sqlalchemy.orm import Session

from .db import _database_url
from .search import PostgresSearchBackend, SearchBackend
from .storage import StorageAdapter, get_default_adapter

# Load .env so the module works when run directly (uvicorn main:app) without
# externally-set environment variables.
load_dotenv()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# pool_pre_ping tests the connection on checkout — handles DB restarts cleanly.
_engine = create_engine(_database_url(), pool_pre_ping=True)


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
# Search
# ---------------------------------------------------------------------------

_search_backend: SearchBackend = PostgresSearchBackend()


def get_search_backend() -> SearchBackend:
    return _search_backend


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@dataclass
class AuthContext:
    """Describes who made the current request and how they authenticated."""

    user_id: uuid.UUID | None  # None for API key or anonymous access
    email: str | None
    method: str  # "session", "api_key", or "anonymous"


def verify_auth(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> AuthContext:
    """Authenticate the request via session cookie, API key, or anonymous access.

    Priority:
    1. Valid ``marrow_session`` cookie → session auth
    2. Valid ``X-API-Key`` header → API key auth
    3. Neither, but OIDC and API_KEY both unconfigured → anonymous (dev mode)
    4. Otherwise → 401
    """
    from .auth import COOKIE_NAME, decode_session_jwt, get_oidc_config

    # 1. Session cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            claims = decode_session_jwt(token)
            return AuthContext(
                user_id=uuid.UUID(claims["sub"]),
                email=claims.get("email"),
                method="session",
            )
        except Exception:
            # Invalid/expired token — fall through to other methods
            pass

    # 2. API key
    api_key_required = os.getenv("API_KEY")
    if api_key_required:
        if x_api_key == api_key_required:
            return AuthContext(user_id=None, email=None, method="api_key")
    elif x_api_key and not api_key_required:
        # API key header sent but no API_KEY configured — ignore it
        pass

    # 3. Anonymous access (dev mode) — only when neither OIDC nor API_KEY is configured
    config = get_oidc_config()
    if not config.is_enabled and not api_key_required:
        return AuthContext(user_id=None, email=None, method="anonymous")

    raise HTTPException(status_code=401, detail="Authentication required")


def get_db_with_org(
    auth: AuthContext = Depends(verify_auth),
    db: Session = Depends(get_db),
) -> Generator[Session, None, None]:
    """Yield a session with ``app.current_org`` set for session-authenticated users.

    When the requesting user authenticated via OIDC session, this dependency
    looks up their first org membership and sets the ``app.current_org``
    PostgreSQL session variable so RLS policies restrict rows to that org.

    API key and anonymous auth leave ``app.current_org`` unset, which the RLS
    policies treat as unrestricted access (superuser / dev mode).
    """
    if auth.method == "session" and auth.user_id is not None:
        from .models import OrgMembership

        membership = db.execute(
            select(OrgMembership).where(OrgMembership.user_id == auth.user_id).limit(1)
        ).scalar_one_or_none()
        if membership is not None:
            db.execute(
                sa_text("SELECT set_config('app.current_org', :org_id, false)"),
                {"org_id": str(membership.org_id)},
            )
    yield db
