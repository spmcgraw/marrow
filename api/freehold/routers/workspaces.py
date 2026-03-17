"""Workspace CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import Workspace
from ..schemas import WorkspaceCreate, WorkspaceRead, WorkspaceTree

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(db: Session = Depends(get_db)):
    return db.query(Workspace).order_by(Workspace.created_at).all()


@router.post("", response_model=WorkspaceRead, status_code=201)
def create_workspace(body: WorkspaceCreate, db: Session = Depends(get_db)):
    ws = Workspace(slug=body.slug, name=body.name)
    db.add(ws)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Workspace slug '{body.slug}' already exists")
    db.refresh(ws)
    return ws


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: UUID, db: Session = Depends(get_db)):
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("/{workspace_id}/tree", response_model=WorkspaceTree)
def get_workspace_tree(workspace_id: UUID, db: Session = Depends(get_db)):
    """Return the full workspace hierarchy for sidebar rendering.

    Pydantic serializes the ORM relationships (lazy-loaded within the active
    session) into the nested tree structure.
    """
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: UUID, db: Session = Depends(get_db)):
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()
