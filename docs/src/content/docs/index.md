---
title: Marrow
description: Self-hosted, open-source knowledge base built around a non-negotiable restore guarantee.
---

Marrow is a self-hosted, open-source knowledge base. Every workspace can be exported to a transparent, human-readable bundle, and any export bundle can be restored to an exact replica of the original workspace.

## Where to start

- **[Quickstart](/getting-started/quickstart/)** — get a local instance running.
- **[Docker Compose](/deployment/docker-compose/)** — production-style self-host.
- **[OIDC](/configuration/oidc/)** — wire Marrow up to Google, Keycloak, or any OIDC provider.
- **[Restore guarantee](/concepts/restore-guarantee/)** — the architectural foundation.

## Core principles

1. **Restore guarantee.** Every export bundle is restorable to a byte-faithful workspace.
2. **Append-only history.** Every save is a new revision. Old revisions are never modified.
3. **Transparent format.** Bundles are plain Markdown + JSON in a zip.
4. **Self-hosted.** Your data never leaves the infrastructure you control.

[GitHub →](https://github.com/spmcgraw/marrow)
