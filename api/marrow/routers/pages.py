"""Page CRUD, revision history, and attachment endpoints."""

import hashlib
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import AuthContext, get_db, get_storage
from ..models import Attachment, Collection, OrgRole, Page, Revision
from ..rbac import require_collection_role
from ..schemas import (
    AttachmentRead,
    PageCreate,
    PageReadWithContent,
    PageUpdate,
    RevisionRead,
    RevisionReadWithContent,
)
from ..storage import StorageAdapter

router = APIRouter(prefix="/api/collections/{collection_id}/pages", tags=["pages"])


def _get_collection_or_404(collection_id: UUID, db: Session) -> Collection:
    col = db.get(Collection, collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return col


def _get_page_or_404(collection_id: UUID, page_id: UUID, db: Session) -> Page:
    page = db.get(Page, page_id)
    if page is None or page.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


def _page_with_content(page: Page) -> PageReadWithContent:
    """Build the response schema, pulling content from the current revision."""
    content = page.current_revision.content if page.current_revision else None
    content_format = page.current_revision.content_format if page.current_revision else "markdown"
    return PageReadWithContent(
        id=page.id,
        collection_id=page.collection_id,
        slug=page.slug,
        title=page.title,
        current_revision_id=page.current_revision_id,
        created_at=page.created_at,
        content=content,
        content_format=content_format,
    )


# ---------------------------------------------------------------------------
# Page CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=list[PageReadWithContent])
def list_pages(
    collection_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.VIEWER)),
):
    _get_collection_or_404(collection_id, db)
    pages = db.query(Page).filter_by(collection_id=collection_id).order_by(Page.created_at).all()
    return [_page_with_content(p) for p in pages]


@router.post("", response_model=PageReadWithContent, status_code=201)
def create_page(
    collection_id: UUID,
    body: PageCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.EDITOR)),
):
    """Create a page and its first revision in one transaction."""
    _get_collection_or_404(collection_id, db)

    page = Page(
        collection_id=collection_id,
        slug=body.slug,
        title=body.title,
        current_revision_id=None,
    )
    db.add(page)
    db.flush()

    rev = Revision(page_id=page.id, content=body.content, content_format=body.content_format)
    db.add(rev)
    db.flush()

    page.current_revision_id = rev.id

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Page slug '{body.slug}' already exists in this collection"
        )

    db.refresh(page)
    return _page_with_content(page)


@router.get("/{page_id}", response_model=PageReadWithContent)
def get_page(
    collection_id: UUID,
    page_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.VIEWER)),
):
    page = _get_page_or_404(collection_id, page_id, db)
    return _page_with_content(page)


@router.patch("/{page_id}", response_model=PageReadWithContent)
def update_page(
    collection_id: UUID,
    page_id: UUID,
    body: PageUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.EDITOR)),
):
    """Update a page's title and/or content.

    If content is provided, a new revision is appended — existing revisions
    are never modified (append-only guarantee).
    """
    page = _get_page_or_404(collection_id, page_id, db)

    if body.title is not None:
        page.title = body.title

    if body.content is not None:
        rev = Revision(page_id=page.id, content=body.content, content_format=body.content_format)
        db.add(rev)
        db.flush()
        page.current_revision_id = rev.id

    db.commit()
    db.refresh(page)
    return _page_with_content(page)


@router.delete("/{page_id}", status_code=204)
def delete_page(
    collection_id: UUID,
    page_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.OWNER)),
):
    page = _get_page_or_404(collection_id, page_id, db)
    db.delete(page)
    db.commit()


# ---------------------------------------------------------------------------
# Revisions (read-only — history is never deleted)
# ---------------------------------------------------------------------------


@router.get("/{page_id}/revisions", response_model=list[RevisionRead])
def list_revisions(
    collection_id: UUID,
    page_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.VIEWER)),
):
    _get_page_or_404(collection_id, page_id, db)
    return db.query(Revision).filter_by(page_id=page_id).order_by(Revision.created_at.desc()).all()


@router.get("/{page_id}/revisions/{revision_id}", response_model=RevisionReadWithContent)
def get_revision(
    collection_id: UUID,
    page_id: UUID,
    revision_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.VIEWER)),
):
    _get_page_or_404(collection_id, page_id, db)
    rev = db.get(Revision, revision_id)
    if rev is None or rev.page_id != page_id:
        raise HTTPException(status_code=404, detail="Revision not found")
    return rev


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


@router.get("/{page_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    collection_id: UUID,
    page_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_collection_role(OrgRole.VIEWER)),
):
    _get_page_or_404(collection_id, page_id, db)
    return db.query(Attachment).filter_by(page_id=page_id).order_by(Attachment.created_at).all()


@router.post("/{page_id}/attachments", response_model=AttachmentRead, status_code=201)
async def upload_attachment(
    collection_id: UUID,
    page_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    storage: StorageAdapter = Depends(get_storage),
    auth: AuthContext = Depends(require_collection_role(OrgRole.EDITOR)),
):
    """Upload a file attachment."""
    _get_page_or_404(collection_id, page_id, db)

    data = await file.read()
    sha256 = hashlib.sha256(data).hexdigest()
    filename = file.filename or "upload"

    att_id = uuid.uuid4()
    storage.write(str(att_id), filename, data)

    att = Attachment(
        id=att_id,
        page_id=page_id,
        filename=filename,
        hash=sha256,
        size_bytes=len(data),
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@router.get("/{page_id}/attachments/{attachment_id}/file")
def download_attachment(
    collection_id: UUID,
    page_id: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
    storage: StorageAdapter = Depends(get_storage),
    auth: AuthContext = Depends(require_collection_role(OrgRole.VIEWER)),
):
    _get_page_or_404(collection_id, page_id, db)
    att = db.get(Attachment, attachment_id)
    if att is None or att.page_id != page_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    data = storage.read(str(attachment_id), att.filename)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{att.filename}"'},
    )
