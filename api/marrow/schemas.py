"""Pydantic request/response schemas for the Marrow REST API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class _ReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


class WorkspaceCreate(BaseModel):
    slug: str
    name: str
    org_id: UUID | None = None


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
# Node
# ---------------------------------------------------------------------------


class NodeCreate(BaseModel):
    type: Literal["folder", "page"]
    name: str
    slug: str | None = None
    parent_id: UUID | None = None
    description: str | None = None
    content: str | None = None
    content_format: Literal["markdown", "json"] = "markdown"


class NodeRead(_ReadBase):
    id: UUID
    space_id: UUID
    parent_id: UUID | None
    type: Literal["folder", "page"]
    name: str
    slug: str
    position: str
    description: str | None
    current_revision_id: UUID | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NodeReadWithContent(NodeRead):
    content: str | None = None
    content_format: Literal["markdown", "json"] | None = None


class NodeUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    content: str | None = None
    content_format: Literal["markdown", "json"] | None = None
    position: str | None = None
    parent_id: UUID | None = None


class NodeTreeItem(_ReadBase):
    id: UUID
    parent_id: UUID | None
    type: Literal["folder", "page"]
    name: str
    slug: str
    position: str
    description: str | None
    children: list["NodeTreeItem"] = []


NodeTreeItem.model_rebuild()


class SpaceTreeItem(_ReadBase):
    id: UUID
    slug: str
    name: str
    nodes: list[NodeTreeItem] = []


class WorkspaceTree(_ReadBase):
    id: UUID
    slug: str
    name: str
    spaces: list[SpaceTreeItem] = []


# ---------------------------------------------------------------------------
# Revision
# ---------------------------------------------------------------------------


class RevisionRead(_ReadBase):
    id: UUID
    node_id: UUID
    content: str
    content_format: Literal["markdown", "json"]
    created_at: datetime


# ---------------------------------------------------------------------------
# Attachment
# ---------------------------------------------------------------------------


class AttachmentRead(_ReadBase):
    id: UUID
    node_id: UUID
    filename: str
    hash: str
    size_bytes: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchResultItem(BaseModel):
    node_id: UUID
    name: str
    snippet: str
    space_id: UUID
    space_name: str
    node_path: list[str]
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
    role: str


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
    method: str
    oidc_enabled: bool
