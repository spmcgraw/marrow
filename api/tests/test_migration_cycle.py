"""
Integration tests for the core schema migration upgrade/downgrade cycle.

Requires a running PostgreSQL instance (Docker Compose default: localhost:5433).
Run from the api/ directory: pytest tests/test_migration_cycle.py
"""

import os
import uuid

import psycopg2
import psycopg2.errors
import pytest
from alembic.config import Config
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from alembic import command

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://marrow:marrow@localhost:5433/marrow")


def _base_dsn() -> str:
    """Strip the database name from DATABASE_URL for admin connections."""
    return DATABASE_URL.rsplit("/", 1)[0]


def _alembic_cfg(url: str) -> Config:
    # env.py reads DATABASE_URL from os.environ; point it at the test DB.
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="module")
def db_url():
    """Create a fresh database for the module, yield its URL, then drop it."""
    db_name = f"marrow_test_{uuid.uuid4().hex[:8]}"

    admin = psycopg2.connect(f"{_base_dsn()}/postgres")
    admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{db_name}"')
    admin.close()

    yield f"{_base_dsn()}/{db_name}"

    admin = psycopg2.connect(f"{_base_dsn()}/postgres")
    admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with admin.cursor() as cur:
        cur.execute(f'DROP DATABASE "{db_name}" WITH (FORCE)')
    admin.close()


def _insert_revision(db_url: str) -> str:
    """Insert the minimum rows needed to get a revision row; return its id."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO organizations (slug, name) VALUES (%s, %s) RETURNING id",
            (f"org-{uuid.uuid4().hex[:6]}", "Test Org"),
        )
        org_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO workspaces (org_id, slug, name) VALUES (%s, %s, %s) RETURNING id",
            (org_id, f"ws-{uuid.uuid4().hex[:6]}", "Test WS"),
        )
        ws_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO spaces (workspace_id, slug, name) VALUES (%s, %s, %s) RETURNING id",
            (ws_id, f"sp-{uuid.uuid4().hex[:6]}", "Test Space"),
        )
        sp_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO collections (space_id, slug, name) VALUES (%s, %s, %s) RETURNING id",
            (sp_id, f"col-{uuid.uuid4().hex[:6]}", "Test Collection"),
        )
        col_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO pages (collection_id, slug, title) VALUES (%s, %s, %s) RETURNING id",
            (col_id, f"pg-{uuid.uuid4().hex[:6]}", "Test Page"),
        )
        pg_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO revisions (page_id, content) VALUES (%s, %s) RETURNING id",
            (pg_id, "Initial content"),
        )
        rev_id = cur.fetchone()[0]

    conn.close()
    return str(rev_id)


class TestMigrationCycle:
    """Verify the upgrade/downgrade cycle for the core schema migration.

    Tests run in file order: upgrade → constraint checks → downgrade.
    """

    def test_upgrade_runs_cleanly(self, db_url):
        command.upgrade(_alembic_cfg(db_url), "head")

        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
            tables = {row[0] for row in cur.fetchall()}
        conn.close()

        expected = {
            "workspaces",
            "spaces",
            "collections",
            "pages",
            "revisions",
            "attachments",
            "users",
            "organizations",
            "org_memberships",
        }
        assert expected.issubset(tables)

    def test_revision_update_is_blocked(self, db_url):
        rev_id = _insert_revision(db_url)

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        try:
            cur.execute("UPDATE revisions SET content = 'tampered' WHERE id = %s", (rev_id,))
            pytest.fail("Expected trigger to block UPDATE on revisions")
        except psycopg2.errors.RaiseException:
            pass
        finally:
            conn.rollback()
            cur.close()
            conn.close()

    def test_downgrade_reverses_cleanly(self, db_url):
        command.downgrade(_alembic_cfg(db_url), "base")

        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
            tables = {row[0] for row in cur.fetchall()}
        conn.close()

        marrow_tables = {
            "workspaces",
            "spaces",
            "collections",
            "pages",
            "revisions",
            "attachments",
        }
        assert not marrow_tables & tables
