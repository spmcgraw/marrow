"""Node CRUD, revision, and attachment endpoints."""

import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import AuthContext, get_db, get_storage
from ..models import Attachment, Node, OrgRole, Revision, Space
from ..rbac import require_node_role, require_space_role
from ..schemas import (
    AttachmentRead,
    NodeCreate,
    NodeRead,
    NodeReadWithContent,
    NodeUpdate,
    RevisionRead,
)

router = APIRouter(tags=["nodes"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _node_or_404(node_id: UUID, db: Session) -> Node:
    node = db.get(Node, node_id)
    if node is None or node.deleted_at is not None:
        raise HTTPException(404, "Node not found")
    return node


def _with_content(node: Node) -> NodeReadWithContent:
    data = NodeReadWithContent.model_validate(node)
    if node.type == "page" and node.current_revision:
        data.content = node.current_revision.content
        data.content_format = node.current_revision.content_format  # type: ignore[assignment]
    return data


@router.post("/api/spaces/{space_id}/nodes", response_model=NodeRead, status_code=201)
def create_node(
    space_id: UUID,
    body: NodeCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_space_role(OrgRole.EDITOR)),
):
    slug = body.slug or _slugify(body.name)

    node = Node(
        space_id=space_id,
        parent_id=body.parent_id,
        type=body.type,
        name=body.name,
        slug=slug,
        position="a0",
        description=body.description if body.type == "folder" else None,
    )
    db.add(node)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Slug '{slug}' already exists in this location")

    if body.type == "page":
        content = body.content or ""
        rev = Revision(
            node_id=node.id,
            content=content,
            content_format=body.content_format,
        )
        db.add(rev)
        db.flush()
        node.current_revision_id = rev.id
        db.flush()

    db.commit()
    db.refresh(node)
    return node


@router.get("/api/spaces/{space_id}/nodes", response_model=list[NodeRead])
def list_space_root_nodes(
    space_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_space_role(OrgRole.VIEWER)),
):
    return (
        db.execute(
            select(Node)
            .where(Node.space_id == space_id, Node.parent_id.is_(None), Node.deleted_at.is_(None))
            .order_by(Node.position, Node.created_at)
        )
        .scalars()
        .all()
    )


@router.get("/api/nodes/{node_id}", response_model=NodeReadWithContent)
def get_node(
    node_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.VIEWER)),
):
    node = _node_or_404(node_id, db)
    return _with_content(node)


@router.patch("/api/nodes/{node_id}", response_model=NodeReadWithContent)
def update_node(
    node_id: UUID,
    body: NodeUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.EDITOR)),
):
    node = _node_or_404(node_id, db)

    if body.parent_id is not None and body.parent_id != node.parent_id:
        new_parent = db.get(Node, body.parent_id)
        if new_parent is None or new_parent.deleted_at is not None:
            raise HTTPException(404, "Parent node not found")
        current_space = db.get(Space, node.space_id)
        new_parent_space = db.get(Space, new_parent.space_id)
        if current_space.workspace_id != new_parent_space.workspace_id:
            raise HTTPException(400, "Cannot move node across workspaces")
        node.parent_id = body.parent_id

    if body.name is not None:
        node.name = body.name
    if body.slug is not None:
        node.slug = body.slug
    if body.position is not None:
        node.position = body.position
    if body.description is not None and node.type == "folder":
        node.description = body.description

    if body.content is not None and node.type == "page":
        rev = Revision(
            node_id=node.id,
            content=body.content,
            content_format=body.content_format or "markdown",
        )
        db.add(rev)
        db.flush()
        node.current_revision_id = rev.id

    node.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Slug already exists in this location")

    db.refresh(node)
    return _with_content(node)


@router.delete("/api/nodes/{node_id}", status_code=204)
def delete_node(
    node_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.OWNER)),
):
    node = _node_or_404(node_id, db)
    now = datetime.now(timezone.utc)

    def _soft_delete(n: Node) -> None:
        n.deleted_at = now
        for child in db.execute(
            select(Node).where(Node.parent_id == n.id, Node.deleted_at.is_(None))
        ).scalars():
            _soft_delete(child)

    _soft_delete(node)
    db.commit()


@router.get("/api/nodes/{node_id}/children", response_model=list[NodeRead])
def list_children(
    node_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.VIEWER)),
):
    _node_or_404(node_id, db)
    return (
        db.execute(
            select(Node)
            .where(Node.parent_id == node_id, Node.deleted_at.is_(None))
            .order_by(Node.position, Node.created_at)
        )
        .scalars()
        .all()
    )


@router.get("/api/nodes/{node_id}/revisions", response_model=list[RevisionRead])
def list_revisions(
    node_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.VIEWER)),
):
    node = _node_or_404(node_id, db)
    if node.type != "page":
        raise HTTPException(400, "Only page nodes have revisions")
    return (
        db.execute(
            select(Revision)
            .where(Revision.node_id == node_id)
            .order_by(Revision.created_at)
        )
        .scalars()
        .all()
    )


@router.get("/api/nodes/{node_id}/revisions/{revision_id}", response_model=RevisionRead)
def get_revision(
    node_id: UUID,
    revision_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.VIEWER)),
):
    node = _node_or_404(node_id, db)
    if node.type != "page":
        raise HTTPException(400, "Only page nodes have revisions")
    rev = db.get(Revision, revision_id)
    if rev is None or rev.node_id != node_id:
        raise HTTPException(404, "Revision not found")
    return rev


@router.post("/api/nodes/{node_id}/attachments", response_model=AttachmentRead, status_code=201)
def upload_attachment(
    node_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
    auth: AuthContext = Depends(require_node_role(OrgRole.EDITOR)),
):
    node = _node_or_404(node_id, db)
    data = file.file.read()
    file_hash = hashlib.sha256(data).hexdigest()

    attachment = Attachment(
        node_id=node.id,
        filename=file.filename or "upload",
        hash=file_hash,
        size_bytes=len(data),
    )
    db.add(attachment)
    db.flush()
    storage.write(str(attachment.id), attachment.filename, data)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/api/nodes/{node_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    node_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_node_role(OrgRole.VIEWER)),
):
    _node_or_404(node_id, db)
    return (
        db.execute(
            select(Attachment)
            .where(Attachment.node_id == node_id)
            .order_by(Attachment.created_at)
        )
        .scalars()
        .all()
    )


@router.get("/api/nodes/{node_id}/attachments/{attachment_id}/file")
def download_attachment(
    node_id: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
    auth: AuthContext = Depends(require_node_role(OrgRole.VIEWER)),
):
    _node_or_404(node_id, db)
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or attachment.node_id != node_id:
        raise HTTPException(404, "Attachment not found")
    data = storage.read(str(attachment.id), attachment.filename)
    return Response(content=data, media_type="application/octet-stream")
