# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Keep this file up to date.** Whenever a meaningful change is made — new routes, schema changes, new components, new environment variables, new constraints, or architectural decisions — update the relevant section here before closing out the task. Treat CLAUDE.md as living documentation.

**For every feature request:** create a GitHub issue to track it, then create a dedicated git branch off `main` before writing any code. Branch names should follow the pattern `feature/<short-description>` or `fix/<short-description>`. Never implement features directly on `main`.

---

## Project Overview

Freehold is a self-hosted, open-source knowledge base (wiki) built around a non-negotiable **restore guarantee**: a Freehold export bundle must always be restorable to an exact replica of the original workspace. This guarantee is the architectural foundation — every decision flows from it.

Current status: **v0.1 MVP** — core hierarchy, append-only revisions, export/restore, file attachments, and a working Next.js frontend are all implemented and tested.

---

## Tech Stack

- **Backend**: FastAPI (Python 3.11+), located in `api/`
- **Database**: PostgreSQL 16 (docker-compose maps to port 5433)
- **Migrations**: Alembic
- **Search**: PostgreSQL full-text search planned for v0.1; Meilisearch/OpenSearch later
- **Frontend**: Next.js 16 (React 19), located in `web/`
- **Storage**: Pluggable adapter interface — local filesystem is the only current implementation
- **CLI**: Typer (`freehold export` / `freehold restore`)

---

## Development Setup

```bash
# Start PostgreSQL
docker compose up -d

# Backend
cd api
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"           # installs from pyproject.toml including dev deps
cp .env.example .env              # configure DB connection, storage, API key, CORS
alembic upgrade head              # run migrations
uvicorn main:app --reload         # starts on http://localhost:8000

# Frontend
cd web
npm install
cp .env.local.example .env.local  # set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_API_KEY
npm run dev                       # starts on http://localhost:3000
```

### Environment Variables

**Backend (`api/.env`)**:

```env
DATABASE_URL=postgresql://freehold:freehold@localhost:5433/freehold
SECRET_KEY=changeme
STORAGE_PATH=./storage       # resolves relative to api/ directory
API_KEY=                     # optional; if set, enforces X-API-Key header on all routes
CORS_ORIGINS=http://localhost:3000
```

**Frontend (`web/.env.local`)**:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=         # must match API_KEY in backend .env if set
```

---

## Common Commands

```bash
# Backend tests (integration — require a running database)
cd api && pytest
cd api && pytest tests/path/to/test_file.py::test_function

# Backend linting/formatting
cd api && ruff check .
cd api && ruff format .

# Database migrations
cd api && alembic revision --autogenerate -m "description"
cd api && alembic upgrade head
cd api && alembic downgrade -1

# CLI (export/restore)
cd api && freehold export --workspace <slug> --output <path>
cd api && freehold restore <bundle.zip>

