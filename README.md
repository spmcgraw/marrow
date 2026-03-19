# Freehold

**Your knowledge, owned outright. No landlords. No lock-in. No surprises.**

Freehold is an open-source, sovereign knowledge base for teams and individuals who are done trusting platforms with their work. It is built around one non-negotiable principle: if you have your data, you can always come back. Export, wipe, restore. Every time. No exceptions.

---

## Why Freehold exists

Most knowledge tools are built on a quiet assumption: that you'll stay. Notion, Confluence, Loop — they're designed to be sticky, which is another word for hard to leave. Your pages, your attachments, your links, your history — they live in someone else's house. You pay rent. They set the rules.

Freehold is built on the opposite assumption. You should be able to leave at any time, take everything with you, and rebuild elsewhere in minutes. That's not a feature. That's the foundation.

---

## Core principles

These are not aspirations. They are constraints that every architectural and product decision must respect.

**1. Restore guarantee**
If you have a Freehold export bundle, you can restore your entire workspace exactly as it was. Assets, pages, links, revision history, metadata. All of it. If a restore test fails, the export is broken and that is a critical bug.

**2. Transparent data format**
The export format is documented, human-readable, and boring on purpose. Markdown files, attachments, a JSON manifest, a link graph. No proprietary binary blobs. No surprises. A person with basic technical literacy should be able to read a Freehold export without any tooling.

**3. Append-only revision history**
Nothing is ever silently overwritten. Every save creates a revision. You can reconstruct the state of any page at any point in time. Data loss is not a known failure mode.

**4. Pluggable storage**
Freehold does not care where your data lives. Local disk, S3-compatible object storage, Azure Blob — the storage layer is an interface, not a hard dependency. You bring the storage. Freehold brings the structure.

**5. Self-hosted by default, cloud by choice**
Freehold can be deployed on your own infrastructure or used as a hosted service. Either way, the data ownership model does not change. The hosted version is a convenience, not a trap.

---

## What Freehold is (v0.1 MVP)

The first version does one thing well: it is a wiki that cannot lose your data.

- Pages organized in a tree: Workspaces → Spaces → Collections → Pages
- Block-based editor (Markdown blocks to start, structured blocks to follow)
- File attachments
- Full-text search
- Version history on every save
- Export: a single command produces a zip bundle containing Markdown files, assets, a `manifest.json`, and a full link graph
- Restore: a single command rehydrates a workspace from a bundle
- Storage adapter interface: local filesystem first, S3-compatible next

That's it. No task sync, no approvals workflow, no governance features. Those come later. The MVP is the foundation that earns the right to build everything else.

---

## What Freehold becomes (roadmap direction)

Freehold is designed to grow toward being the layer where knowledge and execution meet, with the same ownership philosophy running through all of it.

- **Two-way task integration**: tasks as first-class objects, synced bidirectionally with external systems (not just "create task" buttons)
- **Content lifecycle**: Draft → Reviewed → Approved → Archived, with audit trail
- **Governance-lite**: permissions, audit log, retention policies — without requiring an IT department to operate
- **Bring-your-own storage**: connect your own S3 bucket, Azure Blob, or local volume
- **Optional client-side encryption**: for sensitive spaces where even the server should not see plaintext

---

## Tech stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Search**: PostgreSQL full-text search initially, Meilisearch or OpenSearch later
- **Storage**: local filesystem abstraction with adapter interface
- **Frontend**: Next.js (React)

---

## Data model (core)

```text
workspaces
spaces
collections
pages
blocks
attachments
revisions        ← append-only, every save
audit_events
tasks            ← future
task_integrations ← future
```

The revision table is the heart of the restore guarantee. Current page state points to the latest revision. History is never deleted.

---

## Export bundle format

A Freehold export bundle is a `.zip` file with the following structure:

```text
freehold-export-{workspace-slug}-{timestamp}.zip
├── manifest.json          # workspace metadata, export timestamp, schema version
├── pages/
│   └── {page-id}.md       # page content in Markdown
├── assets/
│   └── {asset-id}.{ext}   # original attachments
├── revisions/
│   └── {page-id}/
│       └── {revision-id}.md
└── links.json             # full link graph: internal links, broken links, orphans
```

The restore guarantee means: given this bundle and a fresh Freehold installation, `freehold restore --bundle <file>` reproduces the workspace exactly. Asset hashes are verified on restore. If they do not match, the restore fails loudly.

---

## Getting started (development)

**Prerequisites:** Python 3.11+, Node.js 20+, Docker (for PostgreSQL)

### 1. Start PostgreSQL

```bash
docker compose up -d
```

This starts PostgreSQL on port 5433 using the credentials in `docker-compose.yml`.

### 2. Backend (FastAPI)

```bash
cd api

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env             # defaults work with the Docker Compose DB

# Run database migrations
alembic upgrade head

# Start the API server (http://localhost:8000)
uvicorn main:app --reload
```

The interactive API docs are at `http://localhost:8000/docs`.

### 3. Frontend (Next.js)

In a separate terminal:

```bash
cd web
npm install
cp .env.local.example .env.local # set NEXT_PUBLIC_API_URL (and API key if used)
npm run dev                      # http://localhost:3000
```

Open `http://localhost:3000` — you'll land on the workspace list. Create a workspace, then add spaces, collections, and pages from the sidebar.

### Running tests

```bash
cd api
source .venv/bin/activate
pytest                           # all tests
pytest tests/test_round_trip.py  # export/restore round-trip only
```

---

## Contributing

Freehold is open source because the philosophy demands it. A sovereign knowledge base built behind closed doors would be a contradiction.

If you want to contribute, start with the issues labeled `good first issue`. Before writing code, read the restore guarantee section above. Any contribution that compromises the export/restore round-trip will not be merged.

---

## License

Apache 2.0. Use it, fork it, deploy it, build on it. Just don't tell people their data is theirs if it isn't.

---

*Freehold: property owned outright, with no landlord, no lease, and no one who can take it back.*
