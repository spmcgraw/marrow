# ruff: noqa: F821
# (#123) v3 restore logic below references the removed Page/Collection ORM
# classes; these calls NameError at runtime. The v3 → v4 migration lands in
# #133 (2.0k), which will reference this code as the legacy bundle reader.
"""Restore a workspace from an export bundle.

Usage:
    marrow restore <bundle.zip>
"""

import hashlib
import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Attachment, Organization, Revision, Space, Workspace

# NOTE (#123): Page/Collection imports removed; the v3 restore logic below still
# references them and will NameError at call time. Rewrite for the node-tree
# data model lands in #133 (2.0k) — v3 → v4 bundle migration.
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
            raise ValueError(f"Not a valid Marrow bundle: manifest.json missing in {bundle_path}")

        manifest = json.loads(zf.read("manifest.json"))

        schema_version = manifest.get("schema_version")
        if schema_version not in ("1", "2", "3"):
            raise ValueError(
                f"Unsupported bundle schema version '{schema_version}' (expected '1', '2', or '3')"
            )

        is_slim = manifest.get("slim", False)

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

        # --- Organization ---
        # v2/v3 bundles include org metadata; v1 bundles create a new org from workspace name.
        if schema_version in ("2", "3") and "organization" in manifest:
            org_meta = manifest["organization"]
            org_id = uuid.UUID(org_meta["id"])
            existing_org = session.get(Organization, org_id)
            if existing_org is None:
                session.add(
                    Organization(
                        id=org_id,
                        slug=org_meta["slug"],
                        name=org_meta["name"],
                        created_at=_dt(org_meta["created_at"]),
                    )
                )
                session.flush()
        else:
            # v1 bundle: create a new org named after the workspace
            org_id = uuid.uuid4()
            slug_candidate = f"{ws_meta['slug']}-imported"
            # Ensure slug uniqueness
            counter = 0
            slug = slug_candidate
            while session.query(Organization).filter_by(slug=slug).first() is not None:
                counter += 1
                slug = f"{slug_candidate}-{counter}"
            session.add(
                Organization(
                    id=org_id,
                    slug=slug,
                    name=f"{ws_meta['name']} (imported)",
                )
            )
            session.flush()

        # --- Workspace ---
        session.add(
            Workspace(
                id=ws_id,
                org_id=org_id,
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
        if is_slim:
            # Slim bundles omit revision history. Recreate one revision per page
            # from the current page content stored in pages/.
            for p in manifest["pages"]:
                page_id = uuid.UUID(p["id"])
                # Detect JSON vs Markdown from available files
                json_file = f"pages/{p['id']}.json"
                md_file = f"pages/{p['id']}.md"
                if json_file in names:
                    content = zf.read(json_file).decode()
                    content_format = "json"
                elif md_file in names:
                    content = zf.read(md_file).decode()
                    content_format = "markdown"
                else:
                    content = ""
                    content_format = "markdown"
                new_rev_id = uuid.uuid4()
                session.add(
                    Revision(
                        id=new_rev_id,
                        page_id=page_id,
                        content=content,
                        content_format=content_format,
                    )
                )
                page_current_revisions[page_id] = new_rev_id
        else:
            for r in manifest["revisions"]:
                content_format = r.get("content_format", "markdown")
                if content_format == "json":
                    # v3 bundle: canonical content is the .json file
                    rev_file = f"revisions/{r['page_id']}/{r['id']}.json"
                else:
                    rev_file = f"revisions/{r['page_id']}/{r['id']}.md"
                if rev_file not in names:
                    raise ValueError(f"Bundle is missing revision file: {rev_file}")
                content = zf.read(rev_file).decode()
                session.add(
                    Revision(
                        id=uuid.UUID(r["id"]),
                        page_id=uuid.UUID(r["page_id"]),
                        content=content,
                        content_format=content_format,
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
