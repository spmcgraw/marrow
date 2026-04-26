---
title: Restore guarantee
description: The architectural foundation of Marrow.
---

> A Marrow export bundle must always be restorable to an exact replica of the original workspace.

This is the single non-negotiable promise Marrow makes. Every other architectural decision flows from it.

## Why this matters

Most knowledge bases give you an "export" feature that's really a one-way escape hatch — half-broken Markdown, no metadata, no fidelity. The implicit message is: *this data lives here; if you ever leave, you'll lose something.*

Marrow inverts that. Your data is always portable, always whole. You can:

- Move from one Marrow instance to another with no fidelity loss.
- Back up your workspace as a single zip file.
- Inspect the bundle by hand — it's plain Markdown and JSON.
- Restore from a backup taken months earlier, on a different version of Marrow, and trust that the result is the same workspace.

## How the guarantee is enforced

### 1. Append-only revisions

Every save creates a new row in the `revisions` table. Existing revisions are never modified. This is enforced by a PostgreSQL trigger (`revisions_immutable()`) that raises an exception on any `UPDATE` against the table. A migration that removes this trigger is a critical bug.

### 2. Transparent bundle format

Bundles are zip files containing Markdown, JSON, and a `manifest.json`. No proprietary serialization. See [Export bundle format](/concepts/export-format/) for the layout.

### 3. The round-trip test

`api/tests/test_round_trip.py` is a regression anchor: it creates a workspace with multiple spaces, collections, pages, revisions, and attachments, exports it, wipes the database, restores from the bundle, and verifies the result is byte-equivalent to the original. This test must pass at all times. It runs in CI on every change.

### 4. Legacy bundle compatibility

`marrow restore` accepts bundles from earlier Marrow versions, including bundles produced before the project was renamed (the `freehold-export-*.zip` filename prefix is still recognized). The restore guarantee is a forward promise — old bundles must continue to restore on new versions.

## What this rules out

The guarantee imposes constraints contributors should be aware of:

- **No silent migrations** of revision content. If revision data needs reformatting, it happens at read time, not by editing rows.
- **No proprietary blobs** in the export bundle. Every value must be representable in plain text or standard formats.
- **No hidden state.** Attachments live in the bundle. Search indices are derived state and rebuilt on restore.
- **No "this only works in v1.0+" features.** Adding capability is fine; breaking restore for any older bundle is not.

If you're proposing a change that conflicts with the restore guarantee, the change is wrong.
