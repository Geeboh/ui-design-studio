from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ui_design_studio.knowledge import load_rules, select_rules
from ui_design_studio.theme_lifecycle import ThemeLifecycle, ThemeLifecycleError


class M6Tests(unittest.TestCase):
    def test_bounded_rule_selection_preserves_provenance(self):
        rules = load_rules(Path(__file__).resolve().parents[1] / ".prism-rebuild/knowledge/rules.json")
        selected = select_rules(rules, "worker packet bounded instructions", limit=4)
        self.assertTrue(selected)
        self.assertLessEqual(len(selected), 4)
        self.assertTrue(all(rule.source_ids for rule in selected))

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
