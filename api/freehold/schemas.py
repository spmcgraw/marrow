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
    org_id: UUID | None = None  # if None, uses personal org


class WorkspaceRead(_ReadBase):
    id: UUID
    org_id: UUID
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
    content_format: str = "markdown"  # 'markdown' or 'json'


class PageUpdate(BaseModel):
    title: str | None = None
    content: str | None = None  # non-None → new revision appended
    content_format: str = "markdown"  # format of the new content


class PageRead(_ReadBase):
    id: UUID
    collection_id: UUID
    slug: str
    title: str
    current_revision_id: UUID | None
    created_at: datetime


class PageReadWithContent(PageRead):
    content: str | None = None  # current revision content; None if no revisions yet
    content_format: str = "markdown"  # format of current revision content


# ---------------------------------------------------------------------------
# Revision
# ---------------------------------------------------------------------------


class RevisionRead(_ReadBase):
    id: UUID
    page_id: UUID
    content_format: str
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
    org_id: UUID
    slug: str
    name: str
    spaces: list[SpaceTreeItem]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchResultItem(BaseModel):
    page_id: UUID
    title: str
    snippet: str
    collection_id: UUID
    space_id: UUID
    space_name: str
    collection_name: str
    rank: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


class OrganizationCreate(BaseModel):
    slug: str
    name: str


class OrganizationRead(_ReadBase):
    id: UUID
    slug: str
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Org Membership
# ---------------------------------------------------------------------------


class OrgMembershipCreate(BaseModel):
    email: str
    role: str  # "owner" | "editor" | "viewer"


class OrgMembershipRead(_ReadBase):
    id: UUID
    org_id: UUID
    user_id: UUID | None
    email: str
    role: str
    created_at: datetime


class OrgMembershipUpdate(BaseModel):
    role: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserRead(_ReadBase):
    id: UUID
    email: str
    name: str


class AuthStatus(BaseModel):
    authenticated: bool
    user: UserRead | None = None
    method: str  # "session", "api_key", or "anonymous"
    oidc_enabled: bool
