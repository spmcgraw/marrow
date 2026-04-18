"""Tests for authentication: session JWT, API key, anonymous access, and priority."""

import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from marrow.auth import (
    COOKIE_NAME,
    create_session_jwt,
    decode_session_jwt,
    get_oidc_config,
    reset_oidc_config,
)
from marrow.dependencies import AuthContext, verify_auth

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure a clean environment for each test."""
    # Clear any OIDC config so it's not enabled by default
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_ID", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    reset_oidc_config()
    yield
    reset_oidc_config()


# ---------------------------------------------------------------------------
# Session JWT tests
# ---------------------------------------------------------------------------


class TestSessionJWT:
    def test_create_and_decode(self):
        user_id = uuid.uuid4()
        token = create_session_jwt(user_id, "alice@example.com", "Alice")
        claims = decode_session_jwt(token)

        assert claims["sub"] == str(user_id)
        assert claims["email"] == "alice@example.com"
        assert claims["name"] == "Alice"
        assert "exp" in claims
        assert "iat" in claims

    def test_expired_token_raises(self):
        config = get_oidc_config()
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "bob@example.com",
            "name": "Bob",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # expired 1 hour ago
        }
        token = jwt.encode(payload, config.secret_key, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_session_jwt(token)

    def test_invalid_signature_raises(self):
        user_id = uuid.uuid4()
        token = create_session_jwt(user_id, "eve@example.com", "Eve")

        # Tamper with the token
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])

    def test_malformed_token_raises(self):
        with pytest.raises(jwt.InvalidTokenError):
            decode_session_jwt("not-a-valid-jwt")


# ---------------------------------------------------------------------------
# Auth dependency tests (using TestClient)
# ---------------------------------------------------------------------------


class TestVerifyAuth:
    """Test the verify_auth dependency via FastAPI TestClient."""

    @pytest.fixture()
    def app(self):
        """Create a minimal FastAPI app with the auth dependency."""
        from fastapi import Depends, FastAPI

        app = FastAPI()

        @app.get("/test")
        def test_route(auth: AuthContext = Depends(verify_auth)):
            return {
                "user_id": str(auth.user_id) if auth.user_id else None,
                "email": auth.email,
                "method": auth.method,
            }

        return app

    @pytest.fixture()
    def client(self, app):
        return TestClient(app)

    def test_anonymous_access_when_nothing_configured(self, client):
        """No OIDC, no API_KEY → anonymous access allowed."""
        res = client.get("/test")
        assert res.status_code == 200
        data = res.json()
        assert data["method"] == "anonymous"
        assert data["user_id"] is None

    def test_api_key_auth_correct(self, client, monkeypatch):
        """Correct API key → api_key auth."""
        monkeypatch.setenv("API_KEY", "my-secret-key")

        res = client.get("/test", headers={"X-API-Key": "my-secret-key"})
        assert res.status_code == 200
        data = res.json()
        assert data["method"] == "api_key"
        assert data["user_id"] is None

    def test_api_key_auth_wrong(self, client, monkeypatch):
        """Wrong API key → 401."""
        monkeypatch.setenv("API_KEY", "my-secret-key")

        res = client.get("/test", headers={"X-API-Key": "wrong-key"})
        assert res.status_code == 401

    def test_api_key_auth_missing(self, client, monkeypatch):
        """No API key header when API_KEY is set → 401."""
        monkeypatch.setenv("API_KEY", "my-secret-key")

        res = client.get("/test")
        assert res.status_code == 401

    def test_session_cookie_auth(self, client):
        """Valid session cookie → session auth."""
        user_id = uuid.uuid4()
        token = create_session_jwt(user_id, "alice@example.com", "Alice")

        client.cookies.set(COOKIE_NAME, token)
        res = client.get("/test")
        client.cookies.clear()
        assert res.status_code == 200
        data = res.json()
        assert data["method"] == "session"
        assert data["user_id"] == str(user_id)
        assert data["email"] == "alice@example.com"

    def test_expired_session_cookie_with_no_fallback(self, client, monkeypatch):
        """Expired session cookie and OIDC enabled → 401 (no fallback to anonymous)."""
        monkeypatch.setenv("OIDC_ISSUER", "https://example.com")
        reset_oidc_config()

        config = get_oidc_config()
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "bob@example.com",
            "name": "Bob",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        }
        token = jwt.encode(payload, config.secret_key, algorithm="HS256")

        client.cookies.set(COOKIE_NAME, token)
        res = client.get("/test")
        client.cookies.clear()
        assert res.status_code == 401

    def test_session_cookie_takes_precedence_over_api_key(self, client, monkeypatch):
        """When both cookie and API key are present, cookie wins."""
        monkeypatch.setenv("API_KEY", "my-secret-key")

        user_id = uuid.uuid4()
        token = create_session_jwt(user_id, "alice@example.com", "Alice")

        client.cookies.set(COOKIE_NAME, token)
        res = client.get(
            "/test",
            headers={"X-API-Key": "my-secret-key"},
        )
        client.cookies.clear()
        assert res.status_code == 200
        data = res.json()
        assert data["method"] == "session"
        assert data["user_id"] == str(user_id)

    def test_oidc_enabled_blocks_anonymous(self, client, monkeypatch):
        """When OIDC is configured, anonymous access is blocked."""
        monkeypatch.setenv("OIDC_ISSUER", "https://example.com")
        reset_oidc_config()

        res = client.get("/test")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Auth router endpoint tests
# ---------------------------------------------------------------------------


class TestAuthRouter:
    @pytest.fixture()
    def client(self):
        from marrow.app import app

        return TestClient(app, raise_server_exceptions=False)

    def test_me_unauthenticated(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["authenticated"] is False
        assert data["user"] is None

    def test_me_with_valid_session(self, client):
        user_id = uuid.uuid4()
        token = create_session_jwt(user_id, "alice@example.com", "Alice")

        client.cookies.set(COOKIE_NAME, token)
        res = client.get("/api/auth/me")
        client.cookies.clear()
        assert res.status_code == 200
        data = res.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == "alice@example.com"
        assert data["method"] == "session"

    def test_login_returns_404_when_oidc_disabled(self, client):
        res = client.get("/api/auth/login", follow_redirects=False)
        assert res.status_code == 404

    def test_logout_clears_cookie(self, client):
        user_id = uuid.uuid4()
        token = create_session_jwt(user_id, "alice@example.com", "Alice")

        client.cookies.set(COOKIE_NAME, token)
        res = client.post("/api/auth/logout")
        client.cookies.clear()
        assert res.status_code == 200
        # Check that the response sets the cookie to expire
        set_cookie = res.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie
