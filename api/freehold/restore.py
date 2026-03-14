"""Restore a workspace from an export bundle.

Usage:
    freehold restore <bundle.zip>
"""

import hashlib
import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .export import SCHEMA_VERSION
from .models import Attachment, Collection, Page, Revision, Space, Workspace
from .storage import StorageAdapter


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def restore_workspace(
    bundle_path: Path,
    session: Session,
    storage: StorageAdapter,
) -> str:
    """Restore a workspace from *bundle_path* into *session*.

    Returns the workspace slug on success. Raises on any validation failure.
    The caller is responsible for committing the session.
    """
    if not zipfile.is_zipfile(bundle_path):
        raise ValueError(f"Not a valid zip file: {bundle_path}")

    with zipfile.ZipFile(bundle_path) as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            raise ValueError(f"Not a valid Freehold bundle: manifest.json missing in {bundle_path}")

        manifest = json.loads(zf.read("manifest.json"))

        schema_version = manifest.get("schema_version")
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported bundle schema version '{schema_version}' "
                f"(expected '{SCHEMA_VERSION}')"
            )

        ws_meta = manifest["workspace"]
        ws_id = uuid.UUID(ws_meta["id"])

        # Duplicate checks — fail loudly rather than silently overwriting.
        if session.get(Workspace, ws_id) is not None:
            raise ValueError(
                f"Workspace with id={ws_meta['id']} already exists. Delete it before restoring."
            )
        if session.query(Workspace).filter_by(slug=ws_meta["slug"]).first() is not None:
            raise ValueError(
                f"A workspace with slug '{ws_meta['slug']}' already exists. "
                "Delete it before restoring."
            )

        # --- Workspace ---
        session.add(
            Workspace(
                id=ws_id,
                slug=ws_meta["slug"],
                name=ws_meta["name"],
                created_at=_dt(ws_meta["created_at"]),
            )
        )
        session.flush()

        # --- Spaces ---
        for s in manifest["spaces"]:
            session.add(
                Space(
                    id=uuid.UUID(s["id"]),
                    workspace_id=uuid.UUID(s["workspace_id"]),
                    slug=s["slug"],
                    name=s["name"],
                    created_at=_dt(s["created_at"]),
                )
            )
        session.flush()

        # --- Collections ---
        for c in manifest["collections"]:
            session.add(
                Collection(
                    id=uuid.UUID(c["id"]),
                    space_id=uuid.UUID(c["space_id"]),
                    slug=c["slug"],
                    name=c["name"],
                    created_at=_dt(c["created_at"]),
                )
            )
        session.flush()

        # --- Pages (current_revision_id set after revisions are inserted) ---
        page_current_revisions: dict[uuid.UUID, uuid.UUID] = {}
        for p in manifest["pages"]:
            page_id = uuid.UUID(p["id"])
            session.add(
                Page(
                    id=page_id,
                    collection_id=uuid.UUID(p["collection_id"]),
                    slug=p["slug"],
                    title=p["title"],
                    current_revision_id=None,
                    created_at=_dt(p["created_at"]),
                )
            )
            if p["current_revision_id"]:
                page_current_revisions[page_id] = uuid.UUID(p["current_revision_id"])
        session.flush()

        # --- Revisions ---
        for r in manifest["revisions"]:
            rev_file = f"revisions/{r['page_id']}/{r['id']}.md"
            if rev_file not in names:
                raise ValueError(f"Bundle is missing revision file: {rev_file}")
            content = zf.read(rev_file).decode()
            session.add(
                Revision(
                    id=uuid.UUID(r["id"]),
                    page_id=uuid.UUID(r["page_id"]),
                    content=content,
                    created_at=_dt(r["created_at"]),
                )
            )
        session.flush()

        # --- Wire up current_revision_id now that revisions exist ---
        for page_id, rev_id in page_current_revisions.items():
            page = session.get(Page, page_id)
            page.current_revision_id = rev_id
        session.flush()

        # --- Attachments ---
        for att in manifest["attachments"]:
            att_id = att["id"]
            ext = Path(att["filename"]).suffix
            asset_file = f"assets/{att_id}{ext}"
            if asset_file not in names:
                raise ValueError(f"Bundle is missing asset file: {asset_file}")

            data = zf.read(asset_file)
            actual_hash = _sha256(data)
            if actual_hash != att["hash"]:
                raise RuntimeError(
                    f"Hash mismatch for attachment {att_id} ({att['filename']}): "
                    f"expected {att['hash']}, got {actual_hash}"
                )

            storage.write(att_id, att["filename"], data)
            session.add(
                Attachment(
                    id=uuid.UUID(att_id),
                    page_id=uuid.UUID(att["page_id"]),
                    filename=att["filename"],
                    hash=att["hash"],
                    size_bytes=att["size_bytes"],
                    created_at=_dt(att["created_at"]),
                )
            )
        session.flush()

    return ws_meta["slug"]