# Frontend
cd web && npm run dev
cd web && npm run build
cd web && npm run lint
cd web && npm test
```

---

## Repository Layout

```text
freehold/
├── api/                              # FastAPI backend
│   ├── main.py                       # Entry point (re-exports app from freehold.app)
│   ├── pyproject.toml                # Dependencies and CLI entry point
│   ├── alembic.ini
│   ├── .env.example
│   ├── alembic/
│   │   └── versions/
│   │       ├── 69d839126d73_create_core_schema.py
│   │       └── d3981f696939_add_full_text_search.py
│   ├── freehold/                     # Main package
│   │   ├── app.py                    # FastAPI app factory, CORS middleware
│   │   ├── db.py                     # SQLAlchemy session management
│   │   ├── dependencies.py           # FastAPI dependency providers (api key, db session, search)
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── search.py                 # SearchBackend ABC + PostgresSearchBackend
│   │   ├── storage.py                # StorageAdapter ABC + LocalFilesystemAdapter
│   │   ├── export.py                 # Export workspace → zip bundle
│   │   ├── restore.py                # Restore workspace ← zip bundle
│   │   ├── cli.py                    # Typer CLI (export, restore commands)
│   │   └── routers/
│   │       ├── workspaces.py
│   │       ├── spaces.py
│   │       ├── collections.py
│   │       ├── pages.py              # Scoped page routes (under collection)
│   │       └── pages_global.py       # Global page routes (UUID-scoped, no collection_id)
│   ├── tests/
│   │   ├── test_models_smoke.py
│   │   ├── test_migration_cycle.py
│   │   ├── test_export.py
│   │   ├── test_restore.py
│   │   ├── test_round_trip.py        # Critical regression anchor
│   │   └── test_search.py           # FTS trigger + search scoping tests
│   └── storage/                      # Default local attachment storage (gitignored)
│
├── web/                              # Next.js frontend
│   ├── app/
│   │   ├── page.tsx                  # Root → redirects to /workspaces
│   │   ├── layout.tsx                # Root layout with theme provider
│   │   ├── workspaces/page.tsx       # Workspace list + creation
│   │   └── w/[workspaceId]/
│   │       ├── layout.tsx            # Workspace shell with sidebar
│   │       ├── page.tsx              # Redirects to first space or empty state
│   │       └── pages/[pageId]/
│   │           └── page.tsx          # Page editor
│   ├── components/
│   │   ├── app-sidebar.tsx           # Tree nav: Spaces → Collections → Pages + search
│   │   ├── search-dialog.tsx         # Cmd+K search dialog
│   │   ├── page-editor.tsx           # Title + markdown textarea, auto-save, attachments, revisions
│   │   └── ui/                       # Shadcn/Base UI components
│   ├── lib/
│   │   ├── api.ts                    # apiFetch helper + all API client functions
│   │   ├── types.ts                  # TypeScript interfaces mirroring API schemas
│   │   └── utils.ts
│   └── hooks/
│
├── docker-compose.yml                # PostgreSQL 16 (port 5433)
├── CLAUDE.md                         # This file
├── README.md
└── LICENSE                           # Apache 2.0
```

---

## Architecture

### Data Model

```text
workspaces → spaces → collections → pages → blocks (future)
                                          → attachments
                                 → revisions  (append-only, every save)
                       audit_events (future)
                       tasks / task_integrations (future)
```

**Tables** (all use UUIDs, timezone-aware timestamps):

| Table | Key columns |
| --- | --- |
| workspaces | id, slug (unique), name |
| spaces | id, workspace_id (FK cascade), slug (unique per workspace), name |
| collections | id, space_id (FK cascade), slug (unique per space), name |
| pages | id, collection_id (FK cascade), slug (unique per collection), title, current_revision_id (deferred FK), search_vector (tsvector, GIN-indexed, trigger-managed) |
| revisions | id, page_id (FK cascade), content (TEXT) — **immutable via PG trigger** |
| attachments | id, page_id (FK cascade), filename, hash (SHA256), size_bytes |

**Revision immutability**: A PL/pgSQL trigger (`revisions_immutable()`) raises an exception on any `UPDATE` or `DELETE` against the `revisions` table. This enforces the constraint at the database level, not just the application level.

**Deferred FK**: `pages.current_revision_id → revisions.id` is a deferred constraint, allowing page and first revision to be created in a single transaction.

### API Routes Summary

All routes are prefixed with `/api`. Authentication is enforced via `X-API-Key` header when `API_KEY` env var is set.

| Method | Path | Description |
| --- | --- | --- |
| GET | /health | Health check |
| GET/POST | /api/workspaces/ | List / create workspaces |
| GET/DELETE | /api/workspaces/{id} | Get / delete workspace |
| GET | /api/workspaces/{id}/tree | Full hierarchy (sidebar) |
| GET | /api/workspaces/{id}/search?q= | Full-text search across workspace pages |
| GET/POST | /api/workspaces/{id}/spaces/ | List / create spaces |
| GET/DELETE | /api/workspaces/{id}/spaces/{sid} | Get / delete space |
| GET/POST | /api/spaces/{sid}/collections/ | List / create collections |
| GET/DELETE | /api/spaces/{sid}/collections/{cid} | Get / delete collection |
| GET/POST | /api/collections/{cid}/pages/ | List / create pages |
| GET/PATCH/DELETE | /api/collections/{cid}/pages/{pid} | Get / update / delete page |
| GET | /api/collections/{cid}/pages/{pid}/revisions | List revisions |
| GET | /api/collections/{cid}/pages/{pid}/revisions/{rid} | Single revision |
| GET/POST | /api/collections/{cid}/pages/{pid}/attachments | List / upload attachments |
| GET | /api/collections/{cid}/pages/{pid}/attachments/{aid}/file | Download attachment |
| GET/PATCH | /api/pages/{pid} | Global page get / update (no collection_id needed) |
| GET | /api/pages/{pid}/revisions | Global revision list |
| GET | /api/pages/{pid}/revisions/{rid} | Global single revision |

### Storage Adapter Interface

```python
class StorageAdapter(ABC):
    def read(self, attachment_id: str, filename: str) -> bytes: ...
    def write(self, attachment_id: str, filename: str, data: bytes) -> None: ...
