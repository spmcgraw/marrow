# Marrow Design Implementation — PRD

## Context

User delivered a Claude Design handoff bundle containing a React prototype (`Marrow.html` + 7 JSX sources) for four Marrow surfaces: **Landing**, **Product**, **Pricing**, and **App UI**. The prototype establishes a dark-first visual language (Fraunces display serif, Inter body, JetBrains Mono, terracotta `#e8805c` accent, cream/bone secondary surfaces) and a restructured app shell (56px icon rail + panel-switched sidebar + editor with `...` menu / right drawer / floating comment bubble).

This work supports the **Phase 2 SaaS launch** (issue #32): landing/pricing pages are required to market the hosted tier being built in #41 (Cloudflare deployment) and #43 (Stripe tiers). The App UI reskin is a daily-use-value upgrade with no Phase 2 dependency and ships first.

Outcome: (a) a visually polished app matching the approved design, (b) a public marketing site on `marrow.so` ready for Phase 2 launch, and (c) tracked follow-up issues for the deferred backend features the design surfaces (Backlinks, Comments, Starred, Inbox, Watch, Archive).

Source bundle extracted to `/tmp/marrow-design/marrow/project/` — reference JSX files for exact styling values.

## Goals

- App UI visually matches the prototype: left rail, panel-switched sidebar, editor chrome (breadcrumbs + avatars + Share + `...` menu), right drawer for Backlinks/History, floating comment bubble + comments drawer
- Single source of search: left-rail Search tab only (Cmd+K removed; keybinding focuses the rail tab)
- BlockNote editor restyled to match design typography and block treatments (callouts, WikiLinks, tasks, metrics, code)
- Marketing site live on `marrow.so` (separate Next.js app) with Landing / Product / Pricing pages
- Every design-surfaced feature without a backend is captured as a GitHub issue so it doesn't drop

## Non-goals

- Building Backlinks / Comments / Starred / Inbox / Watch / Archive backends in this pass — UI shells + follow-up issues only
- Wiring real Stripe tier data into the pricing page — hardcoded copy now, swap in when #43 lands
- Mobile responsiveness of the App UI beyond what already exists (design is desktop-first)
- Migrating away from BlockNote or restructuring the revisions/pages data model
- Building the design's "Tweaks" toolbar (that was a design-editor affordance, not a product feature)

## Design Decisions

### Sequencing: App UI first, marketing follows
**Decision:** Two branches/PRs. `feature/app-ui-reskin` lands first; `feature/marketing-site` follows aligned with #43.
**Why:** App UI has no Phase 2 backend dependency. Marketing copy (especially pricing) benefits from Stripe tier work landing first, but hardcoded copy unblocks a parallel start if needed.

### Marketing site lives at `web-marketing/`
**Decision:** New Next.js 16 app in the monorepo alongside `web/`. Separate Cloudflare Pages project, deployed to `marrow.so`. `web/` continues as `app.marrow.so`.
**Why:** Clean subdomain split for SEO + auth-free marketing. Monorepo keeps tokens/fonts reviewable in one place. Shared tokens copied (not packaged) initially — they're small and change rarely.

### Single search = left-rail Search tab
**Decision:** Remove `search-dialog.tsx` entirely. Remove the "Search or jump…" pill from the Pages sidebar header (verify — chat indicates this was already removed). Cmd+K keybinding focuses the rail Search tab instead of opening a dialog.
**Why:** Matches the final design decision after iteration. Four search entry points in the old app was noise.

### Deferred features ship as UI shells, tracked as issues
**Decision:** Build the chrome (rail tabs, menu items, drawers, comment bubble) with empty or mocked-data states. Draft one GitHub issue per deferred backend feature listing scope, dependencies, and phase alignment. See **Follow-up issues** section.
**Why:** Keeps the visual design intact without a second reskin later, while avoiding backend scope creep in this PR.

### Theme toggle moves to Settings
**Decision:** Remove `theme-toggle` from the app header/layout. Add a Settings route (or dialog) under the user menu that hosts it.
**Why:** Per user direction — the tweaks toolbar was a prototype affordance; theme selection belongs in account settings, not app chrome.

### BlockNote restyled, not replaced
**Decision:** Keep BlockNote; restyle via its theme API and custom blocks. Port the design's callout, WikiLink (accent color + dashed underline), task, metrics grid, and code-block treatments. Page title uses Fraunces at 40px with `SOFT` variable axis.
**Why:** Preserves auto-save, @mentions, revision/JSON storage, and the existing editor tests. The prototype's static renderer is not production-viable.

## Implementation Plan

### Phase A: App UI reskin (ships first)

**New components (`web/components/`):**
- `app-rail.tsx` — 56px left rail. Workspace glyph button + 4 icon tabs (Pages/Search/Starred/Inbox) + settings + user avatar. Controlled by `railPanel` state lifted to workspace layout.
- `rail-panels/starred-panel.tsx` — list of starred pages (empty state for now)
- `rail-panels/inbox-panel.tsx` — notification feed (empty state for now)
- `rail-panels/search-panel.tsx` — move search UI out of `search-dialog.tsx` into a sidebar panel; wire to existing `searchWorkspace()` in `web/lib/api.ts`
- `page-menu.tsx` — `...` dropdown: Backlinks / Version history / Star / Watch / Duplicate / Move / Export / Archive. Backlinks + History open `side-drawer`. Archive styled destructive.
- `side-drawer.tsx` — 360px right-anchored drawer hosting Backlinks or History content (both use placeholder/empty states until their backends exist; History can wire to the existing `listRevisions` API)
- `comments-drawer.tsx` — 380px right drawer with comment list + composer (empty state)
- `comment-bubble-fab.tsx` — 48px floating button bottom-right with unread badge (always "0" until backend)

**Modify:**
- `web/app/w/[workspaceId]/layout.tsx` — add `AppRail` column; grid becomes `56px 272px 1fr`. Manage `railPanel` state here.
- `web/components/app-sidebar.tsx` — switch body content based on active rail panel (Pages tree / Search / Starred / Inbox). Replace tree header with workspace name + member count + chevron dropdown. Keep footer sync indicator; wire "Synced Xs ago" to real save state from page editor context if cheap, else stub.
- `web/components/inset-header.tsx` — restructure: breadcrumbs (mono font, muted) + stacked avatars (collaborators — mock until presence exists) + Share button + `PageMenu` trigger.
- `web/components/page-editor.tsx` — restyle BlockNote theme: Fraunces h1 with `SOFT` axis, WikiLink styling on `@` mentions / page links, callout block custom component, task list checkbox styling, code block chrome (`shell · copy` bar), metrics grid as a custom block or leave if not used organically. Keep auto-save, @mentions, revisions.
- `web/app/globals.css` — verify design tokens map cleanly to existing ones (primary → `#e8805c` for dark; audit light palette). Add Fraunces variable-axis font load including `SOFT` and `WONK`.
- `web/components/theme-toggle.tsx` — move into a new Settings screen/dialog under user avatar menu.
- Delete: `web/components/search-dialog.tsx` and all Cmd+K dialog wiring. Keep Cmd+K keydown handler that focuses the rail Search tab.

**Verification:**
- Run `cd web && npm run dev`; click through Pages/Search/Starred/Inbox rail tabs — each shows correct panel
- Open a page, click `...` → Backlinks drawer opens; click History → History drawer (shows real revision list via existing API)
- Floating comment bubble visible; click opens Comments drawer with empty state
- Cmd+K focuses rail Search tab (no dialog)
- Theme toggle reachable from user menu/settings, not app header
- `cd web && npm run lint` passes
- `cd web && npm run build` succeeds
- Existing tests in `web/` pass

### Phase B: Marketing site

**Scaffold:** `web-marketing/` — `npx create-next-app@latest web-marketing --ts --tailwind --app --no-src-dir`. Copy tokens from `web/app/globals.css` and Fraunces/Inter/JetBrains Mono font setup from `web/app/layout.tsx`.

**Pages (ported from prototype):**
- `app/page.tsx` — Landing (from `landing.jsx`): dark hero with "Your knowledge, down to the marrow.", Marrow app-header product peek, MIT/Postgres/telemetry row, feature grid, editor close-up, Notion/Confluence comparison, self-host terminal, cream testimonial moment, final CTA. Primary CTA = "Deploy On-prem" → `/docs/install`.
- `app/product/page.tsx` — Product (from `product.jsx`): four-section tour (Editor / Organization / Search / History) with demo components.
- `app/pricing/page.tsx` — Pricing (from `pricing.jsx`): Self-host / Cloud / Enterprise with monthly/yearly toggle, comparison table, FAQ. Tier data hardcoded in a local `tiers.ts` to be swapped for Stripe data later.

**Shared chrome:** port `chrome.jsx` (top nav + footer) + `icons.jsx` as React components. Wordmark from prototype.

**Deploy:** Cloudflare Pages project, point `marrow.so` apex + `www`. `app.marrow.so` remains the product (already tracked in #41).

**Verification:**
- `cd web-marketing && npm run dev`; all three routes render correctly at 1440px dark + light
- Lighthouse score >90 for performance on landing
- "Deploy On-prem" CTA href resolves to `/docs/install` (placeholder 404 is fine for now)
- Pricing tier copy matches the prototype exactly

### Follow-up issues to draft (Phase 2+)

Each to be created as a GitHub issue after plan approval:

1. **Backlinks** — parse wiki-links + `@` mentions on save; `page_links` table (`source_page_id`, `target_page_id`); `GET /api/pages/{pid}/backlinks`; populate right drawer. Phase 2 (before or alongside #40 sharing).
2. **Comments** — `comments` table (page-level + future block-level), `GET/POST /api/pages/{pid}/comments`, resolve/reply. Phase 2.
3. **Starred pages** — `user_stars` table (user_id, page_id), API, rail panel + `...` menu toggle. Phase 2 (small; bundle with member management).
4. **Inbox / notifications** — `notifications` table (mentions, comment replies, review requests), delivery on comment + @mention + share. Phase 2.
5. **Watch** — `page_watches` table, API, `...` menu toggle, triggers notifications. Phase 2 (depends on 4).
6. **Archive** — `archived_at` nullable on `pages`, filtered from tree/search, `...` menu action, unarchive from a future archived view. Phase 2.
7. **Settings screen** — new route hosting theme toggle (and later: account, security, API keys). Can be a small bundled issue or rolled into Phase 2 account work.

## Open Questions

- **Collaborator avatars in the editor header:** design shows stacked avatars (presence). Real presence is a #46 (Yjs) concern. Stub with workspace member avatars for now (show up to 3 workspace members sorted by last edit on this page if cheap; else static mock).
- **Starred / Inbox empty-state copy:** draft during Phase A PR; not blocking.
- **Monorepo tooling:** `web/` + `web-marketing/` can both run from root via npm workspaces, or stay independent. Leaning independent to avoid churn; revisit if duplication grows.

## Assumptions

- Design tokens in `web/app/globals.css` (from `docs/design-tokens.md` / issue #74) are already aligned with the prototype's `--color-base`, `--color-accent`, etc. Will audit during Phase A; small fixes may be needed.
- Fraunces is already loaded via `next/font` in `web/app/layout.tsx`; needs `SOFT` + `WONK` variable axes enabled.
- Existing `searchWorkspace()` API client function can power the rail Search panel with minimal changes.
- `cd api && pytest` and `cd web && npm test` remain green throughout — no API contract changes in this work.

## Technical Notes

- **Prototype location:** extracted to `/tmp/marrow-design/marrow/project/`. Source JSX files are the reference; copy styling values exact, not structure.
- **App UI main reference:** `/tmp/marrow-design/marrow/project/src/app_ui.jsx` (886 lines). Contains `AppRail`, `AppSidebar`, `EditorPane`, `PageMenu`, `SideDrawer`, `CommentsDrawer`, `Block`, `WikiLink`, `Backlinks`, `History`, `Comments`.
- **Marketing references:** `landing.jsx` (687 lines), `product.jsx` (371), `pricing.jsx` (331), `chrome.jsx` (225), `icons.jsx` (99).
- **Existing patterns to reuse:**
  - `apiFetch<T>()` in `web/lib/api.ts` — all API calls
  - `searchWorkspace()` — rail Search panel
  - `listRevisions()` — History drawer
  - `next-themes` provider already in root layout for theme
  - BlockNote `@` mention / page link infrastructure — already wired; just restyle
- **Token palette (dark):** `--color-base #111318`, `--color-surface #1a1d27`, `--color-surface-elevated #222636`, `--color-border #2d3348`, `--color-text-primary #e2e8f0`, `--color-text-secondary #94a3b8`, `--color-text-muted #475569`, `--color-accent #e8805c`, `--color-accent-ink #1a0f0a`, `--color-destructive #dc2626`, `--color-warning #d4900a`, `--color-success #34d399`, `--color-cream #f5ecd9`, `--color-bone #ece3d0`.
- **Delete list:** `web/components/search-dialog.tsx`, any Cmd+K dialog refs in `app-sidebar.tsx` and workspace layout.
