"""create core schema

Revision ID: 69d839126d73
Revises:
Create Date: 2026-03-10 22:07:39.876969

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69d839126d73"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # workspaces
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # spaces
    op.create_table(
        "spaces",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("workspace_id", "slug"),
    )

    # collections
    op.create_table(
        "collections",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("space_id", sa.UUID(), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("space_id", "slug"),
    )

    # pages (current_revision_id added via deferred FK after revisions table exists)
    op.create_table(
        "pages",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("collection_id", sa.UUID(), sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("current_revision_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("collection_id", "slug"),
    )

    # revisions (append-only; trigger below enforces no UPDATE/DELETE)
    op.create_table(
        "revisions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("page_id", sa.UUID(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # attachments
    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("page_id", sa.UUID(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("hash", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Deferred FK: pages.current_revision_id → revisions.id
    # Deferred so pages and their first revision can be inserted in the same
    # transaction without ordering constraints.
    op.execute("""
        ALTER TABLE pages
        ADD CONSTRAINT fk_pages_current_revision
        FOREIGN KEY (current_revision_id)
        REFERENCES revisions (id)
        DEFERRABLE INITIALLY DEFERRED
    """)

    # Trigger function + triggers: block UPDATE and DELETE on revisions
    op.execute("""
        CREATE FUNCTION revisions_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'revisions are append-only and cannot be %ed', TG_OP;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER revisions_no_update
        BEFORE UPDATE ON revisions
        FOR EACH ROW EXECUTE FUNCTION revisions_immutable()
    """)
    op.execute("""
        CREATE TRIGGER revisions_no_delete
        BEFORE DELETE ON revisions
        FOR EACH ROW EXECUTE FUNCTION revisions_immutable()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS revisions_no_delete ON revisions")
    op.execute("DROP TRIGGER IF EXISTS revisions_no_update ON revisions")
    op.execute("DROP FUNCTION IF EXISTS revisions_immutable")

    op.execute("ALTER TABLE pages DROP CONSTRAINT IF EXISTS fk_pages_current_revision")

    op.drop_table("attachments")
    op.drop_table("revisions")
    op.drop_table("pages")
    op.drop_table("collections")
    op.drop_table("spaces")
    op.drop_table("workspaces")
