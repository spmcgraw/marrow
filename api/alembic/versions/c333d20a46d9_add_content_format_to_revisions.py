"""add_content_format_to_revisions

Revision ID: c333d20a46d9
Revises: 0999ffe7b838
Create Date: 2026-04-11 23:04:29.642488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c333d20a46d9'
down_revision: Union[str, Sequence[str], None] = '0999ffe7b838'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add content_format column to revisions table.

    New revisions store BlockNote JSON; existing rows default to 'markdown'
    to maintain backward compatibility.
    """
    op.add_column(
        'revisions',
        sa.Column('content_format', sa.Text(), nullable=False, server_default='markdown'),
    )


def downgrade() -> None:
    """Remove content_format column from revisions table."""
    op.drop_column('revisions', 'content_format')
