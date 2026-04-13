# Freehold Design Tokens

Freehold's visual identity inherits from the Weald Labs design system. This doc covers what contributors need to build consistent UI. Full brand guidelines live in the private Weald Labs repo.

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

### Freehold Accent

| Token | Dark | Light | Usage |
| --- | --- | --- | --- |
| `--color-accent` | `#34d399` | `#059669` | Buttons, links, focus rings, active states |

Use `#34d399` in dark mode. Use `#059669` in light mode where WCAG 4.5:1 contrast is required against `#dde3ee` backgrounds.

### Semantic

| Token | Value | Usage |
| --- | --- | --- |
| `--color-destructive` | `#e05c6a` | Delete actions, error states |
| `--color-warning` | `#d4900a` | Caution states, non-blocking warnings |
| `--color-success` | `#34d399` | Confirmations, success states |

---

## Typography

| Role | Typeface | Source |
| --- | --- | --- |
| Headings | **Satoshi** | [Fontshare](https://www.fontshare.com/fonts/satoshi) — free, commercial license |
| Body / UI | **Inter** | Bundled via Blocknote |

**Rules:**

- Satoshi for H1–H4, display text, and marketing headlines only
- Inter for all body copy, UI labels, captions, and form elements
- Never use Satoshi for body copy or inline UI text

---

## Dark Mode

Dark mode is the primary design target. Light mode is fully supported — not an afterthought.

Design dark-first. Both modes must be tested before a UI contribution is considered complete.

---

## Theming

Implement tokens as CSS custom properties on `:root` with a `[data-theme="light"]` override, or use your framework's equivalent theming mechanism. Token names stay the same across both modes — only values swap.
