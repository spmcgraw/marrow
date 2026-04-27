# Marrow

**Your knowledge, owned outright. No landlords. No lock-in. No surprises.**

Marrow is a self-hosted, open-source knowledge base built on one non-negotiable principle: if you have your data, you can always come back. Export, wipe, restore. Every time. No exceptions.

📖 **[Read the docs](./docs/)** for installation, deployment, and configuration guides.

---

## Why Marrow exists

Most knowledge tools are built on a quiet assumption: that you'll stay. Notion, Confluence, Loop — they're designed to be sticky, which is another word for hard to leave. Your pages, your attachments, your links, your history — they live in someone else's house. You pay rent. They set the rules.

Marrow is built on the opposite assumption. You should be able to leave at any time, take everything with you, and rebuild elsewhere in minutes. That's not a feature. That's the foundation.

---

## Core principles

These are not aspirations. They are constraints that every architectural and product decision must respect.

1. **Restore guarantee** — A Marrow export bundle is restorable to an exact replica of the original workspace. A failing restore test is a critical bug.
2. **Transparent format** — Markdown, JSON, attachments in a zip. No proprietary blobs.
3. **Append-only history** — Every save creates a revision. Old revisions are never modified or deleted (enforced by a database trigger).
4. **Pluggable storage** — Local filesystem today, S3 / R2 next. Business logic never bypasses the storage adapter.
5. **Self-hosted by default** — Your data stays on infrastructure you control.

See **[Restore guarantee](./docs/src/content/docs/concepts/restore-guarantee.md)** for the full explanation.

---

## What Marrow is (v0.1)

- Pages organized in a tree: Organizations → Workspaces → Spaces → Collections → Pages
- BlockNote-powered editor with code blocks, tables, page links, and `@` mentions
- File attachments
- Full-text search across a workspace
- Append-only revision history on every save
- One-command export to a transparent zip bundle (full or slim)
- One-command restore from any export bundle (forwards-compatible across versions)
- OIDC authentication with org-level RBAC (owner / editor / viewer)
- Pluggable storage (local filesystem; S3 / R2 next)

---

## Quickstart (development)

**Prerequisites:** Python 3.11+, Node.js 20+, Docker.

```bash
git clone https://github.com/spmcgraw/marrow.git
cd marrow

# Database
docker compose up -d

# Backend
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload         # http://localhost:8000
```

In a second terminal:

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev                       # http://localhost:3000
```

For more depth see **[Quickstart](./docs/src/content/docs/getting-started/quickstart.md)**.

---

## Production deployment

- **[Docker Compose](./docs/src/content/docs/deployment/docker-compose.md)** — recommended. Build images, configure `.env`, `docker compose -f docker-compose.prod.yml up`.
- **[Cloudflare](./docs/src/content/docs/deployment/cloudflare.md)** — Pages + Containers + Neon + R2 (config landed in v0.1.0; full deploy finalized in [#41](https://github.com/spmcgraw/marrow/issues/41)).

See **[Environment variables](./docs/src/content/docs/configuration/env-vars.md)** for the full config reference and **[OIDC](./docs/src/content/docs/configuration/oidc.md)** for sign-in setup.

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 |
| Frontend | Next.js 16, React 19, Tailwind 4, Base UI, BlockNote |
| Auth | OIDC (any provider) + API key fallback |
| Search | PostgreSQL FTS (Meilisearch later) |
| Storage | Local filesystem (S3-compatible adapter next) |
| CLI | Typer (`marrow export`, `marrow restore`) |

---

## Tests

```bash
cd api && pytest                            # full suite (integration tests use a real DB)
cd api && pytest tests/test_round_trip.py   # the restore-guarantee regression anchor
cd web && npm run lint && npm run build     # frontend
cd docs && npm run build                    # docs site
```

---

## Contributing

Marrow is open source because the philosophy demands it. A sovereign knowledge base built behind closed doors would be a contradiction.

Before writing code, read the **[Restore guarantee](./docs/src/content/docs/concepts/restore-guarantee.md)**. Any contribution that compromises the export/restore round-trip will not be merged.

---

## License

Apache 2.0. Use it, fork it, deploy it, build on it. Just don't tell people their data is theirs if it isn't.

---

*Marrow: the core that holds everything together — portable, durable, yours.*
