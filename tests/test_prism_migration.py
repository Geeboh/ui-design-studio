from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ui_design_studio.migration import MigrationConflict, MigrationError, MigrationManager, MigrationPhase

class MigrationTests(unittest.TestCase):
    def make_manager(self):
        temporary = tempfile.TemporaryDirectory(prefix="prism-migration-")
        root = Path(temporary.name)
        source = root / "source"
        source.mkdir()
        (source / "run.json").write_text('{"schemaVersion":"1.0","status":"pending"}', encoding="utf-8")
        (source / "broken.json").write_text("{broken", encoding="utf-8")
        return temporary, root, source, MigrationManager(source, root / "candidate", root / "backup")

    def test_copy_first_import_quarantines_unknown_and_retries_without_duplicates(self):
        temporary, root, source, manager = self.make_manager()
        self.addCleanup(temporary.cleanup)
        original = {path.name: path.read_bytes() for path in source.iterdir()}
        receipt = manager.inventory("migration-1")
        backed = manager.backup(receipt)
        imported = manager.import_records(backed)
        validated = manager.validate(imported)
        resumed = manager.import_records(imported)
        self.assertEqual(validated.phase, MigrationPhase.VALIDATED)
        self.assertEqual(len(resumed.mappings), len(imported.inventory))
        self.assertIn("malformed_json_preserved_as_unknown", {finding["reason"] for finding in validated.findings})
        self.assertEqual(original, {path.name: path.read_bytes() for path in source.iterdir()})

    def test_rollback_rejects_divergent_candidate_writes(self):
        temporary, root, source, manager = self.make_manager()
        self.addCleanup(temporary.cleanup)
        active = manager.activate(manager.validate(manager.import_records(manager.backup(manager.inventory("migration-1")))))
        changed = manager.mark_candidate_write(active)
        with self.assertRaises(MigrationConflict):
            manager.rollback(changed)
        self.assertTrue(manager.locator_path.is_file())
    def test_migration_id_rejects_traversal_and_unicode(self):
        temporary, root, source, manager = self.make_manager()
        self.addCleanup(temporary.cleanup)
        for migration_id in ("../outside", "/absolute", "e\u0301", "x" * 129):
            with self.assertRaises(MigrationError):
                manager.inventory(migration_id)

    def test_migration_roots_reject_symlink_ancestors(self):
        temporary, root, source, manager = self.make_manager()
        self.addCleanup(temporary.cleanup)
        outside = root / "outside"
        outside.mkdir()
        link = root / "linked"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(MigrationError):
            MigrationManager(source, link / "candidate", root / "backup-2")

    def test_rollback_validates_backup_before_changing_locator(self):
        temporary, root, source, manager = self.make_manager()
        self.addCleanup(temporary.cleanup)
        receipt = manager.inventory("migration-2")
        backed = manager.backup(receipt)
        imported = manager.import_records(backed)
        active = manager.activate(manager.validate(imported))
        manifest = manager.backup_root / active.migration_id / "backup-manifest.json"
        manifest.write_text("corrupt\n", encoding="utf-8")
        with self.assertRaises(MigrationError):
            manager.rollback(active)
        self.assertTrue(manager.locator_path.is_file())


if __name__ == "__main__":
    unittest.main()
