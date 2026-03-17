"""Space CRUD endpoints (nested under workspaces)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import Space, Workspace
from ..schemas import SpaceCreate, SpaceRead

router = APIRouter(prefix="/api/workspaces/{workspace_id}/spaces", tags=["spaces"])


def _get_workspace_or_404(workspace_id: UUID, db: Session) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("", response_model=list[SpaceRead])
def list_spaces(workspace_id: UUID, db: Session = Depends(get_db)):
    _get_workspace_or_404(workspace_id, db)
    return (
        db.query(Space)
        .filter_by(workspace_id=workspace_id)
        .order_by(Space.created_at)
        .all()
    )


@router.post("", response_model=SpaceRead, status_code=201)
def create_space(workspace_id: UUID, body: SpaceCreate, db: Session = Depends(get_db)):
    _get_workspace_or_404(workspace_id, db)
    space = Space(workspace_id=workspace_id, slug=body.slug, name=body.name)
    db.add(space)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Space slug '{body.slug}' already exists in this workspace"
        )
    db.refresh(space)
    return space


@router.get("/{space_id}", response_model=SpaceRead)
def get_space(workspace_id: UUID, space_id: UUID, db: Session = Depends(get_db)):
    _get_workspace_or_404(workspace_id, db)
    space = db.get(Space, space_id)
    if space is None or space.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


@router.delete("/{space_id}", status_code=204)
def delete_space(workspace_id: UUID, space_id: UUID, db: Session = Depends(get_db)):
    _get_workspace_or_404(workspace_id, db)
    space = db.get(Space, space_id)
    if space is None or space.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Space not found")
    db.delete(space)
    db.commit()
