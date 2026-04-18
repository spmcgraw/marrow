# Freehold → Marrow Rename & Rebrand — PRD

## Context

Freehold is being renamed to **Marrow**, with domain `marrow.so` (purchased via Namecheap). Marrow becomes the sole product and the sole business entity — Weald Labs is dissolved as a brand before it was ever set up beyond the domain purchase. This PRD captures the full scope: code rename, brand doc expansion in `docs/design-tokens.md`, Cloudflare + DNS configuration, and migration of existing local installs. The rename happens *before* v0.1.0 ships (#52 still open), so there are no external users to migrate.

## Goals

- Every `freehold`/`Freehold`/`FREEHOLD` reference in code, docs, config, and GitHub metadata replaced with `marrow`/`Marrow`/`MARROW`.
- GitHub repo renamed `spmcgraw/freehold` → `spmcgraw/marrow` (GitHub auto-redirects old URLs).
- `docs/design-tokens.md` expanded into a full public-facing brand doc covering color, typography, voice & tone, logo usage, and marketing palette — Weald Labs references removed.
- `marrow.so` delegated to Cloudflare nameservers with split-host layout wired up: `marrow.so` (marketing), `app.marrow.so` (Next.js app), `api.marrow.so` (FastAPI).
- Cloudflare Email Routing live so `@marrow.so` addresses work.
- Issue #41 updated to reference `marrow.so` hostnames and the terracotta/warm brand direction where relevant.
- Existing local install exported, renamed, restored — dogfooding the restore guarantee as the migration mechanism.

## Non-goals

- Logo and wordmark *design* — placeholders only. Asset production happens outside this PRD.
- Outbound transactional email (Resend/Postmark). Deferred until login/auth flows need it.
- Tier-(c) full brand system (motion, illustration, social templates). Deferred to the Marrow company workspace once dogfooded.
- Alembic migration *filenames* — kept as historical artifacts. Content inside migrations is untouched unless it references identifiers being renamed (see Technical Notes).
- Renaming the Weald Labs domain — let it expire or 301 to `marrow.so` later. Out of scope here.
- Per-space/per-collection RBAC changes, RLS work, or other #41 acceptance criteria that are not rename-driven.

## Design Decisions

### Rename scope
**Decision:** Total rename. All code identifiers, Python package (`api/freehold/` → `api/marrow/`), CLI command (`freehold` → `marrow`), env var prefixes, DB name, DB user, session cookie (`freehold_session` → `marrow_session`), storage path defaults, GitHub repo, README, CLAUDE.md, tests, and all user-facing strings.
**Why:** Pre-v0.1.0 means no users to migrate. The cost of a half-rename grows monotonically with every new feature; cost now is the floor. Half-rename states (`freehold_session` cookie on `marrow.so` domain) embarrass contributors.
**Rejected:** Cosmetic-only rename (leaves code identifiers stale, causes confusion on every onboarding). Staged rename over multiple PRs (risk of inconsistent intermediate states in `main`).

### Business entity
**Decision:** Full rebrand to Marrow. Weald Labs is not incorporated and has no contracts, banking, or IP — only a domain. Kill the name everywhere.
**Why:** Solo founder, one product. A parent/holding brand earns its keep only when it houses multiple products or has legal complexity. Neither applies. Explaining the Weald Labs → Marrow relationship would be a recurring tax.
**Rejected:** Weald Labs as holding + Marrow as product (overhead with no payoff at this stage). LLC-carveout variant — moot because the entity was never registered.

### Brand doc scope
**Decision:** Tier (b) — tokens + voice/tone + logo usage + marketing palette — in the public `docs/design-tokens.md` (may be renamed `docs/brand.md`). Tier (c) — full brand system with motion, illustration, social templates — lives inside Marrow (the product) in a company workspace once the app is usable for the founder.
**Why:** Voice/tone and logo rules are needed immediately for landing page, social, and docs tone. Public repo is the right home for anything contributors need. Tier (c) is internal, evolving, and a perfect recursive dogfooding use case for Marrow itself.
**Rejected:** Tier (a) tokens-only (leaves voice/tone unspecified, guarantees inconsistent copy). Tier (c) in the public repo (overkill for v0.1, treats brand as finished when it's still being discovered).

### Logo / wordmark direction
**Decision:** Wordmark-forward, with the "inside" concept baked into a single letter of the wordmark. Icon is derived from that glyph so the whole system is coherent: wordmark in header, glyph as favicon, glyph-in-a-square for OG/social.
**Why:** At solo-founder scale the wordmark gets ~10× more use than an icon, so that's where investment lands. Derived glyph yields favicon/app-icon for free. Avoids the anatomical-literal trap (cross-section-of-bone) and the generic "dot in a circle" startup-logo trap. The name "Marrow" is already evocative; the mark shouldn't illustrate it.
**Rejected:** Anatomical/literal marrow imagery (medical/visceral vibes). Abstract-only "inner structure" mark (generic, crowded). Icon-first branding (under-used at this scale).

### Tone (warm vs. sharp)
**Decision:** Warm — humanist, editorial, leaning away from the dev-tool sharp-geometric pack.
**Why:** Marrow's core value prop is *longevity and durability* (the restore guarantee). Warm humanist type signals "built to last"; sharp geometric type signals "shipped this quarter." The dev-tool aesthetic (Linear, Vercel, Cal, Resend) is saturated in 2026 — being another entry makes Marrow forgettable. The *name* "Marrow" is already warm; fighting it with cold type creates dissonance. The product is closer to Obsidian / iA Writer / Bear than to Linear / Vercel.
**Rejected:** Sharp geometric (crowded field, wrong emotional register). Warm + sharp tension (hard to execute without a designer, often reads as inconsistent).

### Typography
**Decision:** **Fraunces** for display/headings, **Inter** for UI and body.
**Why:** Fraunces is SIL OFL (safe for public repo + future commercial use), has optical sizes (one family covers display + serif body), and variable SOFT/WONK axes give Marrow a distinctive identity lever. Inter is already in the stack via BlockNote and is the right choice for long-form reading UI. Two-family system where Fraunces does brand/editorial work and Inter does the product chrome.
**Rejected:** Satoshi (current — sharp geometric, wrong direction post-rebrand). GT Super / Tiempos (premium quality but unnecessary cost for v0.1). Newsreader, Source Serif 4 (solid but less distinctive than Fraunces).

### Accent color
**Decision:** Terracotta. Dark mode `--color-accent: #e8805c` (contrast 5.4:1 on `#111318`). Light mode `--color-accent: #9a3412` (contrast 8.4:1 on `#dde3ee`). Both clear WCAG AA. Shift `--color-destructive` from `#e05c6a` to a deeper red (`#dc2626`-ish) to keep it distinct from the new warm accent.
**Why:** Terracotta is distinctive in the dev-tool/PKM space (no one is using it), pairs beautifully with warm humanist type, is a 5,000-year-old pigment (on-brand for "built to last"), and avoids the blood-marrow literalism that oxblood would invite. Warm accent on cool-undertone dark background creates strong warm/cool tension — a good thing. Lighter shade in dark mode matches existing token pattern (emerald currently uses `#34d399` dark / `#059669` light).
**Rejected:** Amber/ochre (safe but generic, Obsidian-adjacent). Oxblood (too-literal marrow/blood imagery). Warm gold (premium but feels luxury-brand). Keeping emerald (cool + bright, fights warm direction).

### Voice & tone
**Decision:** Baseline **quiet expert** — calm, declarative, understated, few adjectives. One flash of **literary/considered** per page, used as accent. First person sparingly, only in clearly authored contexts (founder notes, changelog).
**Why:** The product sells *durability*; a loud voice contradicts the promise. Quiet expert scales to error messages, empty states, and docs without rewriting. Literary flourishes give the brand warmth and memorability, but overused they become precious. Pure first-person "indie solo-founder" voice traps every update into sounding personal — doesn't age well if the company grows or the founder steps back.
**Rejected:** Pure literary (precious at scale). Pure plainspoken/first-person (doesn't scale). Sharp/tool-voice (contradicts longevity positioning).

### Hostname layout
**Decision:** Split hosts on `marrow.so`:
- `marrow.so` → marketing site (Cloudflare Pages, static, long cache TTLs)
- `app.marrow.so` → Next.js product app (Cloudflare Pages, dynamic)
- `api.marrow.so` → FastAPI (Cloudflare Containers)

Session cookie domain set to `.marrow.so` so the session works across `app.` and `api.`.
**Why:** Clean separation of audiences (public, users, infra), different caching profiles, different change cadences. Parent-domain cookie mirrors the current dev-mode pattern (`COOKIE_DOMAIN=localhost` shared between `:3000` and `:8000`). Easier to swap any one piece later without touching the others. Matches the intent of issue #41.
**Rejected:** Combined app + marketing on `marrow.so` (forces caching compromises). Single host with Next.js proxying to internal Container (couples deploy lifecycles, harder to debug, limits marketing caching).

### DNS & email
**Decision:** Full Cloudflare nameserver delegation from Namecheap. Cloudflare Email Routing enabled for `@marrow.so` forwarding to the founder's existing inbox. No outbound sending now.
**Why:** Full delegation unlocks Cloudflare's product surface (Pages custom domains, Workers routes, Email Routing, DDoS, analytics). Namecheap's DNS is strictly worse and gated behind their UI. Email Routing is free, zero-maintenance, and produces a real `@marrow.so` address before anyone asks. Outbound sending isn't needed until login/password-reset/transactional flows exist — none of which ship in v0.1.
**Rejected:** Keep DNS at Namecheap with CNAMEs pointing at Cloudflare (gives up the free product surface for no gain). Set up outbound email now (premature — no flows need it).

### Existing-install migration
**Decision:** Export the current local workspace with `freehold export`, perform the rename across the repo, re-init with the new `marrow` CLI, then `marrow restore` the bundle.
**Why:** This is precisely what the restore guarantee is for. Dogfooding it *during* the rename surfaces any bug before v0.1.0 ships. No additional migration tooling needed. A failing round-trip is a critical bug that blocks the rename — which is correct: that's exactly the bug you'd want to catch early.
**Rejected:** Rename-in-place DB migration (extra code for a one-shot operation with no users). Skip migration entirely (loses local test data — workable but wasteful).

## Open Questions

- **Logo / wordmark asset production.** The direction is locked (wordmark-forward, "inside" concept in one glyph, warm/humanist, likely derived from Fraunces or a Fraunces-adjacent custom cut). Actual design work is out of scope here. Blocks: finalizing the brand doc's Logo Usage section — ship with a TODO placeholder, fill in when assets exist.
- **`docs/design-tokens.md` → `docs/brand.md` rename.** Filename change is low-stakes. Defer until the brand doc expansion lands; rename then if the scope of the file has clearly outgrown the original "tokens" framing. Blocks: nothing.
- **Weald Labs domain disposition.** Let expire vs. 301 redirect to `marrow.so` vs. park. Not a blocker for this rename. Revisit before the domain renewal date.
- **Outbound email provider (Resend, Postmark, SES).** Deferred until auth/transactional flows land. Blocks: nothing now; blocks any future feature that sends email.

## Assumptions

- GitHub's automatic redirect for renamed repositories is reliable enough that existing clones, issue links, and PR links keep working without a manual backfill.
- `marrow.so` is available to transfer to Cloudflare nameservers — no Namecheap-side holds from the recent purchase.
- Cloudflare Email Routing supports `.so` TLDs (it supports arbitrary TLDs as long as MX can be set; `.so` has no known restrictions).
- Fraunces and Inter both render well across the OSes and browsers Marrow targets. (Known-good for modern Chromium/Firefox/Safari.)
- The existing `export`/`restore` round-trip passes on the current `main` before the rename starts. If `test_round_trip.py` is failing, the migration step in this PRD is blocked until it's fixed.
- Terracotta `#e8805c` / `#9a3412` holds up across all current UI surfaces (buttons, links, focus rings, active states). Will be validated during the token swap, not assumed indefinitely.

## Technical Notes

### Rename — concrete targets

- **Python package:** `api/freehold/` → `api/marrow/`. Update all `from freehold.` / `import freehold` across `api/main.py`, `api/tests/**`, `api/alembic/env.py`. `pyproject.toml` `[project.scripts]` entry `freehold = "freehold.cli:app"` → `marrow = "marrow.cli:app"`.
- **DB identifiers:** `docker-compose.yml` Postgres user/password/db all `freehold` → `marrow`. `DATABASE_URL` in `.env.example` updated. Port 5433 unchanged.
- **Env vars:** `API_KEY`, `SECRET_KEY`, `DATABASE_URL`, `STORAGE_PATH`, etc. — string-constant values may change but variable *names* are already generic; no rename needed. Check `CORS_ORIGINS`, `FRONTEND_URL`, `COOKIE_DOMAIN` sample values.
- **Session cookie:** `freehold_session` → `marrow_session` in `api/freehold/auth.py`. Cookie domain in production: `.marrow.so`.
- **Storage default:** `STORAGE_PATH=./storage` stays; gitignored `api/storage/` dir stays. No path-based `freehold` references expected — verify.
- **Frontend:** `web/proxy.ts`, `web/lib/api.ts`, `web/lib/types.ts`, `web/app/layout.tsx`, `web/app/login/page.tsx`, `web/components/restore-dialog.tsx`, `web/app/workspaces/page.tsx`, `web/components/app-sidebar.tsx` — 1–3 occurrences each. Mostly titles, page headers, copy strings.
- **Export bundle filenames:** `freehold-export-{slug}-{timestamp}.zip` → `marrow-export-{slug}-{timestamp}.zip` in `api/freehold/export.py`. Restore code in `api/freehold/restore.py` must continue to accept the legacy `freehold-export-*` filename prefix to keep old bundles restorable — this is a direct consequence of the restore guarantee.
- **Tests:** `api/tests/test_*.py` reference the package name in imports and the CLI name in subprocess calls. All must be updated in the same PR as the code rename; a split would leave tests broken on `main`.
- **Docs:** `README.md`, `CLAUDE.md`, `references/prd-freehold-roadmap.md` (→ `prd-marrow-roadmap.md`), `references/PR-50-instructions.md`. `CLAUDE.md` lives documentation — update alongside the rename.
- **GitHub repo:** `gh repo rename marrow`. Update any hardcoded `spmcgraw/freehold` URLs in docs. Auto-redirect handles inbound links.
- **Alembic migration files:** filenames kept as-is (historical artifacts). If any migration contains the literal string `freehold` in SQL (e.g., a schema or role reference), audit — expected to be none, since current migrations operate on tables like `pages`, `revisions`, etc.

### Critical files to modify

- `api/pyproject.toml` (package name, CLI entry)
- `api/freehold/` whole directory → `api/marrow/`
- `api/main.py` (re-exports from package)
- `api/freehold/auth.py` → `api/marrow/auth.py` (cookie name)
- `api/freehold/export.py`, `api/freehold/restore.py` (bundle filename prefix + restore tolerance for legacy prefix)
- `api/.env.example`, `api/.env`
- `docker-compose.yml` (DB name/user/password)
- `web/lib/api.ts`, `web/lib/types.ts`, `web/proxy.ts`, `web/app/layout.tsx`, `web/app/login/page.tsx`, `web/components/restore-dialog.tsx`, `web/app/workspaces/page.tsx`, `web/components/app-sidebar.tsx`
- `web/.env.local.example`
- `README.md`, `CLAUDE.md`, `references/prd-freehold-roadmap.md` (rename file too), `references/PR-50-instructions.md`
- `docs/design-tokens.md` — strip Weald Labs line, add Marrow brand sections (see below)
- All `api/tests/test_*.py` — import updates + CLI invocations

### `docs/design-tokens.md` expansion outline

Keep the existing Color / Typography / Dark Mode / Theming sections, with these changes and additions:

1. **Preamble** — replace line 3 ("inherits from the Weald Labs design system") with a one-sentence statement of Marrow's brand posture.
2. **Color tokens** — update Accent rows to terracotta values. Update Destructive to deeper red. Add a small Marketing palette table (1–2 supporting warm tones for landing-page accents, e.g., cream/bone as a light-mode section background).
3. **Typography** — swap Satoshi → Fraunces for headings. Note variable axes (SOFT, WONK) and how to use them. Inter stays for UI/body. Add a type scale (h1/h2/h3/body/small sizes + line heights) so contributors don't free-style.
4. **Logo usage** — new section. Placeholder note ("assets TBD"). Spell out the rules in advance: clearspace = cap height × 1, minimum size, approved backgrounds, don'ts (no stretching, no recoloring outside token palette, no icon without wordmark unless ≤ favicon size).
5. **Voice & tone** — new section. Capture the "quiet expert + literary flash" direction with 2–3 before/after examples (e.g., a bad error message vs. a Marrow-voice error message; a bad empty state vs. a Marrow-voice empty state).
6. **Dark mode first** — existing section; expand to call out that the warm accent was chosen specifically to hold up on the cool-undertone dark base, and that new tokens must clear WCAG AA in both modes.

### Cloudflare + DNS — step-by-step

1. **Cloudflare dashboard** → Add Site → enter `marrow.so` → Free plan. Cloudflare scans for existing DNS records (likely empty on a fresh purchase) and returns a pair of assigned nameservers (e.g., `ada.ns.cloudflare.com`, `bob.ns.cloudflare.com`).
2. **Namecheap dashboard** → Domain List → `marrow.so` → Manage → Nameservers → change from "Namecheap BasicDNS" to "Custom DNS" → paste both Cloudflare nameservers → Save. Propagation: minutes to 24 hours; usually under an hour.
3. Back in Cloudflare, wait for the site to show "Active" (email confirmation arrives).
4. **DNS records** (add via Cloudflare DNS tab):
   - `A` or `CNAME` for `marrow.so` → marketing Pages deployment target (Cloudflare Pages gives a `*.pages.dev` hostname; CNAME apex is supported via CNAME flattening).
   - `CNAME` `app` → app Pages deployment.
   - `CNAME` `api` → Cloudflare Containers hostname for the FastAPI service.
   - All three records set to **Proxied** (orange cloud) to get DDoS + caching.
5. **Custom domains on each Pages project:** in the Pages project settings, add the custom domain (`marrow.so`, `app.marrow.so`). Cloudflare auto-issues certs.
6. **Email Routing** → enable on `marrow.so` → accept the MX record additions → configure destination address (founder inbox) → add routes (`hello@`, `support@`, `sean@`, catch-all → inbox).
7. **Session cookie** (backend): set `COOKIE_DOMAIN=.marrow.so` in the production env. Verify the Set-Cookie header on `/api/auth/callback` shows `Domain=.marrow.so; Secure; HttpOnly; SameSite=Lax`.
8. **CORS**: `CORS_ORIGINS=https://app.marrow.so,https://marrow.so` in the API's production env.

### Issue #41 update

Edit the description of issue #41 to:
- Replace `Freehold` with `Marrow`, `freehold` with `marrow` where referenced.
- Replace generic deployment-target language with the locked hostname layout: `marrow.so` (Pages marketing), `app.marrow.so` (Pages app), `api.marrow.so` (Containers API).
- Add a line noting Cloudflare Email Routing is part of the SaaS environment bring-up.
- No acceptance-criteria changes needed — the shape of the work is unchanged; only names are.

## Verification

End-to-end checks to run before closing out the rename:

1. **Fresh clone, fresh install.** `git clone` the renamed repo, follow the updated setup steps in README.md + CLAUDE.md. Everything should work with no manual search-and-replace.
2. **Full test suite.** `cd api && pytest` passes, including `test_round_trip.py` (critical — it validates the restore guarantee). Frontend `npm test` + `npm run lint` + `npm run build` all pass.
3. **Dogfood migration.** Export the pre-rename local workspace, complete the rename, `marrow restore <bundle>`, verify the restored workspace is byte-identical in its content to the pre-rename state. This is also partially covered by `test_round_trip.py` but should be run against real local data too.
4. **Legacy bundle compatibility.** Restore a `freehold-export-*.zip` bundle with the new `marrow restore` CLI. Must succeed — this is the restore guarantee applied to the rename itself.
5. **Grep sweep.** `rg -i 'freehold|weald'` across the repo (excluding `.git/`, `node_modules/`, `.venv/`, and Alembic migration filenames) must return zero hits outside the `restore.py` legacy-prefix tolerance code.
6. **Brand doc review.** `docs/design-tokens.md` renders correctly on GitHub; every token value in the doc matches what `web/app/globals.css` (or wherever CSS custom props live) actually sets; voice & tone examples are in place.
7. **DNS.** `dig marrow.so NS` returns Cloudflare nameservers. `dig app.marrow.so` and `dig api.marrow.so` resolve. `curl https://marrow.so` returns 200 from the marketing Pages deploy. Email test: send a message to `hello@marrow.so`, confirm it lands in the founder inbox.
8. **Cookie + CORS.** On production, log in via OIDC. Verify `marrow_session` cookie is set with `Domain=.marrow.so`. Verify `app.marrow.so` can call `api.marrow.so` without CORS errors.
9. **GitHub redirects.** Hit the old `spmcgraw/freehold` URL in a browser, confirm it redirects to `spmcgraw/marrow`. Open an existing PR or issue by the old number — confirm it resolves.
