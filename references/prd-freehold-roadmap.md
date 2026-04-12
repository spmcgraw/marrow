# Freehold Product Roadmap — PRD

## Overview

Freehold is an open-source, self-hostable knowledge base built around a non-negotiable restore guarantee: any export bundle can be restored to an exact replica of the original workspace. The v0.1 MVP proves this technically — append-only revisions, zip-based export/restore, and a round-trip integration test that validates the cycle.

This PRD defines the phased roadmap to turn Freehold from a working proof-of-concept into a product that solo contractors and small teams use daily. Each phase is a shippable milestone with its own "done" criteria. Phases can overlap in development but ship sequentially.

**Target user (day one):** Solo contractors and freelancers managing multiple client engagements. One workspace per client. Export when the engagement ends. Restore when they come back.

**Tagline:** "A knowledge base you can leave — and come back to."
**Subheading:** "Fully exportable. Truly portable. Your data stays yours."

---

## Phase 1 — Usable Knowledge Base

**Goal:** Make Freehold usable enough that a solo contractor replaces their current wiki/notes tool with it.

### 1.1 Search

**Decision:** PostgreSQL full-text search. No new infrastructure.
**Why:** Freehold already requires Postgres. A `tsvector` column on pages with a GIN index gets ranked full-text search with zero new services. Handles 10k+ pages comfortably.
**Rejected:** Meilisearch (adds a service dependency, overkill for launch), application-level search (too slow past 1k pages).

**Implementation:**
- Add `search_vector` tsvector column to `pages` table
- GIN index on `search_vector`
- Trigger on revision insert updates the search vector
- `GET /api/workspaces/{id}/search?q=term` returns ranked page stubs
- Frontend: Cmd+K / Ctrl+K search bar in sidebar, results in dropdown overlay
- API contract abstracted so Meilisearch can slot in later without frontend changes

**Done when:**
- User can search by page title and body content across a workspace
- Results ranked by relevance, returned in <200ms for workspaces under 10k pages
- Search bar accessible from every page via keyboard shortcut

### 1.2 Authentication

**Decision:** OIDC-first. Freehold validates JWT tokens from a configured OIDC provider.
**Why:** Avoids building password hashing, reset flows, email verification, brute-force protection. Self-hosters point at their own IdP (Keycloak, Okta, Azure AD). SaaS tier uses a managed provider (Clerk/Auth0). SSO is a natural consequence, not a separate feature.
**Rejected:** Built-in email/password (massive security surface area for a small team), OAuth-only without OIDC (less standardized, harder for self-hosters).

**Implementation:**
- OIDC discovery endpoint configuration (env var or admin UI)
- JWT validation middleware replacing current API key check
- `users` table: id, external_id (from OIDC), email, display_name, created_at
- Session management (JWT in httpOnly cookie or Authorization header)
- API key auth preserved as a fallback for programmatic access and backward compatibility
- SaaS: managed OIDC provider (Clerk or Auth0 — exact choice deferred)

**Done when:**
- Users can sign in via OIDC provider
- Self-hosters can configure their own IdP
- API key auth still works for scripts/CLI
- No unauthenticated access to workspace data

### 1.3 Organizations and Roles

**Decision:** Org-owned workspaces. Three roles: owner, editor, viewer.
**Why:** A solo contractor is an org of one. A 5-person team is an org of five. Same model, no migration later. Three roles cover 95% of cases for teams under 20.
**Rejected:** User-owned workspaces (leads to personal vs. team workspace mess), granular RBAC (time sink, not needed at this scale).

**Implementation:**
- `organizations` table: id, name, slug, created_at
- `org_memberships` table: org_id, user_id, role (owner/editor/viewer)
- Workspaces get an `org_id` foreign key
- Middleware enforces role-based access on all routes
- Owner: full control (delete workspace, manage members, export/restore)
- Editor: create/edit pages, collections, spaces
- Viewer: read-only access

**Done when:**
- Workspaces belong to organizations
- Users can be invited to orgs with a specific role
- Role enforcement on all API endpoints
- Solo users experience no friction (auto-created personal org)

### 1.4 Editor Enhancements

