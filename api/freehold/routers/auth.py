"""Authentication router — OIDC login flow and session management.

These endpoints are registered WITHOUT the global auth dependency so that
unauthenticated users can initiate the login flow.
"""

import re
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from ..auth import (
    COOKIE_NAME,
    create_session_jwt,
    decode_session_jwt,
    get_oauth_client,
    get_oidc_config,
    make_session_cookie_params,
)
from ..dependencies import get_db
from ..models import Organization, OrgMembership, OrgRole, User
from ..schemas import AuthStatus, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _unique_org_slug(db: Session, base: str) -> str:
    """Generate a unique org slug from a base string, appending a suffix on collision."""
    slug = re.sub(r"[^a-z0-9-]", "-", base.lower()).strip("-")[:50] or "org"
    candidate = slug
    attempt = 0
    while db.query(Organization).filter(Organization.slug == candidate).first() is not None:
        attempt += 1
        suffix = uuid.uuid4().hex[:4]
        candidate = f"{slug}-{suffix}"
    return candidate


@router.get("/login")
async def login(request: Request):
    """Redirect the browser to the OIDC provider's authorize endpoint."""
    config = get_oidc_config()
    if not config.is_enabled:
        raise HTTPException(status_code=404, detail="OIDC authentication is not configured")

    oauth = get_oauth_client()
    return await oauth.oidc.authorize_redirect(request, config.redirect_uri)


@router.get("/callback")
async def callback(request: Request):
    """Handle the OIDC callback: exchange code, upsert user, set session cookie."""
    config = get_oidc_config()
    if not config.is_enabled:
        raise HTTPException(status_code=404, detail="OIDC authentication is not configured")

    oauth = get_oauth_client()
    token = await oauth.oidc.authorize_access_token(request)

    # Extract user info from the ID token (falls back to userinfo endpoint)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.oidc.userinfo(token=token)

    sub = userinfo.get("sub")
    email = userinfo.get("email", "")
    name = userinfo.get("name") or userinfo.get("preferred_username") or email

    if not sub:
        raise HTTPException(status_code=400, detail="OIDC provider did not return a subject")

    # Upsert user record
    db = next(get_db())
    try:
        user = (
            db.query(User)
            .filter(User.oidc_issuer == config.issuer, User.oidc_subject == sub)
            .first()
        )
        if user:
            user.email = email
            user.name = name
            user.last_login_at = sa_func.now()
        else:
            user = User(
                oidc_issuer=config.issuer,
                oidc_subject=sub,
                email=email,
                name=name,
            )
            db.add(user)
        db.flush()
        db.refresh(user)

        # Claim any pending memberships that match this user's email
        pending = (
            db.query(OrgMembership)
            .filter(OrgMembership.email == user.email, OrgMembership.user_id.is_(None))
            .all()
        )
        for membership in pending:
            membership.user_id = user.id

        # Auto-create personal org if user has no memberships
        has_memberships = (
            db.query(OrgMembership).filter(OrgMembership.user_id == user.id).first()
        ) is not None

        if not has_memberships:
            slug_base = email.split("@")[0] if email else "user"
            slug = _unique_org_slug(db, slug_base)
            personal_org = Organization(
                name=f"{name}'s Space",
                slug=slug,
            )
            db.add(personal_org)
            db.flush()
            db.add(
                OrgMembership(
                    org_id=personal_org.id,
                    user_id=user.id,
                    email=user.email,
                    role=OrgRole.OWNER.value,
                )
            )

        db.commit()
        db.refresh(user)
        user_id = user.id
        user_email = user.email
        user_name = user.name
    finally:
        db.close()

    # Issue session JWT and set cookie
    session_jwt = create_session_jwt(user_id, user_email, user_name)
    cookie_params = make_session_cookie_params()

    response = RedirectResponse(url=config.frontend_url, status_code=302)
    response.set_cookie(value=session_jwt, **cookie_params)
    return response


@router.get("/me")
async def me(request: Request) -> AuthStatus:
    """Return the current authentication status.

    Checks the session cookie manually (this endpoint is not behind the
    global auth dependency).
    """
    config = get_oidc_config()
    token = request.cookies.get(COOKIE_NAME)

    if token:
        try:
            claims = decode_session_jwt(token)
            user = UserRead(
                id=uuid.UUID(claims["sub"]),
                email=claims["email"],
                name=claims["name"],
            )
            return AuthStatus(
                authenticated=True,
                user=user,
                method="session",
                oidc_enabled=config.is_enabled,
            )
        except Exception:
            pass

    return AuthStatus(
        authenticated=False,
        user=None,
        method="anonymous",
        oidc_enabled=config.is_enabled,
    )


@router.post("/logout")
async def logout():
    """Clear the session cookie."""
    from fastapi.responses import JSONResponse

    config = get_oidc_config()
    response = JSONResponse(content={"status": "ok"})
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        domain=config.cookie_domain,
    )
    return response
