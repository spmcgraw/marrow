"""Pydantic request/response schemas for the Freehold REST API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared config — all read schemas allow ORM model instances as input
# ---------------------------------------------------------------------------

class _ReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

class WorkspaceCreate(BaseModel):
    slug: str
    name: str


class WorkspaceRead(_ReadBase):
    id: UUID
    slug: str
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Space
# ---------------------------------------------------------------------------

class SpaceCreate(BaseModel):
    slug: str
    name: str


class SpaceRead(_ReadBase):
    id: UUID
    workspace_id: UUID
    slug: str
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

class CollectionCreate(BaseModel):
    slug: str
    name: str


class CollectionRead(_ReadBase):
    id: UUID
    space_id: UUID
    slug: str
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class PageCreate(BaseModel):
    slug: str
    title: str
    content: str = ""  # seeds the first revision


class PageUpdate(BaseModel):
    title: str | None = None
    content: str | None = None  # non-None → new revision appended


class PageRead(_ReadBase):
    id: UUID
    collection_id: UUID
    slug: str
    title: str
    current_revision_id: UUID | None
    created_at: datetime


class PageReadWithContent(PageRead):
    content: str | None = None  # current revision content; None if no revisions yet


# ---------------------------------------------------------------------------
# Revision
# ---------------------------------------------------------------------------

class RevisionRead(_ReadBase):
    id: UUID
    page_id: UUID
    created_at: datetime


class RevisionReadWithContent(RevisionRead):
    content: str


# ---------------------------------------------------------------------------
# Attachment
# ---------------------------------------------------------------------------

class AttachmentRead(_ReadBase):
    id: UUID
    page_id: UUID
    filename: str
    hash: str
    size_bytes: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Workspace tree (nested, for sidebar)
# ---------------------------------------------------------------------------

class PageTreeItem(_ReadBase):
    id: UUID
    collection_id: UUID
    slug: str
    title: str
    current_revision_id: UUID | None


class CollectionTreeItem(_ReadBase):
    id: UUID
    slug: str
    name: str
    pages: list[PageTreeItem]


class SpaceTreeItem(_ReadBase):
    id: UUID
    slug: str
    name: str
    collections: list[CollectionTreeItem]


class WorkspaceTree(_ReadBase):
    id: UUID
    slug: str
    name: str
    spaces: list[SpaceTreeItem]