**Decision:** Add inline page links, code blocks with syntax highlighting, and basic tables. Dual format storage — BlockNote JSON canonical, Markdown generated on export.
**Why:** These three features cover the core knowledge base writing needs. Dual format means the editor isn't artificially constrained by Markdown limitations while preserving human-readable exports.
**Rejected:** Column layouts, colored text, custom block types (don't round-trip to Markdown for the human-readable export layer), embeds (not launch-critical).

**Implementation:**
- BlockNote extensions: page links (`[[page]]` or `@`-mention), code blocks (with Prism/Shiki), tables
- Revision content format migration: TEXT (Markdown) → JSONB (BlockNote JSON)
- `content_format` column on revisions or schema version bump to distinguish legacy Markdown from JSON
- Export generates both `pages/{id}.json` (canonical) and `pages/{id}.md` (human-readable)
- `blocksToMarkdownLossy()` already exists for the Markdown rendering path
- Restore reads JSON format; legacy Markdown revisions still supported

**Done when:**
- Users can create page links, code blocks, and tables in the editor
- Revisions store BlockNote JSON as canonical format
- Export bundles contain both JSON and Markdown for every page
- Restore works from both new (JSON) and legacy (Markdown) bundles

### 1.5 Export UX Improvements

**Decision:** Full revision history by default, `--slim` flag for current-content-only. UI warns about file size.
**Why:** Default protects the restore guarantee. Slim flag respects practicality for users who just want a portable snapshot.

**Implementation:**
- `--slim` CLI flag skips revisions directory in export
- API export endpoint accepts `?slim=true` query param
- Frontend export dialog shows estimated bundle size
- Warning text when full history is selected: explains file size implications

**Done when:**
- Both full and slim exports work via CLI and API
- UI shows size estimate and explains the tradeoff

### 1.6 v0.1.0 Release — Deployment Docs, Docker, and README

**Decision:** Ship v0.1.0 after #37 and #38 are both complete.
**Why:** All Phase 1 functionality must be in place before the first public release. Deployment artifacts and documentation are the final step — they let a self-hoster get running without reading source code.

**Implementation:**
- `README.md` updated: project overview, feature summary, local dev quickstart
- `Dockerfile` for FastAPI backend
- `Dockerfile` for Next.js frontend
- `docker-compose.prod.yml` for production-style deployment with env var docs
- Environment variable reference complete for both `api/.env` and `web/.env.local`
- OIDC configuration guide (Keycloak, Google, etc.)
- GitHub release `v0.1.0` tagged on `main`

**Blocked by:** 1.4 (#37), 1.5 (#38)

**Done when:**
- A stranger can self-host Freehold in under 30 minutes following the README
- `v0.1.0` GitHub release created and tagged

---

## Phase 2 — Collaboration and SaaS

**Goal:** Launch the hosted SaaS tier. Enable team collaboration and external sharing.

### 2.1 Sharing Links

**Decision:** View-only public links for pages and collections. No account required to view.
**Why:** Contractors share project docs with clients constantly. This is the simplest collaboration primitive — no real-time, no permissions complexity.

**Implementation:**
- `share_links` table: id, resource_type (page/collection), resource_id, token (unique), created_by, expires_at (nullable), created_at
- `GET /shared/{token}` returns read-only rendered content
- Frontend: "Share" button in page toolbar generates link
- Optional expiry date on links
- Owner/editor can revoke links

**Done when:**
- Users can generate a view-only link for any page or collection
- Link recipients can read content without an account
- Links can be revoked or set to expire

### 2.2 SaaS Deployment

**Decision:** Fly.io for backend + Postgres, Vercel for frontend. Shared database with Postgres Row Level Security for tenant isolation.
**Why:** Fly.io supports region-selectable deploys (data sovereignty). Shared DB with RLS enforces isolation at the database level (same philosophy as revision immutability trigger). Vercel is the natural fit for Next.js.
**Rejected:** Database-per-tenant (operationally expensive, doesn't scale cheaply at free tier), AWS/GCP (overkill at this stage), Railway (less regional control).

**Implementation:**
- Postgres RLS policies on all tables: `WHERE org_id = current_setting('app.current_org')`
- Middleware sets `app.current_org` on every request from authenticated user's org
- Fly.io deployment config (fly.toml, health checks, auto-scaling)
- Vercel deployment for frontend
- Local filesystem storage on Fly.io volume initially; S3 adapter later
- CI/CD pipeline: GitHub Actions → deploy on merge to main

**Done when:**
- SaaS instance running on Fly.io with RLS-enforced tenant isolation
- Frontend deployed on Vercel
- Region-selectable deployment documented
- Health monitoring and basic alerting in place

### 2.3 SaaS Pricing Tiers

**Decision:** Free tier with limits, paid tier ~$8-12/user/month. Self-hosted is fully free.
**Why:** Free tier drives adoption. Limits on workspace count and storage (not features) create natural upgrade pressure without feeling hostile to open-source-leaning users. SSO is the one feature gate (industry standard).
**Rejected:** Feature-gating (hostile to target audience), usage-based pricing (unpredictable for small teams).

**Tiers:**
- **Free:** 1 workspace, 100MB attachment storage, 3 members
- **Pro (~$8-12/user/month):** Unlimited workspaces, 10GB storage, unlimited members, custom OIDC/SSO
- **Self-hosted:** Completely free, unlimited everything

**Done when:**
- Billing integration (Stripe) handles subscriptions
- Free tier limits enforced in the application
- Upgrade flow in the UI
- SSO configuration gated behind Pro tier on SaaS

### 2.4 Page Properties System

**Decision:** Typed key-value metadata on pages. Foundation for PM features in phase 4.
**Why:** Knowledge base use cases (tags, categories, status labels) need structured metadata. Building this now on solid ground means PM later inherits a battle-tested system.

**Implementation:**
- `page_properties` table: id, page_id, key, value, value_type (text/number/date/select/multi-select/checkbox)
- Collection-level schemas: a collection can define "every page here has these properties with these types"
- Properties included in export bundle (in page JSON and manifest)
- Frontend: property editor below page title (tag-style chips, date pickers, dropdowns)
- Properties searchable via FTS

**Done when:**
- Pages can have typed properties
- Collections can define property schemas
- Properties render in the editor and are included in exports
- Properties are searchable

### 2.5 Collection Views

**Decision:** Table view and board view over collections. Renders pages as rows/cards using their properties.
**Why:** This transforms collections from flat page lists into structured views. Direct foundation for PM (a board view with status columns = a kanban board).

**Implementation:**
- `collection_views` table: id, collection_id, view_type (table/board/list), config (JSONB — sort, filter, group-by)
- Frontend: view switcher in collection header
- Table view: spreadsheet-style rows with property columns
- Board view: columns grouped by a select property
- List view: current sidebar-style list (default)

**Done when:**
- Users can create table and board views on any collection
- Views can sort, filter, and group by properties
- Views included in export metadata

---

## Phase 3 — Privacy and Real-Time

**Goal:** Ship E2EE for SaaS users and real-time collaborative editing.

### 3.1 End-to-End Encryption

**Decision:** E2EE for SaaS tier. Client-side encryption/decryption. Server never sees plaintext.
**Why:** "We can't read your data even if we wanted to" is a differentiator no competitor offers with collaboration. Mentioned on the public roadmap from day one to build trust.

**Key challenges:**
- Key management: org-level keys, distributed to members via key wrapping
- Access revocation: re-encrypt with new key when a member is removed
- Search: client-side search index required (server can't FTS over ciphertext)
- Restore guarantee: encrypted export bundles must be restorable with the org's key
- Key loss: if the owner loses the key, data is unrecoverable. This is a feature, not a bug — but requires clear UX communication and recovery key ceremony.

**Open questions (to resolve before implementation):**
- Exact key management model (per-workspace vs. per-org keys)
- Client-side search index approach (encrypted SQLite, bloom filters, etc.)
- Recovery key UX (print-and-store, split across admins, etc.)
- Impact on export bundle format (encrypted JSON + key metadata)

**Done when:**
- SaaS users can enable E2EE per workspace
- Content encrypted client-side before transmission
- Server stores only ciphertext
- Export bundles are restorable with the workspace key
- Search works on encrypted workspaces (client-side)

### 3.2 Real-Time Collaborative Editing

**Decision:** Yjs-based CRDT sync via WebSocket. Ships alongside or after E2EE.
**Why:** BlockNote already supports Yjs. Async editing (last-write-wins) works for launch, but real-time is expected by teams comparing to Notion. Shipping after E2EE means the collab protocol can be designed with encryption in mind.
**Rejected:** Operational Transform (more complex, less suited to P2P/encrypted scenarios).

**Implementation:**
- WebSocket server (Hocuspocus or custom) for Yjs sync
- Presence awareness (cursors, selections, user avatars)
- Conflict resolution via Yjs CRDT (no last-write-wins)
- Revision snapshots at save points (not every keystroke)
- E2EE-compatible: Yjs updates encrypted in transit

**Done when:**
- Multiple users can edit the same page simultaneously
- Live cursors and presence indicators
- Changes sync in real-time without data loss
- Works with E2EE enabled

---

## Phase 4 — Project Management

**Goal:** Extend the knowledge base into lightweight project management, built entirely on the page/properties/views foundation.

### 4.1 PM Templates

**Decision:** Tasks are pages with structured properties. A "project" is a Collection with a predefined schema and board view.
**Why:** No new data model. Tasks get the restore guarantee, export format, revision history, and search for free. The connection between docs and tasks is native — a task can link to a spec page because they're both pages.
**Rejected:** Separate tasks table (breaks restore guarantee for integrated data, adds a parallel data model).

**Implementation:**
- Project template: creates a Collection with properties (status, assignee, priority, due date) and a default board view
- Task template: creates a Page with those properties pre-filled
- Templates are just JSON definitions — exportable, restorable, shareable
- Automations (move to "Done" when checkbox checked, etc.) are future scope

**Done when:**
- Users can create a "Project" from a template
- Tasks appear as pages with structured properties
- Board and table views work for project management workflows
- Projects export and restore perfectly (they're just collections)

---

## Non-Goals (Across All Phases)

- Fuzzy/typo-tolerant search at launch (Meilisearch upgrade path exists)
- Searching within attachments or revision history
- Custom RBAC beyond three roles
- Notion-style databases-as-first-class (properties on pages achieve this without the complexity)
- Offline-first/local-first sync (revisit if demand warrants)
- Mobile native apps (responsive web is sufficient)
- Marketplace for plugins/extensions
- AI features (summarization, search, writing assistance)

---

## Open Questions

| Question | Why Deferred | Blocks |
|----------|-------------|--------|
| Exact OIDC provider for SaaS (Clerk vs Auth0) | Needs evaluation of pricing, DX, and self-hosted story | Phase 1.2 implementation |
| Content format migration path (TEXT → JSONB revisions) | Needs design for backward compatibility with existing exports | Phase 1.4 implementation |
| E2EE key management model | Requires dedicated security review | Phase 3.1 |
| Client-side search for encrypted workspaces | Depends on E2EE architecture | Phase 3.1 |
| Self-hosted enterprise tier pricing | No data yet on what teams will pay for | Post-phase 2 |
| S3 storage adapter timeline | Local filesystem on Fly.io volume works initially | Phase 2.2 (nice-to-have) |

---

## Assumptions

- Solo contractors and freelancers will adopt a self-hosted or free-tier knowledge base if the export story is demonstrably better than Notion/Confluence
- PostgreSQL FTS quality is sufficient for workspaces under 10k pages — users won't churn over lack of typo tolerance
- OIDC is well-understood enough by self-hosters that "bring your own IdP" isn't a support burden
- Three roles (owner/editor/viewer) cover 95%+ of permission needs for teams under 20
- Fly.io remains price-competitive and reliable for the SaaS tier at early scale
- BlockNote's Yjs support is mature enough to build real-time collab on when phase 3 arrives
- The EU Data Act and "file over app" movement continue to drive awareness of data sovereignty

---

## Technical Notes

- `revisions.content` is currently TEXT holding Markdown. Phase 1.4 requires migration to JSONB or a `content_format` discriminator column. Legacy Markdown revisions must remain readable.
- `pages.current_revision_id` uses a deferred FK — same pattern should apply to any new deferred relationships.
- `revisions_immutable()` PL/pgSQL trigger enforces append-only at the DB level. Any new immutability constraints should follow this pattern (DB-level, not app-level).
- `StorageAdapter` ABC is ready for S3 implementation. `LocalFilesystemAdapter` is the only current impl. Tests use `FakeStorageAdapter` (in-memory).
- `apiFetch<T>()` in `web/lib/api.ts` centralizes auth headers. New endpoints (search, sharing) just need new client functions following the existing pattern.
- Postgres RLS for multi-tenancy follows the same philosophy as the immutability trigger: enforce at the database level, don't trust the application.
- Export bundle format change (adding .json alongside .md) requires a schema version bump in manifest.json. Restore must handle both v1 (Markdown-only) and v2 (dual format) bundles.
- `blocksToMarkdownLossy()` already exists in the frontend. The "lossy" is honest — rich features (columns, colors) degrade gracefully to plain Markdown.