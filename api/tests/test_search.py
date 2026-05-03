"""Tests for PostgreSQL full-text search: triggers, endpoint, and scoping."""

import os
import uuid

import psycopg2
import pytest
from alembic.config import Config
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from marrow.models import Node, Organization, Revision, Space, Workspace

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://marrow:marrow@localhost:5433/marrow")


# ---------------------------------------------------------------------------
# Fixtures
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
    db_name = f"marrow_search_{uuid.uuid4().hex[:8]}"

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


@pytest.fixture(scope="module")
def engine(db_url):
    eng = create_engine(db_url)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    """Yield a session and rollback after each test for isolation."""
    conn = engine.connect()
    tx = conn.begin()
    session = Session(bind=conn)
    yield session
    session.close()
    tx.rollback()
    conn.close()


def _seed_workspace(db: Session) -> tuple[Workspace, Space]:
    org = Organization(slug=f"org-{uuid.uuid4().hex[:6]}", name="Test Org")
    db.add(org)
    db.flush()
    ws = Workspace(org_id=org.id, slug=f"ws-{uuid.uuid4().hex[:6]}", name="Test Workspace")
    db.add(ws)
    db.flush()
    space = Space(workspace_id=ws.id, slug="main", name="Main")
    db.add(space)
    db.flush()
    return ws, space


def _create_page(
    db: Session,
    space: Space,
    slug: str,
    name: str,
    content: str,
    parent: Node | None = None,
) -> Node:
    """Create a page node with one revision. Uses deferred FK for current_revision_id."""
    node = Node(
        space_id=space.id,
        parent_id=parent.id if parent else None,
        type="page",
        name=name,
        slug=slug,
        position="a0",
    )
    db.add(node)
    db.flush()
    rev = Revision(node_id=node.id, content=content)
    db.add(rev)
    db.flush()
    node.current_revision_id = rev.id
    db.flush()
    return node


def _create_folder(
    db: Session,
    space: Space,
    slug: str,
    name: str,
    parent: Node | None = None,
) -> Node:
    node = Node(
        space_id=space.id,
        parent_id=parent.id if parent else None,
        type="folder",
        name=name,
        slug=slug,
        position="a0",
    )
    db.add(node)
    db.flush()
    return node


# ---------------------------------------------------------------------------
# Trigger tests
# ---------------------------------------------------------------------------


def test_search_vector_populated_on_revision_insert(db):
    """Inserting a revision should populate the node's search_vector."""
    ws, space = _seed_workspace(db)
    page = _create_page(
        db, space, "test-page", "Quantum Computing",
        "An introduction to qubits and superposition",
    )

    db.refresh(page)
    assert page.search_vector is not None
    sv = str(page.search_vector).lower()
    assert "quantum" in sv or "comput" in sv


def test_search_vector_updates_on_new_revision(db):
    """Adding a new revision should update the search_vector with new content."""
    ws, space = _seed_workspace(db)
    page = _create_page(db, space, "evolving", "Original Name", "First draft about elephants")

    new_rev = Revision(node_id=page.id, content="Revised content about dinosaurs")
    db.add(new_rev)
    db.flush()
    page.current_revision_id = new_rev.id
    db.flush()

    db.refresh(page)
    sv = str(page.search_vector).lower()
    assert "dinosaur" in sv


def test_search_vector_updates_on_name_change(db):
    """Changing only the node name should refresh the search_vector."""
    ws, space = _seed_workspace(db)
    page = _create_page(db, space, "name-change", "Old Name", "Some body content")

    page.name = "Brand New Name"
    db.flush()
    db.refresh(page)

    sv = str(page.search_vector).lower()
    assert "brand" in sv


def test_search_vector_not_set_on_folder(db):
    """Folder nodes must never have a search_vector (enforced by shape constraint)."""
    ws, space = _seed_workspace(db)
    folder = _create_folder(db, space, "a-folder", "My Folder")

    db.refresh(folder)
    assert folder.search_vector is None


def test_search_vector_updates_on_slug_change(db):
    """Changing node slug should also trigger a search_vector refresh."""
    ws, space = _seed_workspace(db)
    page = _create_page(db, space, "original-slug", "Slug Test", "Some body content")

    page.slug = "new-slug"
    db.flush()
    db.refresh(page)

    # search_vector should still be populated (trigger must not have blanked it)
    assert page.search_vector is not None


# ---------------------------------------------------------------------------
# Search query tests (raw SQL mirroring PostgresSearchBackend logic)
# ---------------------------------------------------------------------------


def test_search_returns_matching_nodes(db):
    """Search should find page nodes matching the query."""
    ws, space = _seed_workspace(db)
    _create_page(db, space, "p1", "Rust Programming", "Rust is a systems programming language")
    _create_page(db, space, "p2", "Python Guide", "Python is great for scripting")

    rows = db.execute(
        text("""
            SELECT n.id, n.name,
                   ts_rank(n.search_vector, plainto_tsquery('english', :q)) AS rank
            FROM nodes n
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :ws_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND n.search_vector @@ plainto_tsquery('english', :q)
            ORDER BY rank DESC
        """),
        {"ws_id": ws.id, "q": "rust programming"},
    ).fetchall()

    assert len(rows) >= 1
    assert rows[0].name == "Rust Programming"


