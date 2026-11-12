"""Focused installer coverage for the optional native progress adapter payload."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ui_design_progress_install_test", PACKAGE / "scripts/install.py")
INSTALL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = INSTALL
SPEC.loader.exec_module(INSTALL)
EXTENSION = ".omp/extensions/ui-design-progress.ts"


class ProgressInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="progress installer ")
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name)
        for name in INSTALL.SKILLS:
            directory = self.package / ".omp/skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text("Fixture skill\n", encoding="utf-8")
        studio = self.package / ".omp/skills/ui-design-studio/scripts/studio.py"
        studio.parent.mkdir()
        studio.write_text("print('fixture')\n", encoding="utf-8")
        agents = self.package / ".omp/agents"
        agents.mkdir()
        (agents / "ui-reviewer.md").write_text("Fixture agent\n", encoding="utf-8")
        commands = self.package / ".omp/commands"
        commands.mkdir()
        for name in ("ui-design", "ui-yolo"):
            (commands / f"{name}.md").write_text("Fixture command\n", encoding="utf-8")
        tools = self.package / "tools"
        tools.mkdir()
        (tools / "ui-design").write_text("#!/bin/sh\n", encoding="utf-8")
        self.patch = mock.patch.object(INSTALL, "PACKAGE", self.package)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_fixture_without_extensions_keeps_working(self):
        payload = INSTALL.source_files()
        self.assertNotIn(EXTENSION, payload)
        self.assertIn(".omp/skills/ui-design-studio/scripts/studio.py", payload)
        self.assertEqual(payload["tools/ui-design"][1], 0o755)

    def test_ships_only_the_explicit_extension_with_plain_file_mode(self):
        extension = self.package / EXTENSION
        extension.parent.mkdir()
        extension.write_bytes(b"export default function progress() {}\n")
        (extension.parent / "unrelated.ts").write_text("User extension\n", encoding="utf-8")
        payload = INSTALL.source_files()
        self.assertEqual(payload[EXTENSION], (b"export default function progress() {}\n", 0o644))
        self.assertNotIn(".omp/extensions/unrelated.ts", payload)

    def test_refuses_symlinked_extension_and_parent(self):
        outside = self.package / "outside"
        outside.mkdir()
        target = outside / "ui-design-progress.ts"
        target.write_text("Preserve this file\n", encoding="utf-8")
        extension = self.package / EXTENSION
        extension.parent.mkdir()
        extension.symlink_to(target)
        with self.assertRaises(INSTALL.InstallError):
            INSTALL.source_files()
        extension.unlink()
        extension.parent.rmdir()
        extension.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(INSTALL.InstallError):
            INSTALL.source_files()
        self.assertEqual(target.read_text(), "Preserve this file\n")

    def test_managed_ignore_hides_capabilities_not_durable_artwork(self):
        before = b"# User-owned ignore rule\nlocal-only.txt\n"
        after = INSTALL.marked_block(before, INSTALL.IGNORE_START, INSTALL.IGNORE_END, INSTALL.IGNORE_BLOCK)
        self.assertTrue(after.startswith(before))
        self.assertIn(b"**/.design-server.json\n", after)
        self.assertIn(b"**/.design-status.json\n", after)
        self.assertIn(b"/.ui-design-studio/runtime/mcp/\n", after)
        self.assertNotIn(b"artwork-library", after)
        self.assertNotIn(b"progress-pi-tasks", after)
        self.assertEqual(INSTALL.marked_block(after, INSTALL.IGNORE_START, INSTALL.IGNORE_END, INSTALL.IGNORE_BLOCK), after)


if __name__ == "__main__":
    unittest.main()
