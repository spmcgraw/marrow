"""Smoke test: create the full workspace → revision hierarchy via the ORM."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from freehold.models import Collection, Organization, Page, Revision, Space, Workspace

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://freehold:freehold@localhost:5433/freehold")


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(DATABASE_URL)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
        s.rollback()


def test_create_workspace_hierarchy(session):
    org = Organization(slug="smoke-org", name="Smoke Org")
    session.add(org)
    session.flush()

    workspace = Workspace(org_id=org.id, slug="smoke-ws", name="Smoke Workspace")
    session.add(workspace)
    session.flush()

    space = Space(workspace_id=workspace.id, slug="smoke-sp", name="Smoke Space")
    session.add(space)
    session.flush()

    collection = Collection(space_id=space.id, slug="smoke-col", name="Smoke Collection")
    session.add(collection)
    session.flush()

    page = Page(collection_id=collection.id, slug="smoke-pg", title="Smoke Page")
    session.add(page)
    session.flush()

    revision = Revision(page_id=page.id, content="Hello, Freehold.")
    session.add(revision)
    session.flush()

    page.current_revision_id = revision.id
    session.flush()

    # Verify round-trip via ORM
    assert workspace.id is not None
    assert space.workspace_id == workspace.id
    assert collection.space_id == space.id
    assert page.collection_id == collection.id
    assert revision.page_id == page.id
    assert page.current_revision_id == revision.id
