---
title: Cloudflare deployment
description: Deploy Marrow to Cloudflare Pages + Containers, with Neon for Postgres and R2 for attachments.
---

:::caution
The Cloudflare deployment path is **deferred to [issue #41](https://github.com/spmcgraw/marrow/issues/41)**. The repo ships intended `wrangler.toml` configs in v0.1.0, but `@cloudflare/next-on-pages` does not yet support Next.js 16 (peer range `>=14.3.0 <=15.5.2`). The container side (API on Cloudflare Containers) is structurally ready. This page documents the intended topology; expect updates once next-on-pages or OpenNext adds Next 16 support.
:::

## Topology

| Component | Service |
| --- | --- |
| Frontend | Cloudflare Pages (`@cloudflare/next-on-pages`) |
| Backend API | Cloudflare Containers (image from GHCR) |
| Database | [Neon](https://neon.tech) Postgres |
| Attachments | Cloudflare R2 (S3-compatible) — *adapter not yet implemented; falls back to container-local storage today* |
| DNS | Cloudflare DNS (`marrow.so`) |

## Prerequisites

- A Cloudflare account with Pages and Containers enabled.
- A Neon project with a Postgres instance.
- `wrangler` CLI authenticated (`wrangler login`).
- A GitHub Container Registry (GHCR) login token if pushing images manually.

## 1. Configure secrets

In the Cloudflare dashboard or via `wrangler secret put`:

- `SECRET_KEY`
- `DATABASE_URL` (Neon connection string)
- `OIDC_CLIENT_SECRET` (if using OIDC)

Non-secret config goes in `api/wrangler.toml` and `web/wrangler.toml`.

## 2. Build the web app

```bash
cd web
npm run pages:build
npm run pages:deploy
```

`pages:build` runs `@cloudflare/next-on-pages`, which translates the Next.js standalone output into the format Cloudflare Pages expects.

## 3. Build and deploy the API container

The GitHub Actions release workflow does this automatically on push to `main`. To do it manually:

```bash
cd api
docker build -t ghcr.io/<you>/marrow-api:latest .
docker push ghcr.io/<you>/marrow-api:latest
wrangler deploy
```

## 4. DNS and cookies

For the session cookie to be shared between `app.marrow.so` and `api.marrow.so`, set:

- `COOKIE_DOMAIN=.marrow.so`
- `CORS_ORIGINS=https://app.marrow.so`
- `FRONTEND_URL=https://app.marrow.so`

## See also

- [Environment variables](/configuration/env-vars/)
- [OIDC](/configuration/oidc/)
