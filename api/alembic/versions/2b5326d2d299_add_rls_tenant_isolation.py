"""add_rls_tenant_isolation

Revision ID: 2b5326d2d299
Revises: bd52bac0673f
Create Date: 2026-05-02 13:42:46.092348

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "2b5326d2d299"
down_revision: str | None = "bd52bac0673f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UNSET = (
    "current_setting('app.current_org', true) IS NULL"
    " OR current_setting('app.current_org', true) = ''"
)
_VIA_ORG = "id = current_setting('app.current_org', true)::uuid"
_VIA_WORKSPACE = "org_id = current_setting('app.current_org', true)::uuid"
_VIA_SPACE = (
    "workspace_id IN ("
    "SELECT id FROM workspaces"
    f" WHERE {_VIA_WORKSPACE})"
)
_VIA_NODE = (
    "space_id IN ("
    "SELECT s.id FROM spaces s"
    " JOIN workspaces w ON w.id = s.workspace_id"
    f" WHERE {_VIA_WORKSPACE})"
)
_VIA_NODE_INDIRECT = (
    "node_id IN ("
    "SELECT n.id FROM nodes n"
    " JOIN spaces s ON s.id = n.space_id"
    " JOIN workspaces w ON w.id = s.workspace_id"
    f" WHERE {_VIA_WORKSPACE})"
)


def _enable_rls(table: str, tenant_expr: str) -> None:
    op.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    op.execute(
        text(
            f"CREATE POLICY tenant_isolation ON {table}"
            f" USING ({_UNSET} OR {tenant_expr})"
        )
    )


def upgrade() -> None:
    _enable_rls("organizations", _VIA_ORG)
    _enable_rls("org_memberships", _VIA_WORKSPACE)
    _enable_rls("workspaces", _VIA_WORKSPACE)
    _enable_rls("spaces", _VIA_SPACE)
    _enable_rls("nodes", _VIA_NODE)
    _enable_rls("revisions", _VIA_NODE_INDIRECT)
    _enable_rls("attachments", _VIA_NODE_INDIRECT)


def downgrade() -> None:
    for table in [
        "attachments",
        "revisions",
        "nodes",
        "spaces",
        "workspaces",
        "org_memberships",
        "organizations",
    ]:
        op.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        op.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