```

`LocalFilesystemAdapter` stores files at `{STORAGE_PATH}/{attachment_id}/{filename}`. New backends implement this interface without touching any other code.

### Export Bundle Format

```
freehold-export-{workspace-slug}-{timestamp}.zip
├── manifest.json        # workspace metadata, all entity IDs, schema version
├── pages/
│   └── {page-id}.md     # current content of each page
├── revisions/
│   └── {page-id}/
│       └── {revision-id}.md
├── assets/
│   └── {attachment-id}{ext}
└── links.json           # internal links, broken links, orphaned pages
```

### Frontend Patterns

- **API client** (`lib/api.ts`): all server calls go through `apiFetch<T>()` which injects auth headers and handles errors
- **Auto-save**: `PageEditor` debounces saves 2 seconds after last keystroke; shows Saving… / Saved / Error status
- **Sidebar create flows**: hover-to-reveal `+` buttons open `CreateDialog` with slug auto-generation via `slugify()`
- **UI library**: Base UI (`@base-ui/react`) with Tailwind CSS 4 — uses `render` prop pattern, not `asChild`
- **Theme**: `next-themes` wraps the root layout

---

## Core Constraints

These constraints are non-negotiable and must be respected in all contributions:

1. **Restore guarantee**: `freehold restore <bundle.zip>` must reproduce a workspace exactly from any valid export bundle. A failing restore test is a critical bug.
2. **Append-only revisions**: saves always create new revisions; existing revisions are never modified or deleted. The database trigger enforces this — do not remove it.
3. **Transparent export format**: export bundles must remain human-readable without tooling (Markdown + JSON, no proprietary blobs).
4. **Pluggable storage**: business logic must not bypass the storage adapter interface. Never call filesystem APIs directly from routers or models.

---

## Test Strategy

Tests in `api/tests/` are **integration tests** — they hit a real database. A fresh test database is created per run and dropped after.

- `test_round_trip.py` is the critical regression anchor: it does a full create → export → wipe → restore → verify cycle. This test must pass at all times.
- `FakeStorageAdapter` (in-memory) is used in tests so no filesystem is needed.
- Run `pytest` from `api/` with the venv active and a running PostgreSQL instance.

---

## What's Not Built Yet

- Meilisearch upgrade for fuzzy/typo-tolerant search (PostgreSQL FTS is implemented)
- S3-compatible storage adapter
- Rich text / TipTap editor (currently plain Markdown textarea)
- User authentication and permissions (API key is the only auth layer)
- Audit log / audit_events table
- Task management and integrations
- Deployment docs (Docker image, K8s, systemd)
- Page templates, collaborative editing, offline sync
