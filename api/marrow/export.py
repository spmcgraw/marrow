"""Export a workspace to a portable zip bundle.

Bundle layout (schema v3):
    marrow-export-{workspace-slug}-{timestamp}.zip
    ├── manifest.json
    ├── pages/{page-id}.json          # canonical BlockNote JSON (v3 only, format='json')
    ├── pages/{page-id}.md            # human-readable Markdown (all versions)
    ├── assets/{asset-id}{ext}
    ├── revisions/{page-id}/{revision-id}.json   # for JSON-format revisions
    ├── revisions/{page-id}/{revision-id}.md     # for all revisions
    └── links.json

v1/v2 bundles only had .md files. v3 adds .json as the canonical format for
revisions stored as BlockNote JSON.
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

SCHEMA_VERSION = "3"


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


# ---------------------------------------------------------------------------
# BlockNote JSON → Markdown converter (for human-readable export)
# ---------------------------------------------------------------------------


def _inline_to_text(inline_content: list) -> str:
    """Convert BlockNote inline content array to Markdown text."""
    text = ""
    for item in inline_content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type", "text")
        if item_type == "text":
            t = item.get("text", "")
            styles = item.get("styles", {})
            if styles.get("code"):
                t = f"`{t}`"
            if styles.get("bold"):
                t = f"**{t}**"
            if styles.get("italic"):
                t = f"*{t}*"
            if styles.get("strike"):
                t = f"~~{t}~~"
            text += t
        elif item_type == "link":
            href = item.get("href", "")
            link_content = item.get("content", [])
            link_text = _inline_to_text(link_content)
            text += f"[{link_text}]({href})"
        elif item_type == "mention":
            # Member mention: lossy fallback to "@DisplayName" plaintext.
            # The canonical userId is preserved in the JSON revision.
            display_name = item.get("props", {}).get("displayName", "")
            if display_name:
                text += f"@{display_name}"
    return text


def _blocks_to_markdown(blocks: list, indent: int = 0) -> list[str]:
    """Recursively convert BlockNote block array to Markdown lines."""
    lines: list[str] = []
    prefix = "  " * indent

    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "paragraph")
        content = block.get("content", [])
        props = block.get("props", {})
        children = block.get("children", [])

        # Table blocks store content as a 2D grid, not inline content
        if btype == "table":
            rows = content if isinstance(content, list) else []
            if rows:
                md_rows = []
                for i, row in enumerate(rows):
                    cells = row.get("cells", []) if isinstance(row, dict) else []
                    cell_texts = [
                        _inline_to_text(cell) if isinstance(cell, list) else str(cell)
                        for cell in cells
                    ]
                    md_rows.append(f"{prefix}| {' | '.join(cell_texts)} |")
                    if i == 0:
                        separator = f"{prefix}|" + "|".join(
                            [" --- " for _ in cells]
                        ) + "|"
                        md_rows.append(separator)
                lines.extend(md_rows)
            continue

        text = _inline_to_text(content) if isinstance(content, list) else str(content)

        if btype == "paragraph":
            if text.strip():
                lines.append(f"{prefix}{text}")
            else:
                lines.append("")
        elif btype == "heading":
            level = int(props.get("level", 1))
            lines.append(f"{prefix}{'#' * level} {text}")
        elif btype == "bulletListItem":
            lines.append(f"{prefix}- {text}")
        elif btype == "numberedListItem":
            lines.append(f"{prefix}1. {text}")
        elif btype == "checkListItem":
            checked = "x" if props.get("checked") else " "
            lines.append(f"{prefix}- [{checked}] {text}")
        elif btype == "codeBlock":
            language = props.get("language", "")
            lines.append(f"{prefix}```{language}")
            lines.append(text)
            lines.append(f"{prefix}```")
        elif btype == "quote":
            lines.append(f"{prefix}> {text}")
        elif btype == "divider":
            lines.append(f"{prefix}---")
        elif btype == "image":
            url = props.get("url", "")
            caption = props.get("caption", "") or props.get("name", "image")
            lines.append(f"{prefix}![{caption}]({url})")
        elif btype == "file":
            url = props.get("url", "")
            name = props.get("name", "file")
            lines.append(f"{prefix}[{name}]({url})")
        elif btype == "toggleListItem":
            lines.append(f"{prefix}> {text}")
        else:
            if text.strip():
                lines.append(f"{prefix}{text}")

        if children:
            lines.extend(_blocks_to_markdown(children, indent + 1))

    return lines


def blocks_to_markdown(content_json: str) -> str:
    """Convert a BlockNote JSON string to human-readable Markdown.

    Used during export to generate the .md companion file for JSON revisions.
    Returns the original string unchanged if parsing fails.
    """
    try:
        blocks = json.loads(content_json)
        if not isinstance(blocks, list):
            return content_json
        lines = _blocks_to_markdown(blocks)
        return "\n".join(lines)
    except (json.JSONDecodeError, TypeError, KeyError):
        return content_json


# ---------------------------------------------------------------------------
# Link analysis (Markdown only — best-effort for JSON revisions)
# ---------------------------------------------------------------------------


def _build_links(pages: list[Page], page_id_set: set[str]) -> dict:
    internal_links: list[dict] = []
    broken_links: list[dict] = []

    for page in pages:
        if page.current_revision is None:
            continue
        content = page.current_revision.content or ""
        content_format = page.current_revision.content_format

        # For JSON revisions, convert to markdown first for link extraction
        if content_format == "json":
            content = blocks_to_markdown(content)

        for href in _extract_hrefs(content):
            source = str(page.id)
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
    spaces = workspace.spaces
    collections = [c for s in spaces for c in s.collections]

    revision_records = [
        {
            "id": str(rev.id),
            "page_id": str(rev.page_id),
            "content_format": rev.content_format,
            "created_at": rev.created_at.isoformat(),
        }
        for page in pages
        for rev in page.revisions
    ]

    org = workspace.organization
    return {
        "schema_version": SCHEMA_VERSION,
        "export_timestamp": export_timestamp,
        "organization": {
            "id": str(org.id),
            "slug": org.slug,
            "name": org.name,
            "created_at": org.created_at.isoformat(),
        },
        "workspace": {
            "id": str(workspace.id),
            "org_id": str(workspace.org_id),
            "slug": workspace.slug,
            "name": workspace.name,
            "created_at": workspace.created_at.isoformat(),
        },
        "spaces": [
            {
                "id": str(s.id),
                "workspace_id": str(s.workspace_id),
                "slug": s.slug,
                "name": s.name,
                "created_at": s.created_at.isoformat(),
            }
            for s in spaces
        ],
        "collections": [
            {
                "id": str(c.id),
                "space_id": str(c.space_id),
                "slug": c.slug,
                "name": c.name,
                "created_at": c.created_at.isoformat(),
            }
            for c in collections
        ],
        "pages": [
            {
                "id": str(p.id),
                "collection_id": str(p.collection_id),
                "slug": p.slug,
                "title": p.title,
                "current_revision_id": (
                    str(p.current_revision_id) if p.current_revision_id else None
                ),
                "created_at": p.created_at.isoformat(),
            }
            for p in pages
        ],
        "revisions": revision_records,
        "attachments": attachment_records,
    }


def estimate_export_sizes(
    slug: str,
    session: Session,
    storage: StorageAdapter,
) -> dict:
    """Return estimated byte sizes for full and slim exports of *slug*.

    Sizes are raw (pre-compression) byte counts. Actual zip files will be
    smaller due to DEFLATE compression, but the ratio between full and slim
    is accurate.
    """
    workspace = session.query(Workspace).filter_by(slug=slug).first()
    if workspace is None:
        raise ValueError(f"Workspace '{slug}' not found")

    pages = _collect_pages(workspace)
    for page in pages:
        _ = page.current_revision
        _ = page.revisions
        _ = page.attachments

    attachment_bytes = 0
    for page in pages:
        for att in page.attachments:
            attachment_bytes += att.size_bytes

    current_content_bytes = sum(
        len((page.current_revision.content or "").encode())
        for page in pages
        if page.current_revision
    )
    revision_bytes = sum(
        len((rev.content or "").encode())
        for page in pages
        for rev in page.revisions
    )

    slim_bytes = current_content_bytes + attachment_bytes
    full_bytes = slim_bytes + revision_bytes

    return {"full_bytes": full_bytes, "slim_bytes": slim_bytes}


def export_workspace(
    slug: str,
    session: Session,
    storage: StorageAdapter,
    output_path: Path | None = None,
    slim: bool = False,
) -> Path:
    """Export *slug* to a zip bundle and return the path of the written file.

    When *slim* is True the revisions/ directory is omitted, producing a
    current-content-only bundle that is smaller but cannot restore full history.
    """
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
    slim_suffix = "-slim" if slim else ""
    bundle_name = f"marrow-export-{workspace.slug}{slim_suffix}-{timestamp_fmt}.zip"

    if output_path is None:
        output_path = Path.cwd() / bundle_name
    elif output_path.is_dir():
        output_path = output_path / bundle_name

    attachment_records: list[dict] = []
    buf = BytesIO()

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for page in pages:
            page_id = str(page.id)

            # Current page content — always write .md; also write .json for JSON format.
            if page.current_revision:
                content = page.current_revision.content
                fmt = page.current_revision.content_format
            else:
                content = ""
                fmt = "markdown"

            if fmt == "json":
                zf.writestr(f"pages/{page_id}.json", content)
                zf.writestr(f"pages/{page_id}.md", blocks_to_markdown(content))
            else:
                zf.writestr(f"pages/{page_id}.md", content)

            if not slim:
                # Every revision (append-only history).
                for rev in page.revisions:
                    rev_id = str(rev.id)
                    if rev.content_format == "json":
                        zf.writestr(f"revisions/{page_id}/{rev_id}.json", rev.content)
                        zf.writestr(
                            f"revisions/{page_id}/{rev_id}.md",
                            blocks_to_markdown(rev.content),
                        )
                    else:
                        zf.writestr(f"revisions/{page_id}/{rev_id}.md", rev.content)

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
                    "created_at": att.created_at.isoformat(),
                }
            )

        zf.writestr("links.json", json.dumps(_build_links(pages, page_id_set), indent=2))

        manifest = _build_manifest(workspace, pages, attachment_records, export_timestamp)
        if slim:
            manifest["slim"] = True
            manifest["revisions"] = []

        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    output_path.write_bytes(buf.getvalue())
    return output_path
