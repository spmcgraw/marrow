# Data Model v2 — PRD

## Overview

Marrow's v0.1 data model — `organization → workspace → space → collection → page` — has more layers than the user types it serves and exposes friction during onboarding (issue #121). v0.2 collapses the page tree into a flexible node hierarchy, hides the org layer for solo users, and aligns terminology with what every modern collab tool uses (Notion / Slack / Linear / Slite). The new model serves four target users uniformly across self-hosted and SaaS: solo, consultancy/multi-client, multi-org employee, and single-team replacement (Confluence-style).

## Goals

- One mental model that works for solo self-hoster, consultancy, multi-org user, and single-team Confluence-replacement — both self-hosted and SaaS.
- Folders and pages mix freely under a space; arbitrary nesting depth.
- URLs survive moves, renames, and reorganization without redirect chains.
- Org/billing layer stays in the data model but is invisible to solo users until they need it.
- Soft-delete preserves user work; trash purges on a schedule.
- Restore guarantee preserved — v3 bundles still restore; new bundles use v4.
- Issue #121 (API_KEY mode can't create first workspace) dissolves structurally, not via UI patch.

## Non-goals

- Space-level ACLs (deferred to v0.3 — for v0.2 all workspace members see all spaces).
- Enterprise tier with multi-workspace billing rollups (deferred — Phase 3+).
- Cross-workspace node moves (use export/restore as the workaround).
- Cross-workspace wiki links / mentions (deferred — node UUIDs are workspace-scoped).
- Change to RBAC role names or count (still owner/editor/viewer).
- Editor changes — BlockNote stays. This PRD is data model only.

## Design Decisions

### Hierarchy

