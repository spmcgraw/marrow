"""Export a workspace to a portable zip bundle.

Bundle layout:
    freehold-export-{workspace-slug}-{timestamp}.zip
    ├── manifest.json
    ├── pages/{page-id}.md
    ├── assets/{asset-id}{ext}
    ├── revisions/{page-id}/{revision-id}.md
    └── links.json
"""

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Attachment, Page, Workspace
from .storage import StorageAdapter

SCHEMA_VERSION = "1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_hrefs(content: str) -> list[str]:
    """Return all link targets found in Markdown content."""
    return re.findall(r"\[(?:[^\]]*)\]\(([^)]+)\)", content)


def _collect_pages(workspace: Workspace) -> list[Page]:
    pages: list[Page] = []
    for space in workspace.spaces:
        for collection in space.collections:
            pages.extend(collection.pages)
    return pages


def _build_links(pages: list[Page], page_id_set: set[str]) -> dict:
    internal_links: list[dict] = []
    broken_links: list[dict] = []

    for page in pages:
        if page.current_revision is None:
            continue
        for href in _extract_hrefs(page.current_revision.content or ""):
            source = str(page.id)
            # Treat /pages/<id> paths and bare UUIDs that match known pages as internal.
            candidate = href.removeprefix("/pages/").rstrip("/")
            if candidate in page_id_set:
                internal_links.append(
                    {"source_page_id": source, "target_page_id": candidate, "href": href}
                )
            elif href.startswith("/") or not href.startswith(("http://", "https://")):
                broken_links.append({"source_page_id": source, "href": href})

    linked_ids = {lnk["target_page_id"] for lnk in internal_links}
    orphaned = [str(p.id) for p in pages if str(p.id) not in linked_ids]

    return {
        "internal_links": internal_links,
        "broken_links": broken_links,
        "orphaned_pages": orphaned,
    }


def _build_manifest(
    workspace: Workspace,
    pages: list[Page],
    attachment_records: list[dict],
    export_timestamp: str,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "export_timestamp": export_timestamp,
        "workspace": {
            "id": str(workspace.id),
            "slug": workspace.slug,
            "name": workspace.name,
            "created_at": workspace.created_at.isoformat(),
        },
        "page_count": len(pages),
        "attachment_count": len(attachment_records),
        "attachments": attachment_records,
    }


def export_workspace(
    slug: str,
    session: Session,
    storage: StorageAdapter,
    output_path: Path | None = None,
) -> Path:
    """Export *slug* to a zip bundle and return the path of the written file."""
    workspace = session.query(Workspace).filter_by(slug=slug).first()
    if workspace is None:
        raise ValueError(f"Workspace '{slug}' not found")

    pages = _collect_pages(workspace)
    page_id_set = {str(p.id) for p in pages}

    # Eagerly touch lazy-loaded relationships while the session is open.
    for page in pages:
        _ = page.current_revision
        _ = page.revisions
        _ = page.attachments

    export_timestamp = datetime.now(timezone.utc).isoformat()
    timestamp_fmt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_name = f"freehold-export-{workspace.slug}-{timestamp_fmt}.zip"

    if output_path is None:
        output_path = Path.cwd() / bundle_name
    elif output_path.is_dir():
        output_path = output_path / bundle_name

    attachment_records: list[dict] = []
    buf = BytesIO()

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for page in pages:
            page_id = str(page.id)

            # Current page content.
            content = page.current_revision.content if page.current_revision else ""
            zf.writestr(f"pages/{page_id}.md", content)

            # Every revision (append-only history).
            for rev in page.revisions:
                zf.writestr(f"revisions/{page_id}/{rev.id}.md", rev.content)

        # Attachments — verify hash before including.
        all_attachments: list[Attachment] = []
        for page in pages:
            all_attachments.extend(page.attachments)

        for att in all_attachments:
            att_id = str(att.id)
            ext = Path(att.filename).suffix
            data = storage.read(att_id, att.filename)
            actual_hash = _sha256(data)
            if actual_hash != att.hash:
                raise RuntimeError(
                    f"Hash mismatch for attachment {att_id} ({att.filename}): "
                    f"expected {att.hash}, got {actual_hash}"
                )
            zf.writestr(f"assets/{att_id}{ext}", data)
            attachment_records.append(
                {
                    "id": att_id,
                    "page_id": str(att.page_id),
                    "filename": att.filename,
                    "hash": att.hash,
                    "size_bytes": att.size_bytes,
                }
            )

        zf.writestr("links.json", json.dumps(_build_links(pages, page_id_set), indent=2))
        zf.writestr(
            "manifest.json",
            json.dumps(
                _build_manifest(workspace, pages, attachment_records, export_timestamp), indent=2
            ),
        )

    output_path.write_bytes(buf.getvalue())
    return output_path
