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
- **Auth**: OIDC authentication (any IdP) with API key fallback — see `api/freehold/auth.py`
- **Search**: PostgreSQL full-text search; Meilisearch/OpenSearch later
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

# OIDC Authentication (optional — omit OIDC_ISSUER to disable)
# OIDC_ISSUER=https://accounts.google.com
# OIDC_CLIENT_ID=
# OIDC_CLIENT_SECRET=
# OIDC_REDIRECT_URI=http://localhost:8000/api/auth/callback
# FRONTEND_URL=http://localhost:3000
# COOKIE_DOMAIN=localhost    # shared domain for session cookie (dev: localhost)
```

**Frontend (`web/.env.local`)**:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=         # must match API_KEY in backend .env if set
NEXT_PUBLIC_OIDC_ENABLED=    # set to "true" when OIDC is configured on the backend
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
│   │       ├── d3981f696939_add_full_text_search.py
│   │       ├── 35eb203afc65_add_users_table.py
│   │       ├── 0999ffe7b838_add_organizations_and_rbac.py
│   │       └── c333d20a46d9_add_content_format_to_revisions.py
│   ├── freehold/                     # Main package
│   │   ├── app.py                    # FastAPI app factory, CORS + session middleware
│   │   ├── auth.py                   # OIDC config, session JWT helpers, cookie params
│   │   ├── db.py                     # SQLAlchemy session management
│   │   ├── dependencies.py           # FastAPI dependency providers (auth, db session, search)
│   │   ├── rbac.py                   # Role-based access control dependency factories
│   │   ├── models.py                 # SQLAlchemy ORM models (incl. User)
│   │   ├── schemas.py                # Pydantic request/response schemas (incl. AuthStatus)
│   │   ├── search.py                 # SearchBackend ABC + PostgresSearchBackend
│   │   ├── storage.py                # StorageAdapter ABC + LocalFilesystemAdapter
│   │   ├── export.py                 # Export workspace → zip bundle
│   │   ├── restore.py                # Restore workspace ← zip bundle
│   │   ├── cli.py                    # Typer CLI (export, restore commands)
│   │   └── routers/
│   │       ├── auth.py               # OIDC login/callback/me/logout + personal org creation
│   │       ├── organizations.py      # Org CRUD, member management (invite, role, remove)
│   │       ├── workspaces.py
│   │       ├── spaces.py
│   │       ├── collections.py
│   │       ├── pages.py              # Scoped page routes (under collection)
│   │       └── pages_global.py       # Global page routes (UUID-scoped, no collection_id)
│   ├── tests/
│   │   ├── test_models_smoke.py
│   │   ├── test_migration_cycle.py
│   │   ├── test_auth.py              # Auth dependency, JWT, and auth router tests
│   │   ├── test_rbac.py              # Role enforcement matrix (owner/editor/viewer × CRUD)
│   │   ├── test_export.py
│   │   ├── test_restore.py
│   │   ├── test_round_trip.py        # Critical regression anchor
│   │   └── test_search.py            # FTS trigger + search scoping tests
│   └── storage/                      # Default local attachment storage (gitignored)
│
├── web/                              # Next.js frontend
│   ├── proxy.ts                      # Route protection (redirects to /login when OIDC enabled)
│   ├── app/
│   │   ├── page.tsx                  # Root → redirects to /workspaces
│   │   ├── layout.tsx                # Root layout with theme provider
│   │   ├── login/page.tsx            # SSO login page (shown when OIDC enabled)
│   │   ├── auth/callback/page.tsx    # Post-OIDC callback landing page
│   │   ├── orgs/[orgId]/settings/page.tsx  # Org member management UI
│   │   ├── workspaces/page.tsx       # Workspace list + creation
│   │   └── w/[workspaceId]/
│   │       ├── layout.tsx            # Workspace shell with sidebar + auth status
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
organizations → org_memberships (user roles: owner/editor/viewer)
             → workspaces → spaces → collections → pages → blocks (future)
                                                         → attachments
                                                → revisions  (append-only, every save)
                              audit_events (future)
                              tasks / task_integrations (future)
```

**Tables** (all use UUIDs, timezone-aware timestamps):

| Table | Key columns |
| --- | --- |
| organizations | id, slug (unique), name |
| org_memberships | id, org_id (FK), user_id (FK, nullable for pending), email, role (owner/editor/viewer) |
| workspaces | id, org_id (FK), slug (unique), name |
| spaces | id, workspace_id (FK cascade), slug (unique per workspace), name |
| collections | id, space_id (FK cascade), slug (unique per space), name |
| pages | id, collection_id (FK cascade), slug (unique per collection), title, current_revision_id (deferred FK), search_vector (tsvector, GIN-indexed, trigger-managed) |
| revisions | id, page_id (FK cascade), content (TEXT), content_format (TEXT: 'markdown'\|'json') — **immutable via PG trigger** |
| attachments | id, page_id (FK cascade), filename, hash (SHA256), size_bytes |
| users | id, oidc_issuer, oidc_subject (unique together), email, name, last_login_at |

**Revision immutability**: A PL/pgSQL trigger (`revisions_immutable()`) raises an exception on any `UPDATE` against the `revisions` table. This enforces the append-only constraint at the database level. `DELETE` is allowed via FK CASCADE (e.g., when a page or workspace is deleted).

**Deferred FK**: `pages.current_revision_id → revisions.id` is a deferred constraint, allowing page and first revision to be created in a single transaction.

### API Routes Summary

All routes are prefixed with `/api`. Authentication is enforced via session cookie (OIDC), `X-API-Key` header, or anonymous access (when neither is configured). Auth routes are unauthenticated.

