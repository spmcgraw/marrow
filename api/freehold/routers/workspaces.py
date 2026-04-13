"""Workspace CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import AuthContext, get_db, get_search_backend, verify_auth
from ..models import OrgMembership, OrgRole, Workspace
from ..rbac import require_workspace_role
from ..schemas import (
    SearchResponse,
    SearchResultItem,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceTree,
)
from ..search import SearchBackend

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_auth),
):
    """List workspaces. Session users see only workspaces in their orgs."""
    if auth.method in ("api_key", "anonymous"):
        return db.query(Workspace).order_by(Workspace.created_at).all()

    return (
        db.execute(
            select(Workspace)
            .join(OrgMembership, OrgMembership.org_id == Workspace.org_id)
            .where(OrgMembership.user_id == auth.user_id)
            .order_by(Workspace.created_at)
        )
        .scalars()
        .all()
    )


@router.post("", response_model=WorkspaceRead, status_code=201)
def create_workspace(
    body: WorkspaceCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_auth),
):
    org_id = body.org_id

    # For session users without explicit org_id, use their first org
    if org_id is None and auth.user_id is not None:
        membership = db.execute(
            select(OrgMembership)
            .where(OrgMembership.user_id == auth.user_id)
            .order_by(OrgMembership.created_at)
        ).scalar_one_or_none()
        if membership is None:
            raise HTTPException(403, "You must belong to an organization to create a workspace")
        org_id = membership.org_id

    # For API key/anonymous, org_id is required
    if org_id is None:
        raise HTTPException(422, "org_id is required for API key or anonymous access")

    ws = Workspace(org_id=org_id, slug=body.slug, name=body.name)
    db.add(ws)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Workspace slug '{body.slug}' already exists")
    db.refresh(ws)
    return ws


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_workspace_role(OrgRole.VIEWER)),
):
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("/{workspace_id}/tree", response_model=WorkspaceTree)
def get_workspace_tree(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_workspace_role(OrgRole.VIEWER)),
):
    """Return the full workspace hierarchy for sidebar rendering."""
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("/{workspace_id}/search", response_model=SearchResponse)
def search_workspace(
    workspace_id: UUID,
    q: str = "",
    db: Session = Depends(get_db),
    search: SearchBackend = Depends(get_search_backend),
    auth: AuthContext = Depends(require_workspace_role(OrgRole.VIEWER)),
):
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    results = search.search(workspace_id, q, db)
    return SearchResponse(
        query=q,
        results=[SearchResultItem(**vars(r)) for r in results],
    )


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_workspace_role(OrgRole.OWNER)),
):
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()
