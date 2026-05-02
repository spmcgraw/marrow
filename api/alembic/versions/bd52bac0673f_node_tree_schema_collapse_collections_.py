"""node tree schema (collapse collections+pages)

Revision ID: bd52bac0673f
Revises: c333d20a46d9
Create Date: 2026-05-01 21:46:11.777598

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd52bac0673f"
down_revision: Union[str, Sequence[str], None] = "c333d20a46d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "nodes",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "space_id", sa.UUID(), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "parent_id", sa.UUID(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("position", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_revision_id", sa.UUID(), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("type IN ('folder', 'page')", name="nodes_type_valid"),
        sa.CheckConstraint(
            "(type = 'folder' AND current_revision_id IS NULL AND search_vector IS NULL)"
            " OR (type = 'page' AND description IS NULL)",
            name="nodes_shape_by_type",
        ),
    )

    # Partial unique indexes: NULLs in regular UNIQUE are treated as distinct,
    # so we need two indexes — one for space-root nodes, one for nested nodes.
    op.create_index(
        "uq_nodes_root_slug",
        "nodes",
        ["space_id", "slug"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_nodes_child_slug",
        "nodes",
        ["parent_id", "slug"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL AND deleted_at IS NULL"),
    )

    op.execute(
        "DO $$ BEGIN"
        " IF (SELECT count(*) FROM pages) > 0"
        " OR (SELECT count(*) FROM collections) > 0"
        " THEN RAISE EXCEPTION 'refusing to run: legacy pages/collections data present';"
        " END IF;"
        " END $$;"
    )

    op.drop_constraint("revisions_page_id_fkey", "revisions", type_="foreignkey")
    op.drop_constraint("attachments_page_id_fkey", "attachments", type_="foreignkey")
    op.alter_column("revisions", "page_id", new_column_name="node_id")
    op.alter_column("attachments", "page_id", new_column_name="node_id")
    op.create_foreign_key(
        "revisions_node_id_fkey", "revisions", "nodes", ["node_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "attachments_node_id_fkey", "attachments", "nodes", ["node_id"], ["id"], ondelete="CASCADE"
    )

    op.execute(
        "ALTER TABLE nodes ADD CONSTRAINT fk_nodes_current_revision "
        "FOREIGN KEY (current_revision_id) REFERENCES revisions(id) DEFERRABLE INITIALLY DEFERRED"
    )

    op.execute(
        "CREATE FUNCTION node_is_page(uuid) RETURNS bool LANGUAGE sql STABLE AS "
        "$$ SELECT type = 'page' FROM nodes WHERE id = $1 $$"
    )
    op.execute(
        "ALTER TABLE revisions ADD CONSTRAINT revisions_node_is_page CHECK (node_is_page(node_id))"
    )

    # Drop the v0.1 FTS triggers/functions that reference the soon-to-be-dropped
    # pages table. The trigger on `revisions` would fire on every revision insert
    # going forward and crash. Node-level FTS is reintroduced in #125 (2.0c).
    op.execute("DROP TRIGGER IF EXISTS trg_page_title_update_search_vector ON pages")
    op.execute("DROP TRIGGER IF EXISTS trg_revision_update_search_vector ON revisions")
    op.execute("DROP FUNCTION IF EXISTS update_page_search_vector_on_title_change()")
    op.execute("DROP FUNCTION IF EXISTS update_page_search_vector()")

    op.drop_table("pages")
    op.drop_table("collections")


def downgrade() -> None:
    raise NotImplementedError(
        "v0.2 schema is a one-way migration; restore from a v0.1 backup instead"
    )
