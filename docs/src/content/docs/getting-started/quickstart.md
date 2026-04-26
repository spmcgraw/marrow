---
title: Quickstart
description: Run Marrow locally for development.
---

This walks you through running Marrow on your machine for development. For production deployment, see [Docker Compose](/deployment/docker-compose/) or [Cloudflare](/deployment/cloudflare/).

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for the local PostgreSQL container)

## 1. Clone the repo

```bash
git clone https://github.com/spmcgraw/marrow.git
cd marrow
```

## 2. Start PostgreSQL

```bash
docker compose up -d
```

This brings up PostgreSQL 16 on port 5433 (so it doesn't collide with a local Postgres on 5432).

## 3. Backend setup

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`.

## 4. Frontend setup

In a second terminal:

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```

The frontend runs at `http://localhost:3000`.

## 5. Try it

- Open `http://localhost:3000`.
- Create a workspace, then a space, then a collection, then a page.
- Type into the editor — it auto-saves after 2 seconds and creates a revision on every save.
- Try `cd api && marrow export --workspace <slug> --output ./out.zip` and inspect the bundle. Then `marrow restore ./out.zip` into a fresh database to confirm the round-trip.

## Configuration

The default dev setup runs without authentication. To turn on auth, see:

- **[Environment variables](/configuration/env-vars/)** — full reference.
- **[OIDC](/configuration/oidc/)** — sign-in via Google, Keycloak, etc.