**Decision:** `organization → workspace → space → node (tree, type ∈ {folder, page})`. Five existing tables collapse to four: `organizations`, `workspaces`, `spaces`, `nodes`. Folders and pages mix freely at every level under a space.
**Why:** Matches the mental model of every modern wiki/notes tool. Eliminates the empty-middleman problem (current `collection` always has 1:N pages with no other purpose) while preserving the org layer for billing/admin separation.
**Rejected:** Collapsing org→workspace into a single `workspace` (loses the billing/admin layer that consultancies and multi-org users actually need); keeping collections as a fixed level (forces structural rules users don't want).

### Node table shape

**Decision:** Single `nodes` table with `type` discriminator (`'folder' | 'page'`), self-referential `parent_id` (nullable for space-root children), `space_id` FK, `position` (fractional index string), and page-only nullable columns: `current_revision_id`, `search_vector`. Folders carry `name`, `slug`, optional `description`. Pages carry the rest.
**Why:** Tree traversal is one recursive CTE on one table. Drag-and-drop, breadcrumbs, search, exports all uniform. Future node types (databases, embeds, whiteboards) drop in without schema changes.
**Rejected:** Separate `folders` and `pages` tables (every tree query becomes a UNION; same problem we just escaped from).

### Node type constraints

**Decision:** A page-only column being non-NULL on a `type='folder'` row (or vice versa) is rejected by a check constraint. `revisions.node_id` FK with a check that the referenced node is `type='page'`. Append-only revision trigger continues to apply.
**Why:** Schema-level guarantees > application-level discipline. Bugs in routes can't corrupt data shape.
**Rejected:** Trusting application code to enforce typing (will drift).

### URLs

**Decision:** Stable, UUID-based, slug-suffixed. Canonical form `/w/{workspace-slug}/n/{node-uuid}/{slug}`. Slug is decorative; UUID is authoritative. Renames/moves don't change the URL.
**Why:** Move-stable, rename-stable, no redirect chains, no slug-collision logic, restore-friendly.
**Rejected:** Path-based URLs (`/w/.../s/.../folder1/page-name`) — every move/rename breaks links.

### Sibling ordering

**Decision:** `position` field as a fractional index string. New nodes inserted at the **bottom** of their parent (lex-greater than all existing siblings). User drag-and-drop overrides freely. No alphabetical mode in v0.2.
**Why:** Wiki structure carries intentional order; new items shouldn't elbow above curated content. Fractional indexing keeps reorder cost O(1) with no rebalancing.
**Rejected:** Recency-based default with mode-switch on drag (confusing UX); integer position with rebalancing (rewrites N rows on insert near top).

### Delete semantics

**Decision:** Soft-delete via `deleted_at` timestamp on `nodes`. Cascades to descendants in one transaction. Trashed nodes hidden from tree, search, backlinks. Trash view per workspace shows only top-level deleted nodes; restoring restores the subtree. Scheduled purge after 30 days. Revisions on trashed pages stay append-only until purge.
**Why:** Knowledge bases get reorganized constantly. Hard-delete by default = inevitable lost work. Append-only revisions already encode "never lose history"; soft-delete is the consistent extension.
**Rejected:** Hard-delete on user action (no modern wiki does this for good reason).

### Cross-workspace moves

**Decision:** Disallow node moves across workspace boundaries in v0.2. Cross-workspace migration uses export → restore.
**Why:** Every node has exactly one workspace ancestor, always. Restore guarantee, RBAC chain, and search scope all stay simple. Cross-workspace is a small minority of real moves.
**Rejected:** Allowing cross-workspace moves (forces revision provenance, attachment storage, and search-index complexity that's not earning its keep yet).

### Org lifecycle & visibility

**Decision:** Auto-create one personal org per OIDC user on first login, named `"{User Name}'s Org"`. Hide all org UI until the user has 2+ workspaces in any org OR is a member of 2+ orgs — then surface an "Org settings" panel in the user menu. API_KEY mode auto-creates a default org named `"Default"` on first boot if none exists.
**Why:** Solo users never see the word "organization." Multi-tenant cases (consultancy, multi-org) get the surface they need exactly when they need it. Issue #121 dissolves — there's always a default org for API_KEY mode.
**Rejected:** Always-visible org UI (friction for 80% of users); dropping orgs entirely (loses billing/admin layer for SaaS and consultancies).

### Workspace lifecycle

**Decision:** First workspace per org auto-created at the same moment as the org, named matching the org. Additional workspaces created via UI by org owner/editor. Workspace-create form does NOT ask for `org_id` — it's resolved from the current workspace context. Switching workspaces (within an org or across orgs) happens via avatar popover (issue #111).
**Why:** Removes the upfront-decision friction. Users who never need a second workspace never see the concept. Solves #121 without a dropdown UI.
**Rejected:** Requiring explicit workspace creation at signup (worse UX, same data shape).

### Space lifecycle

**Decision:** Spaces are explicit and user-created. Sit directly under workspace. No "personal space" magic — the Confluence pattern of "personal space + access to other internal spaces" is served by **workspace-level membership** instead. A space is just a top-level grouping with workspace-level ACLs in v0.2.
**Why:** Personal-vs-shared distinction lives at the workspace boundary, not inside it. Cleaner mental model. Avoids the Confluence-style "user spaces" namespace that gets crufty.
**Rejected:** Auto-created personal spaces inside workspaces (confuses the workspace-vs-space-vs-personal layering).

### RBAC layering

**Decision:** Three roles (owner/editor/viewer) at **workspace level**. Org-level membership only matters for billing/admin: org owner can manage billing, create/delete workspaces, invite members to the org. Workspace-level role governs all data CRUD. Space-level ACLs deferred to v0.3.
**Why:** Workspace is the natural data-permission boundary; org is the natural billing-permission boundary. Don't mix them. Three roles is enough for v0.2; richer ACLs once real-customer needs surface.
**Rejected:** Org-level data permissions (over-couples billing and content); per-space ACLs in v0.2 (premature, no asks yet).

### Restore bundle scope

**Decision:** Bundle remains **per-workspace**. Manifest format bumps to **v4** capturing node tree, types, positions, slugs, soft-delete state. Org metadata (id, name) included in manifest for context but not required to restore — restore can target any org the user has access to. Trashed nodes omitted from bundle by default; `--include-trash` flag preserves them. v3 bundles continue to restore (auto-upgrade in restore code).
**Why:** Workspace = restore unit matches the existing model and the new RBAC boundary. Per-org bundles would force multi-workspace coordination that doesn't exist in any current tooling. Trash exclusion default keeps bundles small and predictable.
**Rejected:** Per-org bundles (mismatches RBAC, forces awkward partial restores); always-include-trash (bloats bundles for the 99% case).

### Migration from v0.1.x

**Decision:** One-shot Alembic migration in v0.2.0:
1. Add `nodes` table with all columns, FK constraints, check constraints.
2. For each existing `collections` row → insert a `nodes` row with `type='folder'`, copy `name` / `slug` / `space_id`, `parent_id=NULL`, `position` synthesized from current order.
3. For each existing `pages` row → insert a `nodes` row with `type='page'`, `parent_id=` the synthesized folder-node, copy `title` (→ `name`), `slug`, `current_revision_id`, `search_vector`, `position`.
4. Repoint `revisions.page_id` → `revisions.node_id`. Update the FK constraint.
5. Drop `collections` and `pages` tables.
6. Document as breaking. v3 export bundles still restore (restore code auto-upgrades to v4 on read).

The PRD assumes no production users — confirmed by stakeholder. If that ever changes, this section needs revisiting.
**Why:** One-shot is honest. Two-phase migrations (dual-write, backfill, switch) cost more code than they're worth at zero users.
**Rejected:** Dual-write migration (zero benefit at current scale); soft-deprecation (carries the old schema forever).

## Open Questions

- **Cross-workspace wiki links / mentions.** Today, page mentions and `/page` slash item are scoped to the workspace. v0.2 keeps this. Do we want to surface "from another workspace I have access to" linking later? Deferred — needs a user research signal first. Blocks nothing.

- **Workspace ownership transfer.** What happens when the org owner who created a workspace leaves the org? Probably "ownership transfers to the org owner of record." Not specified in this PRD — flag for v0.2 implementation.

- **Search scope.** Should search default to current-workspace-only or current-org (across workspaces the user can see)? Deferred — current-workspace is the safer default; can add an "All my workspaces" toggle later.

- **Folder content / metadata.** Folders carry `description` in this PRD. Do they also carry rich content (a "folder home page")? Notion treats every page-with-children as both a doc and a container. Marrow currently doesn't. Deferred — could promote folder→page-with-children or add a `home_page_node_id` later without a migration.

- **Trash purge schedule.** PRD says 30 days. Configurable? Per-workspace? Skip the config in v0.2; revisit if anyone asks.

## Assumptions

- No production users today; one-shot migration is safe.
- BlockNote editor and revision content format (markdown/JSON) stay unchanged. This PRD touches only the structural model.
- Postgres FTS continues to be sufficient for v0.2 search; Meilisearch swap is a separate decision.
- The append-only revision invariant remains non-negotiable.
- Restore guarantee remains non-negotiable — round-trip test stays green through the migration.
- Self-hosted and SaaS deployments share the exact same data model; SaaS-specific concerns (billing, enterprise) layer on top of org without modifying any of the above.

## Technical Notes

- Existing tables that **stay**: `organizations`, `workspaces`, `spaces`, `org_memberships`, `users`, `attachments`, `revisions` (with FK rename).
- Existing tables that **die**: `collections`, `pages` (rolled into `nodes`).
- Existing trigger `revisions_immutable()` continues to apply — it operates on the table, not on column shape.
- New trigger or check constraint: ensure page-only columns null on folders, folder-only columns null on pages, and `revisions.node_id` references a `type='page'` node.
- New trigger: maintain `nodes.search_vector` (FTS) on revision insert, scoped to `type='page'`. Direct port of existing `pages` trigger logic.
- New `deleted_at` index for trash filtering: `CREATE INDEX idx_nodes_active ON nodes (workspace_id) WHERE deleted_at IS NULL`.
- Fractional indexing: use `fractional-indexing` npm package on the frontend; equivalent Python implementation on the backend (small, ~50 LOC).
- Frontend route changes: `/w/{workspaceSlug}/pages/{pageId}` → `/w/{workspaceSlug}/n/{nodeId}/{slug?}`. `app/w/[workspaceId]/pages/[pageId]/` directory renames accordingly.
- API route changes: collection-scoped page routes (`/api/collections/{cid}/pages/...`) deprecated and removed. Global node routes added: `/api/nodes/{nodeId}` (get/patch/delete), `/api/spaces/{sid}/nodes` (list root children, create), `/api/nodes/{nodeId}/children` (list children, create child). Revision routes: `/api/nodes/{nodeId}/revisions`. Attachment routes scope to nodes.
- Existing `apiFetch<T>()` helper unchanged; only the path strings change.
- Tests that need updating: `test_models_smoke.py`, `test_round_trip.py`, `test_search.py`, `test_export.py`, `test_restore.py`. Add `test_node_tree.py` covering parent/child invariants, soft-delete cascade, position semantics.
- Issue #121 closes structurally as part of this PRD's implementation; issue #111 (multi-workspace switcher) gets simpler since "switch" is just workspace-scoped, no nested org switcher needed; issue #109 (skip workspace selection) lands users in their default workspace's home view trivially.