| Method | Path | Description | Min Role |
| --- | --- | --- | --- |
| GET | /health | Health check | — |
| GET | /api/auth/login | Redirect to OIDC provider | — |
| GET | /api/auth/callback | OIDC callback — exchanges code, sets session cookie, claims pending memberships | — |
| GET | /api/auth/me | Current auth status and user info | — |
| POST | /api/auth/logout | Clear session cookie | — |
| GET/POST | /api/orgs | List user's orgs / create org | session |
| GET | /api/orgs/{oid} | Get org details | viewer |
| GET | /api/orgs/{oid}/members | List members (incl. pending) | viewer |
| POST | /api/orgs/{oid}/members | Invite member by email | owner |
| PATCH | /api/orgs/{oid}/members/{mid} | Change member role | owner |
| DELETE | /api/orgs/{oid}/members/{mid} | Remove member | owner |
| GET/POST | /api/workspaces/ | List / create workspaces | viewer/editor |
| GET/DELETE | /api/workspaces/{id} | Get / delete workspace | viewer/owner |
| GET | /api/workspaces/{id}/tree | Full hierarchy (sidebar) | viewer |
| GET | /api/workspaces/{id}/search?q= | Full-text search across workspace pages | viewer |
| GET/POST | /api/workspaces/{id}/spaces/ | List / create spaces | viewer/editor |
| GET/DELETE | /api/workspaces/{id}/spaces/{sid} | Get / delete space | viewer/owner |
| GET/POST | /api/spaces/{sid}/collections/ | List / create collections | viewer/editor |
| GET/DELETE | /api/spaces/{sid}/collections/{cid} | Get / delete collection | viewer/owner |
| GET/POST | /api/collections/{cid}/pages/ | List / create pages | viewer/editor |
| GET/PATCH/DELETE | /api/collections/{cid}/pages/{pid} | Get / update / delete page | viewer/editor/owner |
| GET | /api/collections/{cid}/pages/{pid}/revisions | List revisions | viewer |
| GET | /api/collections/{cid}/pages/{pid}/revisions/{rid} | Single revision | viewer |
| GET/POST | /api/collections/{cid}/pages/{pid}/attachments | List / upload attachments | viewer/editor |
| GET | /api/collections/{cid}/pages/{pid}/attachments/{aid}/file | Download attachment | viewer |
| GET/PATCH | /api/pages/{pid} | Global page get / update (no collection_id needed) | viewer/editor |
| GET | /api/pages/{pid}/revisions | Global revision list | viewer |
| GET | /api/pages/{pid}/revisions/{rid} | Global single revision | viewer |

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
├── manifest.json        # workspace + org metadata, all entity IDs, schema version (v3)
├── pages/
│   ├── {page-id}.md     # human-readable Markdown (all pages)
│   └── {page-id}.json   # canonical BlockNote JSON (JSON-format pages only)
├── revisions/
│   └── {page-id}/
│       ├── {revision-id}.md     # Markdown revisions (legacy) or human-readable export
│       └── {revision-id}.json   # BlockNote JSON revisions (canonical)
├── assets/
│   └── {attachment-id}{ext}
└── links.json           # internal links, broken links, orphaned pages
```

v1/v2 bundles had only `.md` files. v3 adds `.json` as canonical for JSON-format revisions.
Restore supports v1, v2, and v3 bundles.

### Authentication

Freehold supports three authentication methods, checked in priority order:

1. **OIDC session cookie** (`freehold_session`): A JWT signed with `SECRET_KEY` (HS256), issued after successful OIDC login. Contains `sub` (user UUID), `email`, `name`, with 24h expiry.
2. **API key** (`X-API-Key` header): Static key matching `API_KEY` env var. Used by CLI and scripts. **Bypasses all RBAC checks** (superuser equivalent).
3. **Anonymous**: When neither OIDC nor API key is configured, all requests are allowed (dev mode). **Bypasses all RBAC checks**.

**OIDC flow**: The backend is the OIDC Relying Party. `GET /api/auth/login` redirects to the IdP. `GET /api/auth/callback` exchanges the code, upserts the user in the `users` table, claims any pending org memberships matching the user's email, auto-creates a personal org if the user has no memberships, and sets an httpOnly session cookie. The `COOKIE_DOMAIN` env var controls the cookie domain (set to `localhost` for dev so the cookie is shared between `:3000` and `:8000`).

**RBAC**: Org membership with roles (owner/editor/viewer) enforced on all data routes. Role is resolved by following the resource chain (page → collection → space → workspace → org → membership). Dependency factories in `rbac.py` handle resolution for each resource level.

**Key files**: `auth.py` (config, JWT helpers), `dependencies.py` (`verify_auth` + `AuthContext`), `rbac.py` (role enforcement dependencies), `routers/auth.py` (login/callback/me/logout), `routers/organizations.py` (org CRUD + member management).

### Frontend Patterns

- **API client** (`lib/api.ts`): all server calls go through `apiFetch<T>()` which injects auth headers and handles errors
- **Auto-save**: `PageEditor` debounces saves 2 seconds after last keystroke; shows Saving… / Saved / Error status
- **Content format**: new saves store BlockNote JSON (`content_format='json'`); legacy Markdown revisions are loaded via `tryParseMarkdownToBlocks` for backward compat
- **Editor features**: code blocks (Shiki syntax highlighting), tables (`TableHandlesController`), `@` page mentions (`SuggestionMenuController` → `searchWorkspace`)
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
- User permissions and workspace-level access control (OIDC auth is implemented but no per-user data scoping)
- Audit log / audit_events table
- Task management and integrations
- Deployment docs (Docker image, K8s, systemd)
- Page templates, collaborative editing, offline sync
