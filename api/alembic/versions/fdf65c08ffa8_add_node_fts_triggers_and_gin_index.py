"""add node FTS triggers and GIN index

Revision ID: fdf65c08ffa8
Revises: bd52bac0673f
Create Date: 2026-05-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "fdf65c08ffa8"
down_revision: Union[str, Sequence[str], None] = "2b5326d2d299"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # GIN index on search_vector, limited to live page nodes.
    op.execute(
        "CREATE INDEX idx_nodes_search ON nodes USING gin(search_vector)"
        " WHERE type = 'page' AND deleted_at IS NULL"
    )

    # Fires AFTER INSERT on revisions — updates parent node's search_vector.
    # Weighted: name → A (title-match ranks higher), content → B.
    op.execute("""
        CREATE OR REPLACE FUNCTION update_node_search_vector()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            UPDATE nodes
            SET search_vector =
                setweight(to_tsvector('english', COALESCE(nodes.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B')
            WHERE id = NEW.node_id
              AND type = 'page';
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_revision_update_node_search_vector
        AFTER INSERT ON revisions
        FOR EACH ROW EXECUTE FUNCTION update_node_search_vector();
    """)

    # Fires BEFORE UPDATE OF name, slug on nodes — refreshes search_vector when
    # a page's display name or slug changes without a new revision being inserted.
    op.execute("""
        CREATE OR REPLACE FUNCTION update_node_search_vector_on_name_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.type = 'page' THEN
                NEW.search_vector :=
                    setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(
                        (SELECT content FROM revisions WHERE id = NEW.current_revision_id),
                        ''
                    )), 'B');
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_node_name_update_search_vector
        BEFORE UPDATE OF name, slug ON nodes
        FOR EACH ROW EXECUTE FUNCTION update_node_search_vector_on_name_change();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_node_name_update_search_vector ON nodes")
    op.execute("DROP FUNCTION IF EXISTS update_node_search_vector_on_name_change()")
    op.execute("DROP TRIGGER IF EXISTS trg_revision_update_node_search_vector ON revisions")
    op.execute("DROP FUNCTION IF EXISTS update_node_search_vector()")
    op.execute("DROP INDEX IF EXISTS idx_nodes_search")
