from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from ui_design_studio.project_cleanup import CleanupError, cleanup_project


class ProjectCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".omp/skills/ui-design-studio").mkdir(parents=True)
        (self.root / ".omp/skills/ui-design-studio/SKILL.md").write_text("old skill\n")
        (self.root / ".omp/agents").mkdir(parents=True)
        (self.root / ".omp/agents/ui-reviewer.md").write_text("old agent\n")
        (self.root / "tools").mkdir()
        (self.root / "tools/ui-design").write_text("old wrapper\n")
        (self.root / "ui-design-studio.json").write_text('{"custom": true}\n')
        (self.root / "AGENTS.md").write_bytes(b"before\n<!-- ui-design-studio:start -->\nold\n<!-- ui-design-studio:end -->\nafter\n")
        (self.root / ".gitignore").write_bytes(b"before\n# ui-design-studio:start\nold\n# ui-design-studio:end\nafter\n")
        (self.root / ".ui-design-studio/runtime").mkdir(parents=True)
        (self.root / ".ui-design-studio/runtime/active.json").write_text("live\n")
        (self.root / ".ui-design-studio/backups/old").mkdir(parents=True)
        (self.root / ".ui-design-studio/backups/old/manifest.json").write_text("backup\n")
        (self.root / ".ui-design-studio/install-state.json").write_text(json.dumps({
            "package": "ui-design-studio",
            "managedFiles": {
                ".omp/skills/ui-design-studio/SKILL.md": self.record(self.root / ".omp/skills/ui-design-studio/SKILL.md"),
                ".omp/agents/ui-reviewer.md": self.record(self.root / ".omp/agents/ui-reviewer.md"),
                "tools/ui-design": self.record(self.root / "tools/ui-design"),
            },
        }))
        (self.root / ".venv-ui-design/bin").mkdir(parents=True)
        (self.root / ".venv-ui-design/bin/python").write_text("venv\n")

    @staticmethod
    def record(path: Path) -> dict[str, object]:
        return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": 0o644}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dry_run_preserves_project(self) -> None:
        result = cleanup_project(self.root, apply=False, purge_backups=False)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["applied"])
        self.assertTrue((self.root / ".omp/skills/ui-design-studio/SKILL.md").exists())
        self.assertTrue((self.root / ".ui-design-studio/runtime/active.json").exists())

    def test_apply_removes_payload_and_preserves_mcp_data(self) -> None:
        result = cleanup_project(self.root, apply=True, purge_backups=False)
        self.assertTrue(result["applied"])
        self.assertFalse((self.root / ".omp/skills/ui-design-studio/SKILL.md").exists())
        self.assertFalse((self.root / ".omp/agents/ui-reviewer.md").exists())
        self.assertFalse((self.root / "tools/ui-design").exists())
        self.assertFalse((self.root / ".venv-ui-design").exists())
        self.assertFalse((self.root / ".ui-design-studio/install-state.json").exists())
        self.assertTrue((self.root / ".ui-design-studio/runtime/active.json").exists())
        self.assertTrue((self.root / ".ui-design-studio/backups/old/manifest.json").exists())
        self.assertTrue((self.root / "ui-design-studio.json").exists())
        self.assertNotIn(b"ui-design-studio:start", (self.root / "AGENTS.md").read_bytes())
        self.assertNotIn(b"ui-design-studio:start", (self.root / ".gitignore").read_bytes())

    def test_edited_managed_file_blocks_cleanup(self) -> None:
        (self.root / "tools/ui-design").write_text("local edit\n")
        result = cleanup_project(self.root, apply=True, purge_backups=False)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertTrue((self.root / "tools/ui-design").exists())

    def test_unowned_nested_file_is_preserved(self) -> None:
        extra = self.root / "docs/ui-design-studio/user-note.md"
        extra.parent.mkdir(parents=True)
        extra.write_text("keep\n")
        result = cleanup_project(self.root, apply=True, purge_backups=False)
        self.assertTrue(result["applied"])
        self.assertTrue(extra.exists())

    def test_mode_change_blocks_cleanup(self) -> None:
        path = self.root / "tools/ui-design"
        path.chmod(0o755)
        result = cleanup_project(self.root, apply=True, purge_backups=False)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertTrue(path.exists())

    def test_unsafe_state_path_is_rejected(self) -> None:
        state = self.root / ".ui-design-studio/install-state.json"
        state.write_text(json.dumps({"package": "ui-design-studio", "managedFiles": {"../../outside": {}}}))
        with self.assertRaisesRegex(CleanupError, "Unsafe managed path"):
            cleanup_project(self.root, apply=False, purge_backups=False)

    def test_purge_backups_is_explicit(self) -> None:
        result = cleanup_project(self.root, apply=True, purge_backups=True)
        self.assertTrue(result["applied"])
        self.assertFalse((self.root / ".ui-design-studio/backups").exists())


if __name__ == "__main__":
    unittest.main()
