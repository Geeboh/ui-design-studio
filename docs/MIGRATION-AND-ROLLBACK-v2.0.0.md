# Migrate and roll back PRISM Studio 2.0.0

Use the migration manager for legacy run records. It never resets, stashes, cleans, or overwrites the source tree during inventory, backup, import, or validation.

## Create a migration

Keep the source, candidate, and backup roots separate.

```python
from ui_design_studio.migration import MigrationManager

manager = MigrationManager(
    source_root="/absolute/project",
    candidate_root="/absolute/state/prism-migrations/migration-1",
    backup_root="/absolute/state/prism-backups",
)
receipt = manager.inventory("migration-1")
receipt = manager.backup(receipt)
receipt = manager.import_records(receipt)
receipt = manager.validate(receipt)
receipt = manager.activate(receipt)
```

The receipt records the source inventory digest, backup manifest digest, deterministic mappings, checkpoints, quarantined findings, activation journal, and candidate write count. A retry with changed source bytes raises `MigrationConflict`. Malformed legacy records remain readable as quarantined unknowns. The migrator never invents approvals, costs, currencies, model assignments, or evidence.

## Roll back

Rollback restores the prior locator only when the active candidate has no later writes.

```python
receipt = manager.rollback(receipt)
```

After activation, mark candidate writes through the migration owner. A rollback with `candidateWrites > 0` raises `MigrationConflict`. Export or fork the candidate instead of overwriting later work.

The activation journal records `prepared`, `active`, and `restored` phases. Keep the source, backup, mapping, receipt, and referenced blobs until an explicit retention decision removes them.

## State and storage policy

Project authority lives in local state, not `.prism-state`. `.prism-state` holds ignored receipts and evidence. PRISM records the actual SQLite version and source ID. The portable tested policy uses the rollback journal with `synchronous=FULL`. Do not enable multi-connection WAL unless the runtime has the documented SQLite fix and the state path is local to one host.
