---
title: Docker Compose deployment
description: Run Marrow in production with Docker Compose.
---

The repo ships two Compose files:

- `docker-compose.yml` — local dev. Just PostgreSQL on port 5433.
- `docker-compose.prod.yml` — full stack: Postgres + API + web. Production-style.

## 1. Configure

```bash
cp .env.prod.example .env
```

Edit `.env`. The required values:

| Variable | Why |
| --- | --- |
| `SECRET_KEY` | Signs the session JWT. Use a long random string. |
| `POSTGRES_PASSWORD` | Postgres user password. |
| `NEXT_PUBLIC_API_URL` | The URL the browser will call to reach the API (e.g. `https://api.example.com`). |

See [Environment variables](/configuration/env-vars/) for the full reference, including OIDC and CORS.

## 2. Build and start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This:

1. Brings up PostgreSQL with a persistent volume (`postgres_data`).
2. Builds the API image and runs `alembic upgrade head` then `uvicorn`.
3. Builds the web image with the right `NEXT_PUBLIC_*` values baked in (Next.js inlines these at build time).

The API exposes port 8000 and the web exposes port 3000 by default. Override with `API_PORT` / `WEB_PORT`.

## 3. Verify

```bash
curl http://localhost:8000/health
```

Open `http://localhost:3000` — you should see the workspace list.

## Volumes

Two volumes hold all state:

- `postgres_data` — the database.
- `api_storage` — uploaded attachments (mounted at `/data/storage` inside the API container).

Back up both for a complete restore. Or use `marrow export` for portable bundles — see [Restore guarantee](/concepts/restore-guarantee/).

## Reverse proxy

The Compose file does not include a reverse proxy. In production, terminate TLS in front of the web container with Caddy, Traefik, or nginx, and point `NEXT_PUBLIC_API_URL` at the public API hostname.

If the API and web are on different subdomains, set `CORS_ORIGINS` to the web origin and `COOKIE_DOMAIN` to the parent domain (e.g. `.example.com`) so the session cookie is shared.

## Updating

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Migrations run automatically on container start.
