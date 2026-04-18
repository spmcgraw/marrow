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
from marrow.models import Collection, Organization, Page, Revision, Space, Workspace

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://freehold:freehold@localhost:5433/freehold")


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
    db_name = f"freehold_search_{uuid.uuid4().hex[:8]}"

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


def _seed_workspace(db: Session) -> tuple[Workspace, Space, Collection]:
    org = Organization(slug=f"org-{uuid.uuid4().hex[:6]}", name="Test Org")
    db.add(org)
    db.flush()
    ws = Workspace(org_id=org.id, slug=f"ws-{uuid.uuid4().hex[:6]}", name="Test Workspace")
    db.add(ws)
    db.flush()
    space = Space(workspace_id=ws.id, slug="main", name="Main")
    db.add(space)
    db.flush()
    col = Collection(space_id=space.id, slug="docs", name="Docs")
    db.add(col)
    db.flush()
    return ws, space, col


def _create_page(db: Session, col: Collection, slug: str, title: str, content: str) -> Page:
    page = Page(collection_id=col.id, slug=slug, title=title)
    db.add(page)
    db.flush()
    rev = Revision(page_id=page.id, content=content)
    db.add(rev)
    db.flush()
    page.current_revision_id = rev.id
    db.flush()
    return page


# ---------------------------------------------------------------------------
# Trigger tests
# ---------------------------------------------------------------------------


def test_search_vector_populated_on_revision_insert(db):
    """Inserting a revision should populate the page's search_vector."""
    ws, _, col = _seed_workspace(db)
    page = _create_page(
        db,
        col,
        "test-page",
        "Quantum Computing",
        "An introduction to qubits and superposition",
    )

    db.refresh(page)
    assert page.search_vector is not None
    sv = str(page.search_vector).lower()
    assert "quantum" in sv or "comput" in sv


def test_search_vector_updates_on_new_revision(db):
    """Adding a new revision should update the search_vector with new content."""
    ws, _, col = _seed_workspace(db)
    page = _create_page(db, col, "evolving", "Original Title", "First draft about elephants")

    new_rev = Revision(page_id=page.id, content="Revised content about dinosaurs")
    db.add(new_rev)
    db.flush()
    page.current_revision_id = new_rev.id
    db.flush()

    db.refresh(page)
    sv = str(page.search_vector).lower()
    assert "dinosaur" in sv


def test_search_vector_updates_on_title_change(db):
    """Changing only the page title should refresh the search_vector."""
    ws, _, col = _seed_workspace(db)
    page = _create_page(db, col, "title-change", "Old Title", "Some body content")

    page.title = "Brand New Title"
    db.flush()
    db.refresh(page)

    sv = str(page.search_vector).lower()
    assert "brand" in sv


# ---------------------------------------------------------------------------
# Search query tests (using raw SQL to test the PostgresSearchBackend logic)
# ---------------------------------------------------------------------------


def test_search_returns_matching_pages(db):
    """Search should find pages matching the query."""
    ws, _, col = _seed_workspace(db)
    _create_page(db, col, "p1", "Rust Programming", "Rust is a systems programming language")
    _create_page(db, col, "p2", "Python Guide", "Python is great for scripting")

    rows = db.execute(
        text("""
            SELECT p.id, p.title,
                   ts_rank(p.search_vector, plainto_tsquery('english', :q)) AS rank
            FROM pages p
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :ws_id
              AND p.search_vector @@ plainto_tsquery('english', :q)
            ORDER BY rank DESC
        """),
        {"ws_id": ws.id, "q": "rust programming"},
    ).fetchall()

    assert len(rows) >= 1
    assert rows[0].title == "Rust Programming"


def test_search_empty_query_returns_nothing(db):
    """An empty query should not match any pages."""
    ws, _, col = _seed_workspace(db)
    _create_page(db, col, "p1", "Some Page", "Some content")

    rows = db.execute(
        text("""
            SELECT p.id FROM pages p
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :ws_id
              AND p.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws.id, "q": ""},
    ).fetchall()

    assert len(rows) == 0


def test_search_respects_workspace_scoping(db):
    """Pages in a different workspace should not appear in search results."""
    ws1, _, col1 = _seed_workspace(db)
    ws2, _, col2 = _seed_workspace(db)

    _create_page(db, col1, "unique-ws1", "Blockchain Article", "Blockchain fundamentals")
    _create_page(db, col2, "unique-ws2", "Cooking Guide", "How to make pasta")

    # Search ws1 for "blockchain"
    rows = db.execute(
        text("""
            SELECT p.id, p.title FROM pages p
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :ws_id
              AND p.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws1.id, "q": "blockchain"},
    ).fetchall()

    assert len(rows) == 1
    assert rows[0].title == "Blockchain Article"

    # Search ws2 for "blockchain" — should find nothing
    rows2 = db.execute(
        text("""
            SELECT p.id FROM pages p
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :ws_id
              AND p.search_vector @@ plainto_tsquery('english', :q)
        """),
        {"ws_id": ws2.id, "q": "blockchain"},
    ).fetchall()

    assert len(rows2) == 0


def test_title_matches_rank_higher_than_body(db):
    """A match in the title (weight A) should rank higher than body (weight B)."""
    ws, _, col = _seed_workspace(db)
    _create_page(db, col, "title-match", "Kubernetes", "Container orchestration platform")
    _create_page(db, col, "body-match", "DevOps Guide", "This guide covers Kubernetes and more")

    rows = db.execute(
        text("""
            SELECT p.title,
                   ts_rank(p.search_vector, plainto_tsquery('english', :q)) AS rank
            FROM pages p
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :ws_id
              AND p.search_vector @@ plainto_tsquery('english', :q)
            ORDER BY rank DESC
        """),
        {"ws_id": ws.id, "q": "kubernetes"},
    ).fetchall()

    assert len(rows) == 2
    assert rows[0].title == "Kubernetes"


# ---------------------------------------------------------------------------
# PostgresSearchBackend class tests (browse + title-ILIKE paths)
# ---------------------------------------------------------------------------


def test_backend_browse_empty_query_returns_all_pages(db):
    """An empty query should return all pages in the workspace (browse mode)."""
    from marrow.search import PostgresSearchBackend

    ws, _, col = _seed_workspace(db)
    _create_page(db, col, "page-a", "Alpha", "First page content")
    _create_page(db, col, "page-b", "Beta", "Second page content")

    backend = PostgresSearchBackend()
    results = backend.search(ws.id, "", db, limit=20)

    titles = {r.title for r in results}
    assert "Alpha" in titles
    assert "Beta" in titles


def test_backend_title_ilike_matches_partial_title(db):
    """A partial title query should match via ILIKE even if body lacks the word."""
    from marrow.search import PostgresSearchBackend

    ws, _, col = _seed_workspace(db)
    _create_page(db, col, "getting-started", "Getting Started Guide", "Welcome to Freehold.")
    _create_page(db, col, "unrelated", "API Reference", "Lists all endpoints.")

    backend = PostgresSearchBackend()
    results = backend.search(ws.id, "getting", db, limit=20)

    titles = [r.title for r in results]
    assert "Getting Started Guide" in titles
    # The title match should rank first
    assert titles[0] == "Getting Started Guide"
