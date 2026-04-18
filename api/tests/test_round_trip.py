"""Round-trip integration test: export → wipe → restore → verify.

This is the regression anchor for the restore guarantee. A failure here is a
critical bug that must be fixed before any merge.

Run from the api/ directory:
    pytest tests/test_round_trip.py
"""

import hashlib
import os
import uuid

import psycopg2
import pytest
from alembic.config import Config
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from marrow.export import export_workspace
from marrow.models import Attachment, Collection, Organization, Page, Revision, Space, Workspace
from marrow.restore import restore_workspace
from marrow.storage import StorageAdapter

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://marrow:marrow@localhost:5433/marrow")


# ---------------------------------------------------------------------------
# Fake storage adapter (in-memory)
# ---------------------------------------------------------------------------


class FakeStorageAdapter(StorageAdapter):
    def __init__(self) -> None:
        self._files: dict[tuple[str, str], bytes] = {}

    def read(self, attachment_id: str, filename: str) -> bytes:
        key = (attachment_id, filename)
        if key not in self._files:
            raise FileNotFoundError(f"No file for {key}")
        return self._files[key]

    def write(self, attachment_id: str, filename: str, data: bytes) -> None:
        self._files[(attachment_id, filename)] = data

    def has(self, attachment_id: str, filename: str) -> bool:
        return (attachment_id, filename) in self._files


# ---------------------------------------------------------------------------
# Fresh database fixture
# ---------------------------------------------------------------------------


def _base_dsn() -> str:
    return DATABASE_URL.rsplit("/", 1)[0]


def _alembic_cfg(url: str) -> Config:
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="module")
def db_url():
    """Create a fresh database, run migrations, yield URL, then drop it."""
    db_name = f"marrow_roundtrip_{uuid.uuid4().hex[:8]}"

    admin = psycopg2.connect(f"{_base_dsn()}/postgres")
    admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{db_name}"')
    admin.close()

    url = f"{_base_dsn()}/{db_name}"
    command.upgrade(_alembic_cfg(url), "head")

    yield url

    admin = psycopg2.connect(f"{_base_dsn()}/postgres")
    admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with admin.cursor() as cur:
        cur.execute(f'DROP DATABASE "{db_name}" WITH (FORCE)')
    admin.close()


# ---------------------------------------------------------------------------
# Round-trip test
# ---------------------------------------------------------------------------


