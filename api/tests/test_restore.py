"""Integration tests for the restore command.

Runs against a live PostgreSQL database. Each test uses hand-crafted bundles
with unique UUIDs and rolls back its transaction so the DB stays clean.
"""

import hashlib
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from marrow.export import SCHEMA_VERSION
from marrow.models import Attachment, Page, Revision, Workspace
from marrow.restore import restore_workspace
from marrow.storage import StorageAdapter

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://freehold:freehold@localhost:5433/freehold")


# ---------------------------------------------------------------------------
# Fake storage adapter (in-memory)
# ---------------------------------------------------------------------------


class FakeStorageAdapter(StorageAdapter):
    def __init__(self) -> None:
        self._files: dict[tuple[str, str], bytes] = {}

    def read(self, attachment_id: str, filename: str) -> bytes:
        key = (attachment_id, filename)
        if key not in self._files:
            raise FileNotFoundError(f"No fake file for {key}")
        return self._files[key]

    def write(self, attachment_id: str, filename: str, data: bytes) -> None:
        self._files[(attachment_id, filename)] = data

    def has(self, attachment_id: str, filename: str) -> bool:
        return (attachment_id, filename) in self._files


# ---------------------------------------------------------------------------
# Bundle builder helper
# ---------------------------------------------------------------------------


def _make_bundle(
    *,
    ws_id: uuid.UUID | None = None,
    ws_slug: str = "test-ws",
    ws_name: str = "Test Workspace",
    org_id: uuid.UUID | None = None,
    with_attachment: bool = False,
    attachment_data: bytes = b"attachment bytes",
    corrupt_attachment: bool = False,
    schema_version: str = SCHEMA_VERSION,
    omit_manifest: bool = False,
    omit_revision_file: bool = False,
) -> tuple[Path, dict]:
    """Return (bundle_path written to a tmp BytesIO, manifest dict)."""
    now = datetime.now(timezone.utc).isoformat()

    ws_id = ws_id or uuid.uuid4()
    org_id = org_id or uuid.uuid4()
    space_id = uuid.uuid4()
    col_id = uuid.uuid4()
    page_id = uuid.uuid4()
    rev_id = uuid.uuid4()
    att_id = uuid.uuid4()

    att_hash = hashlib.sha256(attachment_data).hexdigest()

    manifest: dict = {
        "schema_version": schema_version,
        "export_timestamp": now,
        "organization": {
            "id": str(org_id),
            "slug": f"{ws_slug}-org",
            "name": f"{ws_name} Org",
            "created_at": now,
        },
        "workspace": {
            "id": str(ws_id),
            "org_id": str(org_id),
            "slug": ws_slug,
            "name": ws_name,
            "created_at": now,
        },
        "spaces": [
            {
                "id": str(space_id),
                "workspace_id": str(ws_id),
                "slug": "sp",
                "name": "Space",
                "created_at": now,
            }
        ],
        "collections": [
            {
                "id": str(col_id),
                "space_id": str(space_id),
                "slug": "col",
                "name": "Col",
                "created_at": now,
            }
        ],
        "pages": [
            {
                "id": str(page_id),
                "collection_id": str(col_id),
                "slug": "pg",
                "title": "Page",
                "current_revision_id": str(rev_id),
                "created_at": now,
            }
        ],
        "revisions": [{"id": str(rev_id), "page_id": str(page_id), "created_at": now}],
        "attachments": (
            [
                {
                    "id": str(att_id),
                    "page_id": str(page_id),
                    "filename": "file.txt",
                    "hash": att_hash,
                    "size_bytes": len(attachment_data),
                    "created_at": now,
                }
            ]
            if with_attachment
            else []
        ),
    }

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if not omit_manifest:
            zf.writestr("manifest.json", json.dumps(manifest))
        if not omit_revision_file:
            zf.writestr(f"revisions/{page_id}/{rev_id}.md", "# Page\nContent.")
        zf.writestr(f"pages/{page_id}.md", "# Page\nContent.")
        zf.writestr(
            "links.json",
            json.dumps(
                {"internal_links": [], "broken_links": [], "orphaned_pages": [str(page_id)]}
            ),
        )
        if with_attachment:
            asset_bytes = b"corrupted" if corrupt_attachment else attachment_data
            zf.writestr(f"assets/{att_id}.txt", asset_bytes)

    return buf.getvalue(), manifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(DATABASE_URL)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
        s.rollback()


@pytest.fixture
def storage():
    return FakeStorageAdapter()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _write_bundle(tmp_path: Path, bundle_bytes: bytes, name: str = "bundle.zip") -> Path:
    p = tmp_path / name
    p.write_bytes(bundle_bytes)
    return p


def test_restore_creates_workspace(session, storage, tmp_path):
    bundle_bytes, manifest = _make_bundle(ws_slug="restore-creates-ws")
    path = _write_bundle(tmp_path, bundle_bytes)

    slug = restore_workspace(path, session, storage)

    assert slug == "restore-creates-ws"
    ws = session.query(Workspace).filter_by(slug="restore-creates-ws").first()
    assert ws is not None
    assert str(ws.id) == manifest["workspace"]["id"]


