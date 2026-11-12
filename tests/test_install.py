"""Installer integration tests. Run inside a venv with unittest discovery."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PACK = Path(__file__).resolve().parents[1]
SKILLS = (
    "ui-design-studio", "ui-assess", "ui-plan", "ui-design", "ui-produce",
    "ui-review", "ui-finalize", "ui-theme", "ui-yolo",
)


def snapshot(root: Path, ignore_venv: bool = False) -> dict:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if ignore_venv and relative.startswith(".venv-ui-design/"):
            continue
        if path.is_file() and not path.is_symlink():
            result[relative] = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
        elif path.is_symlink():
            result[relative] = ("symlink", os.readlink(path))
    return result


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ui design installer test ")
        self.base = Path(self.temp.name)
        self.pack = self.base / "package with spaces"
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        for name in ("scripts", "tools", ".omp/agents", ".omp/commands", "docs", "prompts"):
            (self.pack / name).mkdir(parents=True)
        shutil.copy2(PACK / "scripts/install.py", self.pack / "scripts/install.py")
        shutil.copy2(PACK / "install.sh", self.pack / "install.sh")
        shutil.copy2(PACK / "tools/ui-design", self.pack / "tools/ui-design")
        for name in SKILLS:
            directory = self.pack / ".omp/skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Fixture\n---\nOriginal {name}\n")
        script = self.pack / ".omp/skills/ui-design-studio/scripts/studio.py"
        script.parent.mkdir()
        script.write_text("import sys\nfrom pathlib import Path\nprint('venv=' + str(sys.prefix != sys.base_prefix))\nprint('cwd=' + str(Path.cwd()))\nprint('args=' + repr(sys.argv[1:]))\n")
        (self.pack / ".omp/agents/ui-reviewer.md").write_text("---\nname: ui-reviewer\ndescription: Fixture\n---\nReview.\n")
        for name in ("ui-design", "ui-yolo"):
            (self.pack / f".omp/commands/{name}.md").write_text(f"---\ndescription: {name}\n---\n$ARGUMENTS\n")
        (self.pack / "README.md").write_text("Fixture README\n[Run types](docs/RUN-TYPES.md)\n[Prompt](prompts/START.md)\n")
        (self.pack / "LICENSE.txt").write_text("Synthetic package license\n")
        (self.pack / "release.json").write_text('{"version":"1.1.0"}\n')
        (self.pack / "docs/GUIDE.md").write_text("Fixture guide\n")
        (self.pack / "docs/RUN-TYPES.md").write_text("Fixture run types\n")
        (self.pack / "prompts/START.md").write_text("Fixture prompt\n")

    def tearDown(self):
        self.temp.cleanup()

    def run_install(self, *args, expected=0, shell=False):
        command = ["bash", str(self.pack / "install.sh")] if shell else [sys.executable, str(self.pack / "scripts/install.py")]
        result = subprocess.run(command + ["--project", str(self.project), *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def backups(self):
        return sorted((self.project / ".ui-design-studio/backups").glob("*/manifest.json"))

    def test_dry_run_no_target_mutations(self):
        (self.project / "AGENTS.md").write_bytes(b"Existing\r\nKeep exact trailing bytes")
        before = snapshot(self.project)
        result = self.run_install("--dry-run", shell=True)
        self.assertIn("No project files were changed", result.stdout)
        self.assertEqual(before, snapshot(self.project))
        self.assertFalse((self.project / ".venv-ui-design").exists())
        self.assertFalse((self.project / ".ui-design-studio").exists())

    def test_fresh_install_idempotent_and_wrapper_spaces(self):
        self.run_install(shell=True)
        config = json.loads((self.project / "ui-design-studio.json").read_text())
        self.assertNotIn("profile", config)
        self.assertEqual(config["modelPolicy"], "auto-models")
        self.assertEqual(config["paths"], {"runs": "docs/design/runs", "themes": "themes"})
        self.assertEqual(len(self.backups()), 1)
        initial = snapshot(self.project)
        result = self.run_install("--profile", "generic")
        self.assertIn("deprecated and ignored", result.stderr)
        self.assertIn("already installed", result.stdout)
        self.assertEqual(initial, snapshot(self.project))
        self.assertEqual(len(self.backups()), 1)
        wrapper = subprocess.run([str(self.project / "tools/ui-design"), "doctor", "two words"], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
        self.assertIn("venv=True", wrapper.stdout)
        self.assertIn("cwd=" + str(self.project), wrapper.stdout)
        self.assertIn("'two words'", wrapper.stdout)
        readme = (self.project / "docs/ui-design-studio/README.md").read_text()
        self.assertIn("](RUN-TYPES.md)", readme)
        self.assertIn("](prompts/START.md)", readme)
        self.assertTrue((self.project / "docs/ui-design-studio/RUN-TYPES.md").is_file())
        self.assertEqual((self.project / "docs/ui-design-studio/LICENSE.txt").read_text(), "Synthetic package license\n")
        self.assertEqual(json.loads((self.project / "docs/ui-design-studio/release.json").read_text())["version"], "1.1.0")

    def test_active_temporary_model_routing_blocks_update_without_mutating_files(self):
        self.run_install()
        active = self.project / ".ui-design-studio/model-routing/active.json"
        active.parent.mkdir()
        active.write_text('{"run":"synthetic-active-run"}\n')
        before = snapshot(self.project)
        result = self.run_install("--update", expected=1)
        self.assertIn("models-restore", result.stderr)
        self.assertEqual(snapshot(self.project), before)

    def test_deprecated_profile_does_not_add_project_constraints(self):
        result = self.run_install("--profile", "tada")
        self.assertIn("deprecated and ignored", result.stderr)
        config = json.loads((self.project / "ui-design-studio.json").read_text())
        self.assertNotIn("profile", config)
        self.assertNotIn("offlineRequired", config)

    def test_obsolete_managed_file_is_backed_up_and_restorable(self):
        source = self.pack / "docs/obsolete.md"
        source.write_text("Old generated profile documentation\n")
        self.run_install()
        target = self.project / "docs/ui-design-studio/obsolete.md"
        original = target.read_bytes()
        source.unlink()
        self.run_install(expected=1)
        self.assertEqual(target.read_bytes(), original)
        dry = self.run_install("--update", "--dry-run")
        self.assertIn("REMOVE docs/ui-design-studio/obsolete.md", dry.stdout)
        self.assertEqual(target.read_bytes(), original)
        self.run_install("--update")
        self.assertFalse(target.exists())
        manifest = next(json.loads(path.read_text()) for path in self.backups()
                        if any(entry["action"] == "remove" for entry in json.loads(path.read_text())["files"]))
        target.write_text("A later user file at the retired path\n")
        before = snapshot(self.project)
        self.run_install("--restore", manifest["backupId"], expected=1)
        self.assertEqual(snapshot(self.project), before)
        target.unlink()
        self.run_install("--restore", manifest["backupId"])
        self.assertEqual(target.read_bytes(), original)

    def test_edited_obsolete_managed_file_blocks_retirement(self):
        source = self.pack / "docs/obsolete.md"
        source.write_text("Original generated content\n")
        self.run_install()
        source.unlink()
        target = self.project / "docs/ui-design-studio/obsolete.md"
        target.write_text("User-maintained content\n")
        before = snapshot(self.project)
        result = self.run_install("--update", expected=1)
        self.assertIn("obsolete managed file was edited", result.stderr)
        self.assertEqual(snapshot(self.project), before)

    def test_unowned_conflict_preflight_no_partial_install(self):
        conflict = self.project / ".omp/skills/ui-theme/SKILL.md"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("Unrelated existing content\n")
        before = snapshot(self.project)
        self.run_install(expected=1)
        self.assertEqual(before, snapshot(self.project))
        self.run_install("--update", expected=1)
        self.assertEqual(before, snapshot(self.project))
        self.assertFalse((self.project / ".venv-ui-design").exists())

    def test_edited_managed_payload_blocks_update_before_any_changes(self):
        self.run_install()
        agent = self.project / ".omp/agents/ui-reviewer.md"
        agent.write_text(agent.read_text() + "User-maintained reviewer instructions\n")
        guide = self.pack / "docs/GUIDE.md"
        guide.write_text("Updated generated guide\n")
        (self.pack / "docs/NEW.md").write_text("New generated documentation\n")
        before = snapshot(self.project)
        result = self.run_install("--update", expected=1)
        self.assertIn("managed file was edited since installation", result.stderr)
        self.assertEqual(snapshot(self.project), before)
        self.assertFalse((self.project / "docs/ui-design-studio/NEW.md").exists())

    def test_changed_managed_mode_blocks_update_but_desired_state_is_idempotent(self):
        self.run_install()
        agent = self.project / ".omp/agents/ui-reviewer.md"
        agent.chmod(0o600)
        before = snapshot(self.project)
        result = self.run_install("--update", expected=1)
        self.assertIn("managed file was edited since installation", result.stderr)
        self.assertEqual(snapshot(self.project), before)
        agent.chmod(0o644)
        source = self.pack / ".omp/agents/ui-reviewer.md"
        desired = source.read_text() + "Updated package instructions\n"
        source.write_text(desired)
        agent.write_text(desired)
        # A file already matching the desired package is not overwritten or
        # falsely called a conflict, even when the old ownership hash differs.
        self.run_install("--update")
        self.assertEqual(agent.read_text(), desired)

    def test_update_preserves_config_and_unrelated_bytes_then_restore(self):
        agents_before = b"# Existing policy\r\n\r\nKeep these exact bytes."
        ignore_before = b"/existing/\r\n"
        omp_config = b"modelRoles:\n  default: user-choice\n"
        (self.project / "AGENTS.md").write_bytes(agents_before)
        (self.project / "AGENTS.md").chmod(0o640)
        (self.project / ".gitignore").write_bytes(ignore_before)
        (self.project / ".omp").mkdir()
        (self.project / ".omp/config.yml").write_bytes(omp_config)
        self.run_install("--profile", "tada")
        config = self.project / "ui-design-studio.json"
        config.write_bytes(b'{"profile":"my-custom-profile","keep":true}\n')
        source = self.pack / ".omp/skills/ui-assess/SKILL.md"
        source.write_text(source.read_text() + "Updated instructions\n")
        self.run_install(expected=1)
        self.run_install("--update", "--profile", "generic")
        self.assertEqual(config.read_bytes(), b'{"profile":"my-custom-profile","keep":true}\n')
        self.assertEqual((self.project / ".omp/config.yml").read_bytes(), omp_config)
        self.assertTrue((self.project / "AGENTS.md").read_bytes().startswith(agents_before))
        manifests = [json.loads(x.read_text()) for x in self.backups()]
        update = next(x for x in manifests if any(f["path"] == ".omp/skills/ui-assess/SKILL.md" and f["action"] == "replace" for f in x["files"]))
        self.run_install("--restore", update["backupId"])
        self.assertNotIn(b"Updated instructions", (self.project / ".omp/skills/ui-assess/SKILL.md").read_bytes())
        self.assertEqual(config.read_bytes(), b'{"profile":"my-custom-profile","keep":true}\n')

    def test_restore_original_bytes_modes_and_remove_only_created(self):
        before = b"Policy before installation\r\n"
        (self.project / "AGENTS.md").write_bytes(before)
        (self.project / "AGENTS.md").chmod(0o600)
        (self.project / "existing.txt").write_text("Keep me\n")
        self.run_install()
        backup_id = self.backups()[0].parent.name
        original_snapshot = snapshot(self.project)
        self.run_install("--restore", backup_id, "--dry-run")
        self.assertEqual(original_snapshot, snapshot(self.project))
        self.run_install("--restore", backup_id)
        self.assertEqual((self.project / "AGENTS.md").read_bytes(), before)
        self.assertEqual(stat.S_IMODE((self.project / "AGENTS.md").stat().st_mode), 0o600)
        self.assertEqual((self.project / "existing.txt").read_text(), "Keep me\n")
        self.assertFalse((self.project / "ui-design-studio.json").exists())
        self.assertFalse((self.project / "tools/ui-design").exists())
        self.assertTrue((self.project / ".venv-ui-design/pyvenv.cfg").exists())
        self.run_install("--restore", backup_id)

    def test_restore_refuses_edited_file_before_mutation(self):
        self.run_install()
        backup_id = self.backups()[0].parent.name
        (self.project / "AGENTS.md").write_text("User added important policy\n")
        before = snapshot(self.project)
        result = self.run_install("--restore", backup_id, expected=1)
        self.assertIn("AGENTS.md", result.stderr)
        self.assertEqual(before, snapshot(self.project))

    def test_symlink_and_bad_markers_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.project / ".omp").symlink_to(outside, target_is_directory=True)
        self.run_install(expected=1)
        self.assertEqual([], list(outside.iterdir()))
        (self.project / ".omp").unlink()
        (self.project / "AGENTS.md").write_text("<!-- ui-design-studio:start -->\nNo ending marker\n")
        self.run_install(expected=1)
        self.assertFalse((self.project / ".venv-ui-design").exists())

    def test_transaction_rolls_back_when_write_fails(self):
        spec = importlib.util.spec_from_file_location("ui_design_install_test", self.pack / "scripts/install.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        existing = self.project / "existing.txt"
        existing.write_bytes(b"original")
        changes = [
            module.Change("created.txt", None, None, b"new", 0o644),
            module.Change("existing.txt", b"original", 0o644, b"replaced", 0o644),
            module.Change("another.txt", None, None, b"another", 0o644),
        ]
        original_write = module.atomic_write
        def fail_one(path, data, mode):
            if path.name == "another.txt":
                raise OSError("injected write failure")
            return original_write(path, data, mode)
        with mock.patch.object(module, "atomic_write", side_effect=fail_one):
            with self.assertRaises(OSError):
                module.apply_changes(self.project, changes)
        self.assertEqual(existing.read_bytes(), b"original")
        self.assertFalse((self.project / "created.txt").exists())
        self.assertFalse((self.project / "another.txt").exists())

    def test_config_and_marked_block_preserve_surroundings(self):
        prefix = b"PREAMBLE\r\n"
        suffix = b"\r\nTRAILER with no final newline"
        (self.project / "AGENTS.md").write_bytes(prefix + b"<!-- ui-design-studio:start -->OLD<!-- ui-design-studio:end -->" + suffix)
        (self.project / "ui-design-studio.json").write_bytes(b'{"custom": 42}\n')
        self.run_install(expected=1)
        self.run_install("--update")
        updated = (self.project / "AGENTS.md").read_bytes()
        self.assertTrue(updated.startswith(prefix))
        self.assertTrue(updated.endswith(suffix))
        self.assertEqual(updated.count(b"<!-- ui-design-studio:start -->"), 1)
        self.assertEqual((self.project / "ui-design-studio.json").read_bytes(), b'{"custom": 42}\n')


if __name__ == "__main__":
    unittest.main()
