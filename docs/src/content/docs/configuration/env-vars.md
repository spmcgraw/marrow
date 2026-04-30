---
title: Environment variables
description: Full reference for Marrow's backend and frontend environment variables.
---

Marrow has two `.env` files: one for the FastAPI backend (`api/.env`) and one for the Next.js frontend (`web/.env.local`). When deploying with `docker-compose.prod.yml`, both are sourced from a single root `.env` (see `.env.prod.example`).

## Backend (`api/.env`)

### Required

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | — | PostgreSQL connection string. Example: `postgresql://marrow:marrow@localhost:5433/marrow`. |
| `SECRET_KEY` | — | Signing key for the session JWT. **Use a long random string in production** (e.g. `openssl rand -hex 32`). |

### Storage

| Variable | Default | Description |
| --- | --- | --- |
| `STORAGE_PATH` | `./storage` | Directory where attachments are stored. Relative paths resolve from `api/`. Inside the API container, this is `/data/storage` and is backed by a Docker volume. |

### Authentication

Marrow checks auth in priority order: OIDC session cookie → `X-API-Key` header → anonymous. If neither OIDC nor `API_KEY` is set, **all requests are allowed** — fine for dev, never for prod.

| Variable | Default | Description |
| --- | --- | --- |
| `API_KEY` | unset | Static key for `X-API-Key` header. Bypasses RBAC (superuser equivalent). Used by the CLI and scripts. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins. |

### OIDC (optional)

Set `OIDC_ISSUER` to enable. All other OIDC vars are required when enabled.

| Variable | Description |
| --- | --- |
| `OIDC_ISSUER` | OIDC discovery URL, e.g. `https://accounts.google.com`. |
| `OIDC_CLIENT_ID` | Client ID from your IdP. |
| `OIDC_CLIENT_SECRET` | Client secret from your IdP. |
| `OIDC_REDIRECT_URI` | Where the IdP redirects after login. Must match what's registered. Example: `http://localhost:8000/api/auth/callback`. |
| `FRONTEND_URL` | Base URL of the web app. Used as the post-login redirect target. |
| `COOKIE_DOMAIN` | Domain for the `marrow_session` cookie. For dev: `localhost`. For prod with split subdomains: `.marrow.so`. |

See [OIDC](/configuration/oidc/) for setup walkthroughs.

## Frontend (`web/.env.local` for dev, container env for prod)

These are read at **runtime**, not build time. The container generates a small `/config.js` file from these env vars at startup, so the same prebuilt image works in any deployment without rebuilding.

| Variable | Default | Description |
| --- | --- | --- |
| `MARROW_API_URL` | `http://localhost:8000` | URL the browser uses to reach the API. Must be reachable from end-user browsers. |
| `MARROW_API_KEY` | unset | If `API_KEY` is set on the backend, set this to match. |
| `MARROW_OIDC_ENABLED` | unset | Set to `true` when OIDC is configured on the backend. Enables the `/login` route and route-protection middleware. |
| `INTERNAL_API_URL` | same as `MARROW_API_URL` | URL Next.js uses for SSR fetches inside the Docker network. Set to `http://api:8000` in the prod compose file. |

## Production compose root `.env`

When using `docker-compose.prod.yml`, both files are replaced by a single root `.env`. Additional vars used only by the Compose file:

| Variable | Default | Description |
| --- | --- | --- |
| `MARROW_VERSION` | `latest` | Image tag pulled from GHCR. |
| `POSTGRES_USER` | `marrow` | Postgres username. |
| `POSTGRES_DB` | `marrow` | Postgres database name. |
| `POSTGRES_PASSWORD` | — | **Required.** Postgres password. |
| `API_PORT` | `8000` | Host port the API binds to. |
| `WEB_PORT` | `3000` | Host port the web binds to. |