def test_restore_preserves_full_hierarchy(session, storage, tmp_path):
    bundle_bytes, manifest = _make_bundle(ws_slug="restore-hierarchy-ws")
    path = _write_bundle(tmp_path, bundle_bytes)

    restore_workspace(path, session, storage)

    ws = session.query(Workspace).filter_by(slug="restore-hierarchy-ws").first()
    assert len(ws.spaces) == 1
    space = ws.spaces[0]
    assert str(space.id) == manifest["spaces"][0]["id"]
    assert len(space.collections) == 1
    col = space.collections[0]
    assert str(col.id) == manifest["collections"][0]["id"]
    assert len(col.pages) == 1
    page = col.pages[0]
    assert str(page.id) == manifest["pages"][0]["id"]
    assert len(page.revisions) == 1
    assert str(page.current_revision_id) == manifest["pages"][0]["current_revision_id"]


def test_restore_preserves_page_content(session, storage, tmp_path):
    bundle_bytes, manifest = _make_bundle(ws_slug="restore-content-ws")
    path = _write_bundle(tmp_path, bundle_bytes)

    restore_workspace(path, session, storage)

    page_id = manifest["pages"][0]["id"]
    rev_id = manifest["revisions"][0]["id"]
    page = session.get(Page, uuid.UUID(page_id))
    rev = session.get(Revision, uuid.UUID(rev_id))
    assert rev is not None
    assert rev.content == "# Page\nContent."
    assert str(page.current_revision_id) == rev_id


def test_restore_with_attachment(session, storage, tmp_path):
    att_data = b"hello attachment"
    bundle_bytes, manifest = _make_bundle(
        ws_slug="restore-att-ws", with_attachment=True, attachment_data=att_data
    )
    path = _write_bundle(tmp_path, bundle_bytes)

    restore_workspace(path, session, storage)

    att_meta = manifest["attachments"][0]
    att = session.get(Attachment, uuid.UUID(att_meta["id"]))
    assert att is not None
    assert att.hash == att_meta["hash"]
    assert att.size_bytes == len(att_data)
    assert storage.has(att_meta["id"], "file.txt")
    assert storage._files[(att_meta["id"], "file.txt")] == att_data


def test_restore_verifies_attachment_hash(session, storage, tmp_path):
    bundle_bytes, _ = _make_bundle(
        ws_slug="restore-hash-ws", with_attachment=True, corrupt_attachment=True
    )
    path = _write_bundle(tmp_path, bundle_bytes)

    with pytest.raises(RuntimeError, match="Hash mismatch"):
        restore_workspace(path, session, storage)


def test_restore_duplicate_id_raises(session, storage, tmp_path):
    ws_id = uuid.uuid4()
    bundle_bytes, _ = _make_bundle(ws_id=ws_id, ws_slug="restore-dup-id-ws")
    path = _write_bundle(tmp_path, bundle_bytes)

    restore_workspace(path, session, storage)

    # Second restore with same ID.
    bundle_bytes2, _ = _make_bundle(ws_id=ws_id, ws_slug="restore-dup-id-ws-2")
    path2 = _write_bundle(tmp_path, bundle_bytes2, name="bundle2.zip")
    with pytest.raises(ValueError, match="already exists"):
        restore_workspace(path2, session, storage)


def test_restore_duplicate_slug_raises(session, storage, tmp_path):
    bundle_bytes, _ = _make_bundle(ws_slug="restore-dup-slug-ws")
    path = _write_bundle(tmp_path, bundle_bytes)

    restore_workspace(path, session, storage)

    # Second restore with same slug but different ID.
    bundle_bytes2, _ = _make_bundle(ws_slug="restore-dup-slug-ws")
    path2 = _write_bundle(tmp_path, bundle_bytes2, name="bundle2.zip")
    with pytest.raises(ValueError, match="already exists"):
        restore_workspace(path2, session, storage)


def test_restore_missing_manifest_raises(session, storage, tmp_path):
    bundle_bytes, _ = _make_bundle(ws_slug="restore-no-manifest-ws", omit_manifest=True)
    path = _write_bundle(tmp_path, bundle_bytes)

    with pytest.raises(ValueError, match="manifest.json missing"):
        restore_workspace(path, session, storage)


def test_restore_unsupported_schema_version_raises(session, storage, tmp_path):
    bundle_bytes, _ = _make_bundle(ws_slug="restore-bad-version-ws", schema_version="99")
    path = _write_bundle(tmp_path, bundle_bytes)

    with pytest.raises(ValueError, match="Unsupported bundle schema version"):
        restore_workspace(path, session, storage)


def test_restore_missing_revision_file_raises(session, storage, tmp_path):
    bundle_bytes, _ = _make_bundle(ws_slug="restore-missing-rev-ws", omit_revision_file=True)
    path = _write_bundle(tmp_path, bundle_bytes)

    with pytest.raises(ValueError, match="missing revision file"):
        restore_workspace(path, session, storage)


def test_restore_not_a_zip_raises(session, storage, tmp_path):
    path = tmp_path / "notazip.zip"
    path.write_bytes(b"this is not a zip")

    with pytest.raises(ValueError, match="Not a valid zip"):
        restore_workspace(path, session, storage)
