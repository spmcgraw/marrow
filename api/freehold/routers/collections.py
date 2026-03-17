"""Collection CRUD endpoints (nested under spaces)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import Collection, Space
from ..schemas import CollectionCreate, CollectionRead

router = APIRouter(prefix="/api/spaces/{space_id}/collections", tags=["collections"])


def _get_space_or_404(space_id: UUID, db: Session) -> Space:
    space = db.get(Space, space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


@router.get("", response_model=list[CollectionRead])
def list_collections(space_id: UUID, db: Session = Depends(get_db)):
    _get_space_or_404(space_id, db)
    return (
        db.query(Collection)
        .filter_by(space_id=space_id)
        .order_by(Collection.created_at)
        .all()
    )


@router.post("", response_model=CollectionRead, status_code=201)
def create_collection(space_id: UUID, body: CollectionCreate, db: Session = Depends(get_db)):
    _get_space_or_404(space_id, db)
    col = Collection(space_id=space_id, slug=body.slug, name=body.name)
    db.add(col)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Collection slug '{body.slug}' already exists in this space",
        )
    db.refresh(col)
    return col


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection(space_id: UUID, collection_id: UUID, db: Session = Depends(get_db)):
    _get_space_or_404(space_id, db)
    col = db.get(Collection, collection_id)
    if col is None or col.space_id != space_id:
        raise HTTPException(status_code=404, detail="Collection not found")
    return col


@router.delete("/{collection_id}", status_code=204)
def delete_collection(space_id: UUID, collection_id: UUID, db: Session = Depends(get_db)):
    _get_space_or_404(space_id, db)
    col = db.get(Collection, collection_id)
    if col is None or col.space_id != space_id:
        raise HTTPException(status_code=404, detail="Collection not found")
    db.delete(col)
    db.commit()