def test_export_restore_round_trip(db_url, tmp_path):
    """Seed → export → wipe DB → restore → assert exact parity."""
    engine = create_engine(db_url)
    export_storage = FakeStorageAdapter()

    # ------------------------------------------------------------------
    # Phase 1: Seed a realistic workspace and capture ground truth
    # ------------------------------------------------------------------
    original: dict = {}

    with Session(engine) as session:
        org = Organization(slug="roundtrip-org", name="Round-Trip Org")
        session.add(org)
        session.flush()

        ws = Workspace(org_id=org.id, slug="roundtrip-ws", name="Round-Trip Workspace")
        session.add(ws)
        session.flush()

        space = Space(workspace_id=ws.id, slug="main", name="Main Space")
        session.add(space)
        session.flush()

        col = Collection(space_id=space.id, slug="docs", name="Documentation")
        session.add(col)
        session.flush()

        # Two pages, page-one with multiple revisions.
        page1 = Page(collection_id=col.id, slug="page-one", title="Page One")
        page2 = Page(collection_id=col.id, slug="page-two", title="Page Two")
        session.add_all([page1, page2])
        session.flush()

        rev1a = Revision(
            page_id=page1.id,
            content="# Page One\nFirst draft.",
            content_format="markdown",
        )
        rev1b = Revision(
            page_id=page1.id,
            content="# Page One\nSecond draft.",
            content_format="markdown",
        )
        # Simulate a JSON revision (BlockNote format) for the current revision
        import json as _json

        _h1_block = {
            "id": "a1",
            "type": "heading",
            "props": {
                "level": 1,
                "textColor": "default",
                "backgroundColor": "default",
                "textAlignment": "left",
            },
            "content": [{"type": "text", "text": "Page One", "styles": {}}],
            "children": [],
        }
        _p_block = {
            "id": "a2",
            "type": "paragraph",
            "props": {
                "textColor": "default",
                "backgroundColor": "default",
                "textAlignment": "left",
            },
            "content": [
                {"type": "text", "text": "See also ", "styles": {}},
                {
                    "type": "link",
                    "href": f"/pages/{page2.id}",
                    "content": [{"type": "text", "text": "Page Two", "styles": {}}],
                },
            ],
            "children": [],
        }
        rev1c_content = _json.dumps([_h1_block, _p_block])
        rev1c = Revision(
            page_id=page1.id,
            content=rev1c_content,
            content_format="json",
        )
        rev2a = Revision(
            page_id=page2.id,
            content="# Page Two\nOnly revision.",
            content_format="markdown",
        )
        session.add_all([rev1a, rev1b, rev1c, rev2a])
        session.flush()

        page1.current_revision_id = rev1c.id
        page2.current_revision_id = rev2a.id
        session.flush()

        att_data = b"binary attachment content"
        att_hash = hashlib.sha256(att_data).hexdigest()
        att = Attachment(
            page_id=page1.id,
            filename="diagram.png",
            hash=att_hash,
            size_bytes=len(att_data),
        )
        session.add(att)
        session.flush()

        export_storage.write(str(att.id), "diagram.png", att_data)

        # Capture ground truth before committing (IDs are assigned).
        original["organization"] = {
            "id": str(org.id),
            "slug": org.slug,
            "name": org.name,
        }
        original["workspace"] = {
            "id": str(ws.id),
            "org_id": str(ws.org_id),
            "slug": ws.slug,
            "name": ws.name,
        }
        original["space"] = {"id": str(space.id), "slug": space.slug, "name": space.name}
        original["collection"] = {"id": str(col.id), "slug": col.slug, "name": col.name}
        original["pages"] = {
            str(page1.id): {
                "slug": page1.slug,
                "title": page1.title,
                "current_revision_id": str(page1.current_revision_id),
                "revisions": {
                    str(rev1a.id): {
                        "content": rev1a.content,
                        "content_format": rev1a.content_format,
                    },
                    str(rev1b.id): {
                        "content": rev1b.content,
                        "content_format": rev1b.content_format,
                    },
                    str(rev1c.id): {
                        "content": rev1c.content,
                        "content_format": rev1c.content_format,
                    },
                },
            },
            str(page2.id): {
                "slug": page2.slug,
                "title": page2.title,
                "current_revision_id": str(page2.current_revision_id),
                "revisions": {
                    str(rev2a.id): {
                        "content": rev2a.content,
                        "content_format": rev2a.content_format,
                    },
                },
            },
        }
        original["attachment"] = {
            "id": str(att.id),
            "filename": att.filename,
            "hash": att.hash,
            "size_bytes": att.size_bytes,
            "data": att_data,
        }

        session.commit()

    # ------------------------------------------------------------------
    # Phase 2: Export
    # ------------------------------------------------------------------
    with Session(engine) as session:
        bundle_path = export_workspace(
            slug="roundtrip-ws",
            session=session,
            storage=export_storage,
            output_path=tmp_path,
        )

    assert bundle_path.exists(), "Export produced no bundle"

    # ------------------------------------------------------------------
    # Phase 3: Wipe the database
    # TRUNCATE with CASCADE is a statement-level operation that bypasses
    # the row-level immutability trigger on the revisions table.
    # ------------------------------------------------------------------
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE organizations, workspaces CASCADE"))
        conn.commit()

    # ------------------------------------------------------------------
    # Phase 4: Restore
    # ------------------------------------------------------------------
    restore_storage = FakeStorageAdapter()

    with Session(engine) as session:
        slug = restore_workspace(bundle_path, session, restore_storage)
        session.commit()

    assert slug == "roundtrip-ws"

    # ------------------------------------------------------------------
    # Phase 5: Assert restored state matches original exactly
    # ------------------------------------------------------------------
    with Session(engine) as session:
        ws = session.query(Workspace).filter_by(slug="roundtrip-ws").one()

        # Organization identity
        restored_org = session.get(Organization, uuid.UUID(original["organization"]["id"]))
        assert restored_org is not None, "Organization missing after restore"
        assert restored_org.slug == original["organization"]["slug"]
        assert restored_org.name == original["organization"]["name"]

        # Workspace identity
        assert str(ws.id) == original["workspace"]["id"]
        assert ws.name == original["workspace"]["name"]
        assert str(ws.org_id) == original["workspace"]["org_id"]

        # Space / collection structure
        assert len(ws.spaces) == 1
        restored_space = ws.spaces[0]
        assert str(restored_space.id) == original["space"]["id"]
        assert restored_space.slug == original["space"]["slug"]

        assert len(restored_space.collections) == 1
        restored_col = restored_space.collections[0]
        assert str(restored_col.id) == original["collection"]["id"]
        assert restored_col.slug == original["collection"]["slug"]

        # Pages
        restored_pages = {str(p.id): p for p in restored_col.pages}
        assert set(restored_pages.keys()) == set(original["pages"].keys()), (
            f"Page IDs differ after restore. "
            f"Got: {set(restored_pages.keys())} Expected: {set(original['pages'].keys())}"
        )

        for page_id, expected in original["pages"].items():
            page = restored_pages[page_id]
            assert page.slug == expected["slug"]
            assert page.title == expected["title"]
            assert str(page.current_revision_id) == expected["current_revision_id"], (
                f"current_revision_id mismatch for page {page_id}"
            )

            # Revision history — every revision must be present with exact content
            restored_revs = {str(r.id): r for r in page.revisions}
            assert set(restored_revs.keys()) == set(expected["revisions"].keys()), (
                f"Revision IDs differ for page {page_id}. "
                f"Got: {set(restored_revs.keys())} Expected: {set(expected['revisions'].keys())}"
            )
            for rev_id, rev_data in expected["revisions"].items():
                assert restored_revs[rev_id].content == rev_data["content"], (
                    f"Content mismatch for revision {rev_id}"
                )
                assert restored_revs[rev_id].content_format == rev_data["content_format"], (
                    f"content_format mismatch for revision {rev_id}"
                )

        # Attachment metadata
        exp_att = original["attachment"]
        restored_att = session.get(Attachment, uuid.UUID(exp_att["id"]))
        assert restored_att is not None, "Attachment row missing after restore"
        assert restored_att.filename == exp_att["filename"]
        assert restored_att.hash == exp_att["hash"]
        assert restored_att.size_bytes == exp_att["size_bytes"]

        # Attachment binary data — verify via hash
        assert restore_storage.has(exp_att["id"], exp_att["filename"]), (
            "Attachment file missing from storage after restore"
        )
        restored_data = restore_storage.read(exp_att["id"], exp_att["filename"])
        assert hashlib.sha256(restored_data).hexdigest() == exp_att["hash"], (
            "Attachment hash mismatch after restore"
        )
        assert restored_data == exp_att["data"], "Attachment bytes differ after restore"

    engine.dispose()
