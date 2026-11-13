"""Exercise global installer ownership without network package installation."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ui_design_global_install_test", ROOT / "scripts/install_mcp.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
REAL_RUN = subprocess.run


def snapshot(root: Path) -> dict:
    result = {}
    for path in sorted(root.rglob("*")):
        name = str(path.relative_to(root))
        if path.is_symlink():
            result[name] = ("link", os.readlink(path))
        elif path.is_file():
            result[name] = ("file", hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
        else:
            result[name] = ("directory", stat.S_IMODE(path.stat().st_mode))
    return result


class GlobalMCPInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ui design global installer ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "home with spaces"
        self.home.mkdir()
        self.prefix = self.home / ".local/share/ui-design-studio/mcp"
        self.user_bin = self.home / ".local/bin"
        self.calls = []

    def external_install(self, command, **kwargs):
        self.calls.append(command)
        if command[1:3] == ["-m", "venv"]:
            return REAL_RUN(command[:-1] + ["--without-pip", command[-1]], **kwargs)
        self.assertEqual(command[:6], [str(self.prefix / "bin/python"), "-m", "pip", "--isolated", "install", "--upgrade"])
        self.assertEqual(command[6:], [str(ROOT)])
        for name, function in (("ui-design", "main"), ("ui-design-mcp", "mcp_main")):
            executable = self.prefix / "bin" / name
            executable.write_text(f"#!{self.prefix / 'bin/python'}\nfrom ui_design_studio.cli import {function}\nraise SystemExit({function}())\n")
            executable.chmod(0o755)
        return subprocess.CompletedProcess(command, 0)

    def install(self):
        with mock.patch.object(installer.subprocess, "run", side_effect=self.external_install):
            return installer.install(self.home)

    def test_new_install_and_owned_upgrade_use_isolated_prefix(self):
        projects = [self.base / "first project", self.base / "second project"]
        for project in projects:
            project.mkdir()
            (project / "keep.txt").write_text("Unrelated project data\n")
        before = [snapshot(project) for project in projects]
        self.assertEqual(self.install(), (self.prefix, self.user_bin))
        self.assertEqual(json.loads((self.prefix / installer.MARKER).read_text()), {
            "schemaVersion": 1, "installer": "ui-design-studio-mcp",
            "prefix": str(self.prefix), "userBin": str(self.user_bin),
        })
        for name in ("ui-design", "ui-design-mcp"):
            self.assertEqual(os.readlink(self.user_bin / name), str(self.prefix / "bin" / name))
            self.assertTrue(os.access(self.user_bin / name, os.X_OK))
        sentinel = self.prefix / "keep.txt"
        sentinel.write_bytes(b"Unrelated owned-prefix data\x00")
        installed = snapshot(self.home)
        self.install()
        self.assertEqual(snapshot(self.home), installed)
        self.assertEqual([snapshot(project) for project in projects], before)
        self.assertEqual(sum(command[1:3] == ["-m", "venv"] for command in self.calls), 1)
        self.assertEqual(sum(command[1:3] == ["-m", "pip"] for command in self.calls), 2)
        self.assertFalse(any("--no-deps" in command for command in self.calls))

    def test_external_pip_target_configuration_cannot_redirect_installation(self):
        config = self.base / "external-pip.conf"
        config.write_text(f"[install]\ntarget = {self.home / '.local'}\n", encoding="utf-8")
        script = (
            "import json; from pip._internal.commands import create_command; "
            "options, args = create_command('install', isolated=True).parse_args(['--upgrade', '.']); "
            "print(json.dumps({'target': options.target_dir, 'prefix': options.prefix_path, 'root': options.root_path}))"
        )

        def install_with_real_config_parser(command, **kwargs):
            if command[1:3] == ["-m", "pip"]:
                parsed = REAL_RUN([sys.executable, "-I", "-c", script], env=kwargs.get("env"),
                                  cwd=self.base, capture_output=True, text=True, check=True)
                self.assertEqual(json.loads(parsed.stdout), {"target": None, "prefix": None, "root": None})
            return self.external_install(command, **kwargs)

        with mock.patch.dict(os.environ, {"PIP_CONFIG_FILE": str(config)}):
            with mock.patch.object(installer.subprocess, "run", side_effect=install_with_real_config_parser):
                self.assertEqual(installer.install(self.home), (self.prefix, self.user_bin))

    def test_unrelated_user_executable_blocks_all_mutations(self):
        self.user_bin.mkdir(parents=True)
        (self.user_bin / "ui-design-mcp").write_bytes(b"User executable\x00")
        before = snapshot(self.home)
        with mock.patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(installer.InstallError, "unrelated executable"):
                installer.install(self.home)
        run.assert_not_called()
        self.assertEqual(snapshot(self.home), before)
        self.assertFalse(self.prefix.exists())

    def test_unmanaged_prefix_and_wrong_marker_block_all_mutations(self):
        self.prefix.mkdir(parents=True)
        (self.prefix / "user-data").write_bytes(b"User venv data\x00")
        for marker in (None, "not JSON", json.dumps({"installer": "other"})):
            with self.subTest(marker=marker):
                if marker is not None:
                    (self.prefix / installer.MARKER).write_text(marker)
                before = snapshot(self.home)
                with mock.patch.object(installer.subprocess, "run") as run:
                    with self.assertRaises(installer.InstallError):
                        installer.install(self.home)
                run.assert_not_called()
                self.assertEqual(snapshot(self.home), before)

    def test_symlinked_parents_and_dangling_user_links_are_untouched(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "user-data").write_text("Keep\n")
        (self.home / ".local").symlink_to(outside, target_is_directory=True)
        before = snapshot(outside)
        with mock.patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(installer.InstallError, "symlinked"):
                installer.install(self.home)
        run.assert_not_called()
        self.assertEqual(snapshot(outside), before)
        (self.home / ".local").unlink()
        self.user_bin.mkdir(parents=True)
        (self.user_bin / "ui-design").symlink_to(self.prefix / "bin/ui-design")
        before = snapshot(self.home)
        with self.assertRaisesRegex(installer.InstallError, "unrelated executable"):
            self.install()
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.calls, [])

    def test_owned_upgrade_rejects_conflicting_link_without_touching_environment(self):
        self.install()
        link = self.user_bin / "ui-design-mcp"
        link.unlink()
        link.write_bytes(b"User replacement\x00")
        before = snapshot(self.home)
        with mock.patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(installer.InstallError, "unrelated executable"):
                installer.install(self.home)
        run.assert_not_called()
        self.assertEqual(snapshot(self.home), before)

    def test_owned_upgrade_rejects_symlinked_environment_and_marker(self):
        self.install()
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("Keep\n")
        link = self.prefix / "bin/external"
        link.symlink_to(outside, target_is_directory=True)
        before = snapshot(self.home), snapshot(outside)
        with mock.patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(installer.InstallError, "symlinked environment"):
                installer.install(self.home)
        run.assert_not_called()
        self.assertEqual((snapshot(self.home), snapshot(outside)), before)
        link.unlink()
        marker = self.prefix / installer.MARKER
        marker.replace(outside / "marker.json")
        marker.symlink_to(outside / "marker.json")
        before = snapshot(self.home), snapshot(outside)
        with self.assertRaisesRegex(installer.InstallError, "unmanaged"):
            self.install()
        self.assertEqual((snapshot(self.home), snapshot(outside)), before)

    def test_failed_new_environment_or_pip_removes_owned_prefix(self):
        for failing_stage in ("venv", "pip"):
            with self.subTest(stage=failing_stage):
                def fail(command, **kwargs):
                    if command[2] == failing_stage:
                        raise subprocess.CalledProcessError(1, command)
                    return self.external_install(command, **kwargs)
                with mock.patch.object(installer.subprocess, "run", side_effect=fail):
                    with self.assertRaises(subprocess.CalledProcessError):
                        installer.install(self.home)
                self.assertFalse(self.prefix.exists())
                self.assertFalse((self.user_bin / "ui-design").exists())
                self.assertFalse((self.user_bin / "ui-design-mcp").exists())

    def test_mixed_project_flags_are_rejected_before_installing(self):
        for flags in (("--project", str(self.base)), ("--update",), ("--dry-run",), ("--restore", "backup")):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()):
                with mock.patch.object(installer, "install") as install:
                    with self.assertRaises(SystemExit) as raised:
                        installer.main(["--mcp-global", *flags])
                self.assertEqual(raised.exception.code, 2)
                install.assert_not_called()
        self.assertEqual(snapshot(self.home), {})

    def test_shell_global_help_and_conflict_clean_bootstrap_without_project_files(self):
        project = self.base / "arbitrary project"
        project.mkdir()
        temporary = self.base / "bootstrap"
        temporary.mkdir()
        environment = dict(os.environ, HOME=str(self.home), TMPDIR=str(temporary))
        help_result = REAL_RUN(["bash", str(ROOT / "install.sh"), "--mcp-global", "--help"], cwd=project,
                               env=environment, text=True, capture_output=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--mcp-global", help_result.stdout)
        result = REAL_RUN(["bash", str(ROOT / "install.sh"), "--mcp-global", "--project", str(project)], cwd=project,
                          env=environment, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unrecognized arguments", result.stderr)
        self.assertEqual(list(temporary.iterdir()), [])
        self.assertEqual(snapshot(project), {})
        self.assertEqual(snapshot(self.home), {})

    def test_main_prints_absolute_paths_and_path_advice(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"HOME": str(self.home)}), mock.patch.object(installer.sys, "prefix", str(self.base / "bootstrap")):
            with mock.patch.object(installer.subprocess, "run", side_effect=self.external_install), contextlib.redirect_stdout(output):
                self.assertEqual(installer.main(["--mcp-global"]), 0)
        for name in ("ui-design", "ui-design-mcp"):
            self.assertIn(str(self.prefix / "bin" / name), output.getvalue())
            self.assertIn(str(self.user_bin / name), output.getvalue())
        self.assertIn("PATH", output.getvalue())
        self.assertIn("--repo /absolute/project/path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
