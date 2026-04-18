"""Global (non-scoped) page endpoints for the frontend.

Page UUIDs are globally unique, so the frontend can address a page directly
without knowing its collection_id. The scoped routes under /collections still
exist for REST completeness.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..dependencies import AuthContext, get_db
from ..models import OrgRole, Page, Revision
from ..rbac import require_page_role
from ..schemas import (
    PageReadWithContent,
    PageUpdate,
    RevisionRead,
    RevisionReadWithContent,
)

router = APIRouter(prefix="/api/pages", tags=["pages"])


def _get_page_or_404(page_id: UUID, db: Session) -> Page:
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


def _page_with_content(page: Page) -> PageReadWithContent:
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


@router.get("/{page_id}", response_model=PageReadWithContent)
def get_page(
    page_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_page_role(OrgRole.VIEWER)),
):
    return _page_with_content(_get_page_or_404(page_id, db))


@router.patch("/{page_id}", response_model=PageReadWithContent)
def update_page(
    page_id: UUID,
    body: PageUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_page_role(OrgRole.EDITOR)),
):
    """Append a new revision when content changes — never update in place."""
    page = _get_page_or_404(page_id, db)

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


@router.get("/{page_id}/revisions", response_model=list[RevisionRead])
def list_revisions(
    page_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_page_role(OrgRole.VIEWER)),
):
    _get_page_or_404(page_id, db)
    return db.query(Revision).filter_by(page_id=page_id).order_by(Revision.created_at.desc()).all()


@router.get("/{page_id}/revisions/{revision_id}", response_model=RevisionReadWithContent)
def get_revision(
    page_id: UUID,
    revision_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_page_role(OrgRole.VIEWER)),
):
    _get_page_or_404(page_id, db)
    rev = db.get(Revision, revision_id)
    if rev is None or rev.page_id != page_id:
        raise HTTPException(status_code=404, detail="Revision not found")
    return rev
