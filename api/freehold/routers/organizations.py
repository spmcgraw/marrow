"""Organization CRUD and member management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import AuthContext, get_db, verify_auth
from ..models import Organization, OrgMembership, OrgRole, User
from ..rbac import require_org_role
from ..schemas import (
    OrganizationCreate,
    OrganizationRead,
    OrgMembershipCreate,
    OrgMembershipRead,
    OrgMembershipUpdate,
)

router = APIRouter(prefix="/api/orgs", tags=["organizations"])


@router.get("", response_model=list[OrganizationRead])
def list_orgs(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_auth),
):
    """List orgs the current user belongs to (all orgs for API key/anonymous)."""
    if auth.method in ("api_key", "anonymous"):
        return db.execute(select(Organization).order_by(Organization.created_at)).scalars().all()

    return (
        db.execute(
            select(Organization)
            .join(OrgMembership, OrgMembership.org_id == Organization.id)
            .where(OrgMembership.user_id == auth.user_id)
            .order_by(Organization.created_at)
        )
        .scalars()
        .all()
    )


@router.post("", response_model=OrganizationRead, status_code=201)
def create_org(
    body: OrganizationCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_auth),
):
    """Create an org. The creating user becomes the owner."""
    org = Organization(slug=body.slug, name=body.name)
    db.add(org)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Organization slug '{body.slug}' already exists")

    if auth.user_id is not None:
        db.add(
            OrgMembership(
                org_id=org.id,
                user_id=auth.user_id,
                email=auth.email or "",
                role=OrgRole.OWNER.value,
            )
        )

    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationRead)
def get_org(
    org_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_org_role(OrgRole.VIEWER)),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(404, "Organization not found")
    return org


@router.get("/{org_id}/members", response_model=list[OrgMembershipRead])
def list_members(
    org_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_org_role(OrgRole.VIEWER)),
):
    return (
        db.execute(
            select(OrgMembership)
            .where(OrgMembership.org_id == org_id)
            .order_by(OrgMembership.created_at)
        )
        .scalars()
        .all()
    )


@router.post("/{org_id}/members", response_model=OrgMembershipRead, status_code=201)
def invite_member(
    org_id: UUID,
    body: OrgMembershipCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_org_role(OrgRole.OWNER)),
):
    """Invite a user by email. Creates a pending membership if the user has no account yet."""
    if body.role not in (r.value for r in OrgRole):
        raise HTTPException(422, f"Invalid role: {body.role}")

    # Check if user exists
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()

    membership = OrgMembership(
        org_id=org_id,
        user_id=user.id if user else None,
        email=body.email,
        role=body.role,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"User '{body.email}' is already a member of this organization")
    db.refresh(membership)
    return membership


@router.patch("/{org_id}/members/{membership_id}", response_model=OrgMembershipRead)
def update_member_role(
    org_id: UUID,
    membership_id: UUID,
    body: OrgMembershipUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_org_role(OrgRole.OWNER)),
):
    if body.role not in (r.value for r in OrgRole):
        raise HTTPException(422, f"Invalid role: {body.role}")

    membership = db.get(OrgMembership, membership_id)
    if membership is None or membership.org_id != org_id:
        raise HTTPException(404, "Membership not found")

    membership.role = body.role
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{org_id}/members/{membership_id}", status_code=204)
def remove_member(
    org_id: UUID,
    membership_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_org_role(OrgRole.OWNER)),
):
    membership = db.get(OrgMembership, membership_id)
    if membership is None or membership.org_id != org_id:
        raise HTTPException(404, "Membership not found")
    db.delete(membership)
    db.commit()
