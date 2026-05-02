"""Role-based access control dependencies for Marrow.

Provides dependency factories that enforce org membership and role requirements
on API routes. API key and anonymous auth bypass all role checks for backward
compatibility.
"""

import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .dependencies import AuthContext, get_db, verify_auth
from .models import (
    OrgMembership,
    OrgRole,
    Space,
    Workspace,
)

# require_collection_role / require_page_role removed in #123 — collection and
# page routers no longer exist. A node-based replacement (require_node_role)
# lands in #124 (2.0b).

ROLE_HIERARCHY: dict[OrgRole, int] = {
    OrgRole.VIEWER: 0,
    OrgRole.EDITOR: 1,
    OrgRole.OWNER: 2,
}


def _check_membership(db: Session, org_id: uuid.UUID, auth: AuthContext, min_role: OrgRole) -> None:
    """Raise 403 if the session user lacks the required role on the org."""
    if auth.method in ("api_key", "anonymous"):
        return

    membership = db.execute(
        select(OrgMembership.role).where(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == auth.user_id,
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(403, "Not a member of this organization")

    if ROLE_HIERARCHY[OrgRole(membership)] < ROLE_HIERARCHY[min_role]:
        raise HTTPException(403, f"Requires {min_role.value} role or higher")


def require_org_role(min_role: OrgRole):
    """Dependency factory: enforce role on org_id path param."""

    def _dep(
        org_id: uuid.UUID,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(verify_auth),
    ) -> AuthContext:
        _check_membership(db, org_id, auth, min_role)
        return auth

    return _dep


def require_workspace_role(min_role: OrgRole):
    """Dependency factory: resolve workspace_id → org, then enforce role."""

    def _dep(
        workspace_id: uuid.UUID,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(verify_auth),
    ) -> AuthContext:
        org_id = db.execute(
            select(Workspace.org_id).where(Workspace.id == workspace_id)
        ).scalar_one_or_none()
        if org_id is None:
            raise HTTPException(404, "Workspace not found")
        _check_membership(db, org_id, auth, min_role)
        return auth

    return _dep


def require_space_role(min_role: OrgRole):
    """Dependency factory: resolve space_id → workspace → org, then enforce role."""

    def _dep(
        space_id: uuid.UUID,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(verify_auth),
    ) -> AuthContext:
        org_id = db.execute(
            select(Workspace.org_id)
            .join(Space, Space.workspace_id == Workspace.id)
            .where(Space.id == space_id)
        ).scalar_one_or_none()
        if org_id is None:
            raise HTTPException(404, "Space not found")
        _check_membership(db, org_id, auth, min_role)
        return auth

    return _dep
