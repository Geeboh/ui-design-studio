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

## Verification

- Core gate receipt: `.prism-state/evidence/20261126T010711Z-57e58bc115/receipt.json`.
- Core profile: G0 through G4 passed with an unchanged source fingerprint.
- Dashboard browser regression: 10 tests passed in Chromium.
- Source ZIP, sdist, and wheel were built under `dist/prism-v2`. Exact hashes are in `.prism-state/release-artifacts.txt`.
- Wheel built from the extracted sdist matched the direct wheel hash.
- The source ZIP extracted outside the checkout without private runtime paths.

The release receipt covers current core and dashboard evidence. It does not claim the final G5 through G8 release profile until those commands are bound and run.

Human participant research remains deferred by project policy. Native and offline targets remain undeclared.
