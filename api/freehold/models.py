"""SQLAlchemy 2.0 ORM models for the Freehold core schema.

These models mirror the Alembic migration exactly, including:
- Server-side UUID primary keys (gen_random_uuid())
- Server-side timestamps (now())
- Deferred FK: pages.current_revision_id → revisions.id
- attachments.hash NOT NULL
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    spaces: Mapped[list["Space"]] = relationship(back_populates="workspace")


class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug"),
        ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="spaces")
    collections: Mapped[list["Collection"]] = relationship(back_populates="space")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("space_id", "slug"),
        ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
    )

    space: Mapped["Space"] = relationship(back_populates="collections")
    pages: Mapped[list["Page"]] = relationship(back_populates="collection")


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Nullable until a revision exists; deferred FK defined in __table_args__
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Managed by database triggers — never set from application code.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("collection_id", "slug"),
        ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        # Deferred so a page and its first revision can be inserted in the same
        # transaction without ordering constraints.
        ForeignKeyConstraint(
            ["current_revision_id"],
            ["revisions.id"],
            name="fk_pages_current_revision",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    collection: Mapped["Collection"] = relationship(back_populates="pages")
    current_revision: Mapped["Revision | None"] = relationship(
        foreign_keys="[Page.current_revision_id]"
    )
    revisions: Mapped[list["Revision"]] = relationship(
        back_populates="page",
        foreign_keys="[Revision.page_id]",
        order_by="Revision.created_at",
    )
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="page")


class Revision(Base):
    __tablename__ = "revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),)

    page: Mapped["Page"] = relationship(
        back_populates="revisions", foreign_keys="[Revision.page_id]"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),)

    page: Mapped["Page"] = relationship(back_populates="attachments")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    oidc_issuer: Mapped[str] = mapped_column(Text, nullable=False)
    oidc_subject: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("oidc_issuer", "oidc_subject"),)
