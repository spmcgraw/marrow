"""add organizations and rbac

Revision ID: 0999ffe7b838
Revises: 35eb203afc65
Create Date: 2026-04-05

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0999ffe7b838"
down_revision: Union[str, Sequence[str], None] = "35eb203afc65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add organizations, org_memberships tables and workspaces.org_id FK."""

    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # --- org_memberships ---
    op.create_table(
        "org_memberships",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),  # NULL = pending invite
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "role IN ('owner', 'editor', 'viewer')", name="ck_org_memberships_role"
        ),
    )

    # Partial unique indexes: one active membership per user per org,
    # one pending invite per email per org.
    op.execute(
        "CREATE UNIQUE INDEX uq_org_memberships_org_user "
        "ON org_memberships (org_id, user_id) WHERE user_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_org_memberships_org_email_pending "
        "ON org_memberships (org_id, email) WHERE user_id IS NULL"
    )

    # --- workspaces.org_id (nullable first, then backfill, then NOT NULL) ---
    op.add_column("workspaces", sa.Column("org_id", sa.UUID(), nullable=True))

    # Backfill: create a default org and assign all existing workspaces to it.
    # Also make all existing users owners of the default org.
    op.execute(
        """
        DO $$
        DECLARE
            default_org_id UUID;
        BEGIN
            -- Only backfill if there are existing workspaces
            IF EXISTS (SELECT 1 FROM workspaces LIMIT 1) THEN
                INSERT INTO organizations (slug, name)
                VALUES ('default', 'Default Organization')
                RETURNING id INTO default_org_id;

                UPDATE workspaces SET org_id = default_org_id WHERE org_id IS NULL;

                -- Make all existing users owners of the default org
                INSERT INTO org_memberships (org_id, user_id, email, role)
                SELECT default_org_id, u.id, u.email, 'owner'
                FROM users u;
            END IF;
        END $$;
        """
    )

    # Drop the revisions_no_delete trigger — it blocks FK CASCADE deletes
    # from parent tables (workspace/page deletion). The UPDATE trigger still
    # enforces append-only semantics for revision content.
    op.execute("DROP TRIGGER IF EXISTS revisions_no_delete ON revisions")

    op.alter_column("workspaces", "org_id", nullable=False)
    op.create_foreign_key(
        "fk_workspaces_org_id",
        "workspaces",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Remove organizations, org_memberships, and workspaces.org_id."""
    # Restore the revisions delete trigger
    op.execute(
        "CREATE TRIGGER revisions_no_delete "
        "BEFORE DELETE ON revisions "
        "FOR EACH ROW EXECUTE FUNCTION revisions_immutable()"
    )
    op.drop_constraint("fk_workspaces_org_id", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "org_id")
    op.drop_table("org_memberships")
    op.drop_table("organizations")
