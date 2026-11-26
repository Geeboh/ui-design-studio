# PRISM Studio 2.0.0

PRISM Studio 2.0.0 keeps the `ui-design-studio` package and CLI aliases. It adds a transactional local core behind the existing CLI, MCP, and authenticated dashboard adapters.

## What changed

- SQLite state uses `foreign_keys=ON`, `journal_mode=DELETE`, `synchronous=FULL`, and a 5-second busy timeout.
- Commands use typed envelopes, structured errors, expected revisions, idempotency receipts, events, and an outbox.
- Artifacts use SHA-256 content-addressed blobs. Corrupt bytes are rejected.
- Copy-first migration records source inventories, backups, deterministic mappings, checkpoints, activation journals, and rollback conflicts.
- Approval rules normalize optional human Approved feedback and exclude unrelated progress metadata from applicability fingerprints.
- Annotation and focused revision contracts pin normalized image coordinates, exact base digests, and annotation revisions.
- Component graphs reject cycles and ownership conflicts. Batch evaluation retains per-item outcomes.
- Budget, model, worker, lease, and provider reconciliation primitives preserve exact currency, actual assignments, bounded ownership, fencing, and unknown exposure.
- Dashboard drafts persist locally across reloads without storing bearer tokens.
- Product version is `2.0.0`; existing `ui-design-mcp`, `ui-design`, `ui-design-studio`, and `ui-design-studio-mcp` names remain available.
- Core and web receipts are retained under `.prism-state/evidence/`. They must be rerun after any source change.
- Dashboard browser regression: 10 tests passed in Chromium. The standalone OMP host regression remains blocked with 17 failures out of 52 tests.
- Source ZIP, sdist, and wheel were built under `dist/prism-v2`. Exact final hashes are in `.prism-state/release-artifacts.txt`.
- Wheel built from the extracted sdist matched the direct wheel hash. The source ZIP extracted outside the checkout without private runtime paths.
- Release profile is intentionally blocked by the open OMP host finding in `docs/PRISM-2.0.0-HANDOFF.md`.
The release profile is blocked until the OMP host regression passes. Human participant research remains deferred by project policy. Native and offline targets remain undeclared.
