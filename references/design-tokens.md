# Marrow Design Tokens

Marrow is a self-hosted knowledge base built to last. This doc is the public source of truth for its visual and verbal identity — tokens, type, voice, and logo rules — so contributors can ship consistent UI and copy without asking.

---

## Color Tokens

### Base (Dark Mode / Light Mode)

| Token | Dark | Light | Usage |
| --- | --- | --- | --- |
| `--color-base` | `#111318` | `#dde3ee` | Page background |
| `--color-surface` | `#1a1d27` | `#eaeff7` | Cards, panels, sidebars |
| `--color-surface-elevated` | `#222636` | `#f4f6fb` | Dropdowns, modals, popovers |
| `--color-border` | `#2d3348` | `#c8d0e0` | Dividers, input borders |

### Text

| Token | Dark | Light | Usage |
| --- | --- | --- | --- |
| `--color-text-primary` | `#e2e8f0` | `#1e293b` | Body text, headings |
| `--color-text-secondary` | `#94a3b8` | `#64748b` | Captions, labels, metadata |
| `--color-text-muted` | `#475569` | `#94a3b8` | Placeholders, disabled states |

### Marrow Accent

| Token | Dark | Light | Usage |
| --- | --- | --- | --- |
| `--color-accent` | `#e8805c` | `#9a3412` | Buttons, links, focus rings, active states |

Terracotta, chosen for warmth against the cool-undertone base and for distinctiveness in the dev-tool / PKM space. `#e8805c` clears WCAG AA at 5.4:1 on `#111318`. `#9a3412` clears AA at 8.4:1 on `#dde3ee`.

### Semantic

| Token | Value | Usage |
| --- | --- | --- |
| `--color-destructive` | `#dc2626` | Delete actions, error states |
| `--color-warning` | `#d4900a` | Caution states, non-blocking warnings |
| `--color-success` | `#34d399` | Confirmations, success states |

Destructive is deeper than the accent so the two never read as the same color. Don't use the accent for destructive actions, and don't use destructive for anything non-destructive.

### Marketing Palette

Supporting warm tones for the landing site and external marketing surfaces. **Not** for product UI — the product runs on the tokens above.

| Token | Value | Usage |
| --- | --- | --- |
| `--color-cream` | `#f5ecd9` | Warm section background on the marketing site |
| `--color-bone` | `#ece3d0` | Section dividers, quiet cards, quoted pull-outs |

---

## Typography

| Role | Typeface | Source |
| --- | --- | --- |
| Headings / display | **Fraunces** | [Google Fonts](https://fonts.google.com/specimen/Fraunces) — SIL OFL |
| Body / UI | **Inter** | Bundled via BlockNote |

**Rules:**

- Fraunces for H1–H4, display text, marketing headlines, and pull quotes.
- Inter for all body copy, UI labels, captions, form elements, and code-adjacent chrome.
- Never use Fraunces for body copy or inline UI text.

**Variable axes (Fraunces):**

- `SOFT` (0–100) — softens terminals and junctions. Use higher values (50–100) on large editorial display sizes for a humanist feel. Keep at 0 for anything under ~32px.
- `WONK` (0 or 1) — enables alternate "wonky" glyphs (single-story g, curlier italics). Reserve for single-word marketing flashes; never set on body or repeated UI text.

### Type scale

Modular scale, 1.25 ratio, 1rem body. Sizes in rem, line-heights unitless.

| Role | Family | Size | Line height |
| --- | --- | --- | --- |
| h1 | Fraunces | 2.5rem | 1.1 |
| h2 | Fraunces | 2rem | 1.15 |
| h3 | Fraunces | 1.5rem | 1.25 |
| body | Inter | 1rem | 1.6 |
| small | Inter | 0.875rem | 1.5 |

---

## Dark Mode First

Dark mode is the primary design target. Light mode is fully supported — not an afterthought. Design dark-first; test both modes before a UI contribution is considered complete.

Marrow's accent is warm (terracotta) and the base is cool (near-black with blue undertones). That tension is deliberate — warm-on-cool gives the brand its character, and keeps the accent legible against the base in both modes.

Any new token must clear **WCAG AA contrast** (4.5:1 for body text, 3:1 for large text and UI components) in *both* dark and light modes before it lands.

---

## Logo Usage

> Wordmark and glyph assets TBD. Direction is locked (wordmark-forward, with the "inside" concept baked into a single letter; icon derived from that glyph). See the [Marrow Rename & Rebrand PRD](../references/prd-marrow-rename-rebrand.md) for the decision rationale.

When assets land, these rules apply:

- **Clearspace:** cap height × 1 on all four sides. No other element, including other brand marks, enters that box.
- **Minimum size:** glyph at 24px; wordmark at 96px. Below 24px use the favicon variant only.
- **Approved backgrounds:** `--color-base` (dark), `--color-base` (light), `--color-cream` (marketing only). Any other background needs a contrast check.
- **Don'ts:**
  - No stretching, rotating, or reflowing the mark.
  - No recoloring outside the token palette.
  - No icon without the wordmark above favicon size.
  - No drop shadows, outlines, glows, or bevels.
  - No placing the mark on a photograph or patterned background without a solid underlay.

---

## Voice & Tone

**Baseline: quiet expert.** Calm, declarative, understated. Short sentences. Few adjectives. Describe what happened, not how the user should feel about it.

**Accent: one literary flash per page.** A single considered phrase — a metaphor, a cadence, a word the reader won't see in other dev tools — used sparingly. Overused, it becomes precious. Used once, it lands.

**First person** only in clearly authored contexts — founder notes, changelog, blog posts. Never in UI strings, error messages, or docs.

Marrow's positioning is longevity. A loud voice contradicts the promise. The words should age the same way the product does.

### Before / after examples

**Error message**

> ❌ Before: *"Something went wrong! Please try again later."*
> ✅ After: *"Save failed. Your last change is still in the editor — try again when you're ready."*

**Empty state (no workspaces yet)**

> ❌ Before: *"You don't have any workspaces yet. Click below to create one!"*
> ✅ After: *"No workspaces yet. Start one — the shape of your notes comes later."*

**Destructive confirm**

> ❌ Before: *"Are you sure you want to delete this page? This action cannot be undone."*
> ✅ After: *"Delete this page. The revision history goes with it."*

---

## Theming

Implement tokens as CSS custom properties on `:root` with a `[data-theme="light"]` override, or use your framework's equivalent theming mechanism. Token names stay the same across both modes — only values swap.
