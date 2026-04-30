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
| `MARROW_API_URL` | The URL the browser will call to reach the API (e.g. `https://api.example.com`). |

See [Environment variables](/configuration/env-vars/) for the full reference, including OIDC and CORS.

:::caution[Postgres password gotcha]
`POSTGRES_PASSWORD` is only applied the first time the database volume is initialized. If you change it later, the existing user keeps the **old** password and the API will fail with `password authentication failed for user "marrow"`.

To start over:

```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

`-v` removes the volume — only safe before you have real data.
:::

## 2. Pull and start

```bash
docker compose -f docker-compose.prod.yml up -d
```

This:

1. Brings up PostgreSQL with a persistent volume (`postgres_data`).
2. Pulls the API image from GHCR and runs `alembic upgrade head` then `uvicorn`.
3. Pulls the web image from GHCR. The browser-visible config (`MARROW_API_URL`, `MARROW_API_KEY`, `MARROW_OIDC_ENABLED`) is read from container env at startup and written into `/config.js` — no rebuild needed when these change.

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

The Compose file does not include a reverse proxy. In production, terminate TLS in front of the web container with Caddy, Traefik, or nginx, and point `MARROW_API_URL` at the public API hostname.

If the API and web are on different subdomains, set `CORS_ORIGINS` to the web origin and `COOKIE_DOMAIN` to the parent domain (e.g. `.example.com`) so the session cookie is shared.

## Updating

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Migrations run automatically on container start.
