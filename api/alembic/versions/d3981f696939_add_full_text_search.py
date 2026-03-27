"""add full text search

Revision ID: d3981f696939
Revises: 69d839126d73
Create Date: 2026-03-26 22:15:52.030262

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd3981f696939'
down_revision: Union[str, Sequence[str], None] = '69d839126d73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add tsvector column
    op.add_column("pages", sa.Column("search_vector", TSVECTOR, nullable=True))

    # 2. GIN index for fast full-text lookups
    op.create_index(
        "ix_pages_search_vector",
        "pages",
        ["search_vector"],
        postgresql_using="gin",
    )

    # 3. Trigger: update search_vector when a new revision is inserted
    op.execute("""
        CREATE OR REPLACE FUNCTION update_page_search_vector()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            UPDATE pages
            SET search_vector =
                setweight(to_tsvector('english', COALESCE(pages.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B')
            WHERE pages.id = NEW.page_id;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_revision_update_search_vector
        AFTER INSERT ON revisions
        FOR EACH ROW EXECUTE FUNCTION update_page_search_vector();
    """)

    # 4. Trigger: update search_vector when a page title changes
    op.execute("""
        CREATE OR REPLACE FUNCTION update_page_search_vector_on_title_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.title IS DISTINCT FROM OLD.title THEN
                NEW.search_vector :=
                    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(
                        (SELECT content FROM revisions WHERE id = NEW.current_revision_id), ''
                    )), 'B');
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_page_title_update_search_vector
        BEFORE UPDATE OF title ON pages
        FOR EACH ROW EXECUTE FUNCTION update_page_search_vector_on_title_change();
    """)

    # 5. Backfill existing pages
    op.execute("""
        UPDATE pages
        SET search_vector =
            setweight(to_tsvector('english', COALESCE(pages.title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(
                (SELECT content FROM revisions WHERE id = pages.current_revision_id), ''
            )), 'B')
        WHERE pages.current_revision_id IS NOT NULL;
    """)
    op.execute("""
        UPDATE pages
        SET search_vector = setweight(to_tsvector('english', COALESCE(pages.title, '')), 'A')
        WHERE current_revision_id IS NULL;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_page_title_update_search_vector ON pages")
    op.execute("DROP FUNCTION IF EXISTS update_page_search_vector_on_title_change()")
    op.execute("DROP TRIGGER IF EXISTS trg_revision_update_search_vector ON revisions")
    op.execute("DROP FUNCTION IF EXISTS update_page_search_vector()")
    op.drop_index("ix_pages_search_vector", table_name="pages")
    op.drop_column("pages", "search_vector")