def test_search_empty_query_returns_nothing(db):
    """An empty FTS query should not match any nodes."""
    ws, space = _seed_workspace(db)
    _create_page(db, space, "p1", "Some Page", "Some content")

    rows = db.execute(
        text("""
            SELECT n.id FROM nodes n
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :ws_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND n.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws.id, "q": ""},
    ).fetchall()

    assert len(rows) == 0


def test_search_respects_workspace_scoping(db):
    """Nodes in a different workspace must not appear in search results."""
    ws1, space1 = _seed_workspace(db)
    ws2, space2 = _seed_workspace(db)

    _create_page(db, space1, "unique-ws1", "Blockchain Article", "Blockchain fundamentals")
    _create_page(db, space2, "unique-ws2", "Cooking Guide", "How to make pasta")

    rows = db.execute(
        text("""
            SELECT n.id, n.name FROM nodes n
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :ws_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND n.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws1.id, "q": "blockchain"},
    ).fetchall()

    assert len(rows) == 1
    assert rows[0].name == "Blockchain Article"

    rows2 = db.execute(
        text("""
            SELECT n.id FROM nodes n
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :ws_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND n.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws2.id, "q": "blockchain"},
    ).fetchall()

    assert len(rows2) == 0


def test_title_matches_rank_higher_than_body(db):
    """A match in the name (weight A) should rank higher than body (weight B)."""
    ws, space = _seed_workspace(db)
    _create_page(db, space, "name-match", "Kubernetes", "Container orchestration platform")
    _create_page(db, space, "body-match", "DevOps Guide", "This guide covers Kubernetes and more")

    rows = db.execute(
        text("""
            SELECT n.name,
                   ts_rank(n.search_vector, plainto_tsquery('english', :q)) AS rank
            FROM nodes n
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :ws_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND n.search_vector @@ plainto_tsquery('english', :q)
            ORDER BY rank DESC
        """),
        {"ws_id": ws.id, "q": "kubernetes"},
    ).fetchall()

    assert len(rows) == 2
    assert rows[0].name == "Kubernetes"


def test_deleted_nodes_excluded_from_search(db):
    """Soft-deleted nodes must not appear in search results."""
    from datetime import datetime, timezone

    ws, space = _seed_workspace(db)
    page = _create_page(db, space, "deleted-page", "Deleted Content", "I should not be found")

    page.deleted_at = datetime.now(tz=timezone.utc)
    db.flush()

    rows = db.execute(
        text("""
            SELECT n.id FROM nodes n
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :ws_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND n.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws.id, "q": "deleted"},
    ).fetchall()

    assert len(rows) == 0


# ---------------------------------------------------------------------------
# PostgresSearchBackend class tests (browse + name-ILIKE paths + node_path)
# ---------------------------------------------------------------------------


def test_backend_browse_empty_query_returns_all_pages(db):
    """An empty query should return all pages in the workspace (browse mode)."""
    from marrow.search import PostgresSearchBackend

    ws, space = _seed_workspace(db)
    _create_page(db, space, "page-a", "Alpha", "First page content")
    _create_page(db, space, "page-b", "Beta", "Second page content")

    backend = PostgresSearchBackend()
    results = backend.search(ws.id, "", db, limit=20)

    names = {r.name for r in results}
    assert "Alpha" in names
    assert "Beta" in names


def test_backend_name_ilike_matches_partial_name(db):
    """A partial name query should match via ILIKE even if body lacks the word."""
    from marrow.search import PostgresSearchBackend

    ws, space = _seed_workspace(db)
    _create_page(db, space, "getting-started", "Getting Started Guide", "Welcome to Marrow.")
    _create_page(db, space, "unrelated", "API Reference", "Lists all endpoints.")

    backend = PostgresSearchBackend()
    results = backend.search(ws.id, "getting", db, limit=20)

    names = [r.name for r in results]
    assert "Getting Started Guide" in names
    assert names[0] == "Getting Started Guide"


def test_backend_result_includes_node_path(db):
    """Search results should include the ordered ancestor folder names as node_path."""
    from marrow.search import PostgresSearchBackend

    ws, space = _seed_workspace(db)
    engineering = _create_folder(db, space, "engineering", "Engineering")
    backend_folder = _create_folder(db, space, "backend", "Backend", parent=engineering)
    _create_page(db, space, "auth-page", "Auth", "Authentication details", parent=backend_folder)

    backend = PostgresSearchBackend()
    results = backend.search(ws.id, "authentication", db, limit=20)

    assert len(results) == 1
    assert results[0].node_path == ["Engineering", "Backend"]


def test_backend_result_node_path_empty_for_root_page(db):
    """A page at space root (no parent) should have an empty node_path."""
    from marrow.search import PostgresSearchBackend

    ws, space = _seed_workspace(db)
    _create_page(db, space, "root-page", "Root Page", "Top-level content here")

    backend = PostgresSearchBackend()
    results = backend.search(ws.id, "top-level", db, limit=20)

    assert len(results) == 1
    assert results[0].node_path == []
