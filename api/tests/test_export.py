"""Integration tests for the export command.

Runs against a live PostgreSQL database (same Docker Compose default as other tests).
Each test rolls back its transaction so the DB stays clean between runs.
"""

import hashlib
import json
import os
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from freehold.export import SCHEMA_VERSION, export_workspace
from freehold.models import Attachment, Collection, Organization, Page, Revision, Space, Workspace
from freehold.storage import StorageAdapter

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://freehold:freehold@localhost:5433/freehold")


# ---------------------------------------------------------------------------
# Fake storage adapter (in-memory; no filesystem required)
# ---------------------------------------------------------------------------


class FakeStorageAdapter(StorageAdapter):
    def __init__(self, files: dict[tuple[str, str], bytes] | None = None) -> None:
        # keys are (attachment_id, filename)
        self._files: dict[tuple[str, str], bytes] = files or {}

    def read(self, attachment_id: str, filename: str) -> bytes:
        key = (attachment_id, filename)
        if key not in self._files:
            raise FileNotFoundError(f"No fake file for {key}")
        return self._files[key]

    def write(self, attachment_id: str, filename: str, data: bytes) -> None:
        self._files[(attachment_id, filename)] = data


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
def seeded(session):
    """Seed a workspace with two pages (two revisions each) and one attachment."""
    org = Organization(slug="export-test-org", name="Export Test Org")
    session.add(org)
    session.flush()

    ws = Workspace(org_id=org.id, slug="export-test-ws", name="Export Test Workspace")
    session.add(ws)
    session.flush()

    space = Space(workspace_id=ws.id, slug="sp", name="Space")
    session.add(space)
    session.flush()

    col = Collection(space_id=space.id, slug="col", name="Collection")
    session.add(col)
    session.flush()

    # Page 1 with two revisions and one internal link to page 2 (added later).
    page1 = Page(collection_id=col.id, slug="page-one", title="Page One")
    session.add(page1)
    session.flush()

    rev1a = Revision(page_id=page1.id, content="# Page One\nFirst draft.")
    session.add(rev1a)
    session.flush()

    rev1b = Revision(page_id=page1.id, content="# Page One\nSecond draft.")
    session.add(rev1b)
    session.flush()

    page1.current_revision_id = rev1b.id
    session.flush()

    # Page 2 (target of internal link from page 1).
    page2 = Page(collection_id=col.id, slug="page-two", title="Page Two")
    session.add(page2)
    session.flush()

    rev2 = Revision(page_id=page2.id, content="# Page Two\nOnly revision.")
    session.add(rev2)
    session.flush()

    page2.current_revision_id = rev2.id
    session.flush()

    # Update page1 current revision to include a link to page2.
    link_content = f"# Page One\n[See page two](/pages/{page2.id})"
    rev1c = Revision(page_id=page1.id, content=link_content)
    session.add(rev1c)
    session.flush()

    page1.current_revision_id = rev1c.id
    session.flush()

    # Attachment on page1.
    att_data = b"fake image bytes"
    att_hash = hashlib.sha256(att_data).hexdigest()
    att = Attachment(
        page_id=page1.id,
        filename="photo.png",
        hash=att_hash,
        size_bytes=len(att_data),
    )
    session.add(att)
    session.flush()

    storage = FakeStorageAdapter({(str(att.id), "photo.png"): att_data})

    return {
        "workspace": ws,
        "pages": [page1, page2],
        "attachment": att,
        "attachment_data": att_data,
        "storage": storage,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_export_produces_zip(seeded, session, tmp_path):
    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )

    assert result.exists()
    assert result.suffix == ".zip"
    assert "export-test-ws" in result.name


def test_zip_contains_expected_members(seeded, session, tmp_path):
    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )

    with zipfile.ZipFile(result) as zf:
        names = set(zf.namelist())

    page1_id = str(seeded["pages"][0].id)
    page2_id = str(seeded["pages"][1].id)
    att_id = str(seeded["attachment"].id)

    assert "manifest.json" in names
    assert "links.json" in names
    assert f"pages/{page1_id}.md" in names
    assert f"pages/{page2_id}.md" in names
    assert f"assets/{att_id}.png" in names


def test_manifest_content(seeded, session, tmp_path):
    ws = seeded["workspace"]
    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )

    with zipfile.ZipFile(result) as zf:
        manifest = json.loads(zf.read("manifest.json"))

    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["workspace"]["slug"] == ws.slug
    assert manifest["workspace"]["id"] == str(ws.id)

    assert len(manifest["spaces"]) == 1
    assert len(manifest["collections"]) == 1
    assert len(manifest["pages"]) == 2
    assert len(manifest["revisions"]) == 4  # rev1a, rev1b, rev1c, rev2
    assert len(manifest["attachments"]) == 1

    att_record = manifest["attachments"][0]
    assert att_record["hash"] == seeded["attachment"].hash
    assert att_record["filename"] == "photo.png"
    assert "created_at" in att_record


def test_page_content_matches_current_revision(seeded, session, tmp_path):
    page1 = seeded["pages"][0]
    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )

    with zipfile.ZipFile(result) as zf:
        content = zf.read(f"pages/{page1.id}.md").decode()

    assert f"/pages/{seeded['pages'][1].id}" in content


def test_all_revisions_are_included(seeded, session, tmp_path):
    page1 = seeded["pages"][0]
    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )

    with zipfile.ZipFile(result) as zf:
        rev_files = [n for n in zf.namelist() if n.startswith(f"revisions/{page1.id}/")]

    # page1 has three revisions (rev1a, rev1b, rev1c)
    assert len(rev_files) == 3


def test_links_json(seeded, session, tmp_path):
    page1_id = str(seeded["pages"][0].id)
    page2_id = str(seeded["pages"][1].id)

    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )

    with zipfile.ZipFile(result) as zf:
        links = json.loads(zf.read("links.json"))

    internal = links["internal_links"]
    assert len(internal) == 1
    assert internal[0]["source_page_id"] == page1_id
    assert internal[0]["target_page_id"] == page2_id

    # page2 is linked to, so only page1 is orphaned (nothing links to it)
    assert page2_id not in links["orphaned_pages"]
    assert page1_id in links["orphaned_pages"]


def test_attachment_hash_mismatch_raises(seeded, session, tmp_path):
    att = seeded["attachment"]
    bad_storage = FakeStorageAdapter({(str(att.id), "photo.png"): b"corrupted bytes"})

    with pytest.raises(RuntimeError, match="Hash mismatch"):
        export_workspace(
            slug="export-test-ws",
            session=session,
            storage=bad_storage,
            output_path=tmp_path,
        )


def test_missing_workspace_raises(session, tmp_path):
    from freehold.storage import LocalFilesystemAdapter

    storage = LocalFilesystemAdapter("/tmp")
    with pytest.raises(ValueError, match="not found"):
        export_workspace(
            slug="no-such-workspace",
            session=session,
            storage=storage,
            output_path=tmp_path,
        )


def test_output_filename_default(seeded, session, tmp_path):
    result = export_workspace(
        slug="export-test-ws",
        session=session,
        storage=seeded["storage"],
        output_path=tmp_path,
    )
    assert result.name.startswith("freehold-export-export-test-ws-")
    assert result.name.endswith(".zip")
