from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from ui_design_studio.knowledge import KnowledgeError, load_rules, select_rules
from ui_design_studio.theme_lifecycle import ThemeLifecycle, ThemeLifecycleError


class M6Tests(unittest.TestCase):
    def test_bounded_rule_selection_preserves_provenance(self):
        rules = load_rules(Path(__file__).resolve().parents[1] / ".prism-rebuild/knowledge/rules.json")
        selected = select_rules(rules, "worker packet bounded instructions", limit=4)
        self.assertTrue(selected)
        self.assertLessEqual(len(selected), 4)
        self.assertTrue(all(rule.source_ids for rule in selected))

    def test_source_informed_rule_requires_provenance(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "rules.json"
            path.write_text(
                '{"schemaVersion":"1.0.0","rules":[{"id":"r","topic":"topic","principle":"principle","appliesWhen":"when","action":"action","check":"check","authority":"source-informed-heuristic","sourceIds":[],"sourceLocators":{}}]}',
                encoding="utf-8",
            )
            with self.assertRaises(KnowledgeError):
                load_rules(path)

    def test_install_rolls_back_target_when_receipt_write_fails(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source"
            source.mkdir()
            (source / "theme.css").write_text("new", encoding="utf-8")
            target = root / "target"
            target.mkdir()
            (target / "theme.css").write_text("old", encoding="utf-8")
            lifecycle = ThemeLifecycle(root / "state")
            original_write_text = Path.write_text

            def fail_receipt(path, data, *args, **kwargs):
                if path.name == "theme-fail.json":
                    raise OSError("synthetic receipt failure")
                return original_write_text(path, data, *args, **kwargs)

            with mock.patch.object(Path, "write_text", fail_receipt):
                with self.assertRaises(OSError):
                    lifecycle.install(source, target, theme_id="fixture", scope="dashboard", receipt_id="theme-fail")
            self.assertEqual((target / "theme.css").read_text(encoding="utf-8"), "old")
            self.assertFalse((lifecycle.state_root / "theme-fail.previous").exists())

    def test_upgrade_activates_and_restore_clears_activation(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source"
            source.mkdir()
            target = root / "target"
            lifecycle = ThemeLifecycle(root / "state")
            (source / "theme.css").write_text("v1", encoding="utf-8")
            (source / "old.css").write_text("retired", encoding="utf-8")
            lifecycle.install(source, target, theme_id="fixture", scope="dashboard", receipt_id="theme-1")
            (target / "old.css").unlink()
            (target / "theme.css").write_text("consumer override", encoding="utf-8")
            (source / "theme.css").write_text("v2", encoding="utf-8")
            second = lifecycle.upgrade(source, target, theme_id="fixture", scope="dashboard", receipt_id="theme-2")
            active = (lifecycle.state_root / "active.json").read_text(encoding="utf-8")
            self.assertIn("theme.css", second.preserved_paths)
            self.assertIn("deleted:old.css", second.preserved_paths)
            self.assertEqual((target / "theme.css").read_text(encoding="utf-8"), "consumer override")
            lifecycle.restore(second)
            self.assertEqual((target / "theme.css").read_text(encoding="utf-8"), "consumer override")
            self.assertFalse((lifecycle.state_root / "active.json").exists())

    def test_theme_restore_refuses_divergent_target(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source"
            source.mkdir()
            (source / "theme.css").write_text(":root{}", encoding="utf-8")
            target = root / "target"
            lifecycle = ThemeLifecycle(root / "state")
            receipt = lifecycle.install(source, target, theme_id="fixture", scope="dashboard", receipt_id="theme-1")
            lifecycle.restore(receipt)
            self.assertFalse(target.exists())
            receipt = lifecycle.install(source, target, theme_id="fixture", scope="dashboard", receipt_id="theme-2")
            (target / "theme.css").write_text("changed", encoding="utf-8")
            with self.assertRaises(ThemeLifecycleError):
                lifecycle.restore(receipt)


if __name__ == "__main__":
    unittest.main()
