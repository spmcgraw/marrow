"""OIDC authentication and session JWT management.

Handles:
- OIDC provider discovery and OAuth client setup via authlib
- Session JWT creation and validation (HS256, signed with SECRET_KEY)
- Cookie configuration for session tokens
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from authlib.integrations.starlette_client import OAuth


@dataclass(frozen=True)
class OIDCConfig:
    """OIDC configuration loaded from environment variables."""

    issuer: str | None
    client_id: str
    client_secret: str
    redirect_uri: str
    frontend_url: str
    cookie_domain: str | None
    secret_key: str
    session_max_age: int = 86400  # 24 hours

    @property
    def is_enabled(self) -> bool:
        return self.issuer is not None and self.issuer != ""


_oidc_config: OIDCConfig | None = None


def get_oidc_config() -> OIDCConfig:
    """Return the singleton OIDC config, loading from env on first call."""
    global _oidc_config
    if _oidc_config is None:
        _oidc_config = OIDCConfig(
            issuer=os.getenv("OIDC_ISSUER") or None,
            client_id=os.getenv("OIDC_CLIENT_ID", ""),
            client_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/auth/callback"),
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3000"),
            cookie_domain=os.getenv("COOKIE_DOMAIN") or None,
            secret_key=os.getenv("SECRET_KEY", "changeme"),
        )
    return _oidc_config


_oauth: OAuth | None = None


def get_oauth_client() -> OAuth:
    """Return the singleton authlib OAuth client.

    Lazily registers the OIDC provider on first call.  Only call this when
    OIDC is enabled (config.is_enabled is True).
    """
    global _oauth
    if _oauth is None:
        config = get_oidc_config()
        _oauth = OAuth()
        _oauth.register(
            name="oidc",
            client_id=config.client_id,
            client_secret=config.client_secret,
            server_metadata_url=f"{config.issuer}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    return _oauth


# ---------------------------------------------------------------------------
# Session JWT helpers
# ---------------------------------------------------------------------------

_JWT_ALGORITHM = "HS256"


def create_session_jwt(
    user_id: uuid.UUID,
    email: str,
    name: str,
) -> str:
    """Create a session JWT for the given user."""
    config = get_oidc_config()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + config.session_max_age,
    }
    return jwt.encode(payload, config.secret_key, algorithm=_JWT_ALGORITHM)


def decode_session_jwt(token: str) -> dict:
    """Decode and validate a session JWT.

    Raises jwt.InvalidTokenError (or subclass) on any failure.
    """
    config = get_oidc_config()
    return jwt.decode(token, config.secret_key, algorithms=[_JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

COOKIE_NAME = "freehold_session"


def make_session_cookie_params() -> dict:
    """Return kwargs suitable for ``response.set_cookie()``."""
    config = get_oidc_config()
    secure = config.redirect_uri.startswith("https://")
    params: dict = {
        "key": COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure": secure,
        "path": "/",
        "max_age": config.session_max_age,
    }
    if config.cookie_domain:
        params["domain"] = config.cookie_domain
    return params


def reset_oidc_config() -> None:
    """Reset cached singletons.  Intended for tests only."""
    global _oidc_config, _oauth
    _oidc_config = None
    _oauth = None
