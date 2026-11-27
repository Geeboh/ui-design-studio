"""Exercise release privacy and destination validation in disposable sources."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ui_design_release_builder_test", ROOT / "scripts/package_release.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
M8_SPEC = importlib.util.spec_from_file_location("ui_design_m8_checks_test", ROOT / "tools/run_prism_m8_checks.py")
m8_checks = importlib.util.module_from_spec(M8_SPEC)
M8_SPEC.loader.exec_module(m8_checks)


class ReleaseBuilderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ui-design-release-test-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "source"
        self.root.mkdir()
        for name in builder.TREES:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        for name in builder.TOP:
            (self.root / name).write_text(name + "\n", encoding="utf-8")
        (self.root / "release.json").write_text(json.dumps({
            "version": "1.4.1", "releaseDate": "2026-11-14", "skillCount": 1, "agentCount": 1,
        }), encoding="utf-8")
        self.skill = self.root / ".omp/skills/example"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text("Example skill\n", encoding="utf-8")
        (self.root / ".omp/agents/ui-example.md").write_text("Example agent\n", encoding="utf-8")
        self.manifest = self.root / "MANIFEST.sha256"
        self.original_manifest = b"Existing manifest must survive rejected builds.\n"
        self.manifest.write_bytes(self.original_manifest)
        self.output = self.base / "external/release.zip"
        patch = mock.patch.object(builder, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)
    def clean_manifest(self):
        self.manifest.write_text(builder.manifest(builder.sources()), encoding="utf-8")

    def test_build_requires_clean_manifest_before_mutation(self):
        with self.assertRaisesRegex(ValueError, "missing or stale"):
            builder.build(self.output)
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
        self.assertFalse(self.output.exists())
        self.clean_manifest()
        self.assertEqual(builder.build(self.output, check=True)["status"], "PASS")
    def test_m8_artifact_names_follow_release_version(self):
        with mock.patch.object(m8_checks, "ROOT", self.root):
            self.assertEqual(
                [path.relative_to(self.root).as_posix() for path in m8_checks.artifacts()],
                [
                    "dist/prism-v2/UI-Design-Studio-PRISM-v1.4.1.zip",
                    "dist/prism-v2/ui_design_studio_mcp-1.4.1.tar.gz",
                    "dist/prism-v2/ui_design_studio_mcp-1.4.1-py3-none-any.whl",
                ],
            )
    def test_private_environment_files_are_excluded_and_example_is_retained(self):
        for directory in (self.skill, self.root / "docs/nested", self.root / "src/example"):
            directory.mkdir(parents=True, exist_ok=True)
            for name in (".env.production", ".env.local"):
                (directory / name).write_text("PRIVATE_ENV=not-for-distribution\n", encoding="utf-8")
            private = directory / ".env.private"
            private.mkdir()
            (private / "settings.txt").write_text("Private directory contents\n", encoding="utf-8")
            (directory / ".env.example").write_text("PUBLIC_ENV=example\n", encoding="utf-8")

        self.clean_manifest()
        result = builder.build(self.output)
        self.assertEqual(result["status"], "PASS")
        with zipfile.ZipFile(self.output) as archive:
            names = archive.namelist()
            self.assertFalse(any(part.startswith(".env.") and part != ".env.example"
                                 for name in names for part in Path(name).parts))
            for relative in (".omp/skills/example", "docs/nested", "src/example"):
                self.assertEqual(archive.read(f"ui-design-studio-v1.4.1/{relative}/.env.example"),
                                 b"PUBLIC_ENV=example\n")
        manifest = self.manifest.read_text(encoding="utf-8")
        self.assertIn(".env.example", manifest)
        for name in (".env.production", ".env.local", ".env.private"):
            self.assertNotIn(name, manifest)

    def test_environment_example_directory_does_not_publish_private_descendants(self):
        directory = self.skill / ".env.example"
        directory.mkdir()
        (directory / "private-config").write_text("PRIVATE_SECRET=not-for-distribution\n", encoding="utf-8")
        (directory / ".env.example").write_text("PRIVATE_NESTED_TEMPLATE=not-for-distribution\n", encoding="utf-8")
        self.clean_manifest()
        builder.build(self.output)
        with zipfile.ZipFile(self.output) as archive:
            self.assertFalse(any("/.env.example/" in name for name in archive.namelist()))
            self.assertNotIn(b"PRIVATE_SECRET", b"".join(archive.read(name) for name in archive.namelist()))
        self.assertNotIn(".env.example/", self.manifest.read_text(encoding="utf-8"))

    def test_runtime_design_records_are_excluded(self):
        runtime = self.root / "docs/design/runs/current"
        runtime.mkdir(parents=True)
        (runtime / ".design-server.json").write_text('{"token":"private"}\n', encoding="utf-8")
        (runtime / "draft.html").write_text("<h1>private</h1>\n", encoding="utf-8")
        (self.root / "docs/.design-owner.json").write_text('{"owner":"private"}\n', encoding="utf-8")
        self.clean_manifest()
        builder.build(self.output)
        with zipfile.ZipFile(self.output) as archive:
            payload = b"".join(archive.read(name) for name in archive.namelist())
        self.assertNotIn(b"private", payload)

    def test_symlinked_manifest_is_rejected_in_check_mode(self):
        target = self.base / "manifest-target.txt"
        target.write_bytes(self.original_manifest)
        self.manifest.unlink()
        self.manifest.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "non-regular manifest"):
            builder.build(self.output, check=True)

    def test_env_and_credentials_are_excluded(self):
        for name in (".env", "credentials/token"):
            with self.subTest(name=name):
                path = self.skill / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Private state\n", encoding="utf-8")
                self.clean_manifest()
                builder.build(self.output)
                with zipfile.ZipFile(self.output) as archive:
                    names = archive.namelist()
                self.assertFalse(any(name in archive_name for archive_name in names))
                self.assertNotIn(name, self.manifest.read_text(encoding="utf-8"))
                path.unlink()
    def test_nested_private_trees_are_not_packaged(self):
        files = {
            "docs/nested/.git/config": "git remote private\n",
            "src/vendor/node_modules/private.js": "module private\n",
            "tools/cache/__pycache__/private.pyc": "bytecode\n",
            "examples/.DS_Store": "finder metadata\n",
            "docs/design/runs/current/draft.html": "runtime private\n",
            "src/.ui-design-studio/state.json": "project state\n",
        }
        for relative, contents in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        self.clean_manifest()
        builder.build(self.output)
        with zipfile.ZipFile(self.output) as archive:
            names = archive.namelist()
        for relative in files:
            self.assertFalse(any(relative in name for name in names), relative)
        manifest = self.manifest.read_text(encoding="utf-8")
        for relative in files:
            self.assertNotIn(relative, manifest)

    def test_symlinked_environment_example_is_rejected(self):
        target = self.base / "private.txt"
        target.write_text("Private state\n", encoding="utf-8")
        (self.skill / ".env.example").symlink_to(target)
        with self.assertRaises(ValueError):
            builder.build(self.output)
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
        self.assertFalse(self.output.exists())

    def test_internal_outputs_are_rejected_before_mutation(self):
        for tree in builder.TREES:
            with self.subTest(tree=tree):
                output = self.root / tree / "new-output/custom.zip"
                with self.assertRaises(ValueError):
                    builder.build(output)
                self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
                self.assertFalse(output.exists())
                self.assertFalse(output.with_name(output.name + ".sha256").exists())
                self.assertFalse(output.parent.exists())

    def test_existing_internal_outputs_are_not_repackaged(self):
        output = self.root / "docs/custom.zip"
        sidecar = output.with_name(output.name + ".sha256")
        output.write_bytes(b"Existing archive")
        sidecar.write_bytes(b"Existing checksum")
        with self.assertRaises(ValueError):
            builder.build(output)
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
        self.assertEqual(output.read_bytes(), b"Existing archive")
        self.assertEqual(sidecar.read_bytes(), b"Existing checksum")

    def test_output_alias_into_packaged_sources_is_rejected(self):
        alias = self.base / "docs-link"
        alias.symlink_to(self.root / "docs", target_is_directory=True)
        output = alias / "custom.zip"
        with self.assertRaises(ValueError):
            builder.build(output)
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_name(output.name + ".sha256").exists())

    def test_symlinked_sidecar_preserves_archive_manifest_and_target(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"Existing archive")
        target = self.base / "private-target.txt"
        target.write_bytes(b"Private target")
        sidecar = self.output.with_name(self.output.name + ".sha256")
        sidecar.symlink_to(target)
        with self.assertRaises(ValueError):
            builder.build(self.output)
        self.assertEqual(self.output.read_bytes(), b"Existing archive")
        self.assertEqual(target.read_bytes(), b"Private target")
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
        self.assertTrue(sidecar.is_symlink())
        self.assertEqual(sidecar.readlink(), target)

    def test_directory_destinations_are_rejected_before_mutation(self):
        self.output.parent.mkdir()
        sidecar = self.output.with_name(self.output.name + ".sha256")
        for destination in (self.output, sidecar):
            with self.subTest(destination=destination.name):
                destination.mkdir()
                if destination == sidecar:
                    self.output.write_bytes(b"Existing archive")
                with self.assertRaises(ValueError):
                    builder.build(self.output)
                self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
                self.assertTrue(destination.is_dir())
                if destination == sidecar:
                    self.assertEqual(self.output.read_bytes(), b"Existing archive")
                    self.output.unlink()
                else:
                    self.assertFalse(sidecar.exists())
                destination.rmdir()

    def test_non_directory_parent_is_rejected_before_manifest_changes(self):
        parent = self.base / "not-a-directory"
        parent.write_bytes(b"Existing file")
        with self.assertRaises(ValueError):
            builder.build(parent / "release.zip")
        self.assertEqual(parent.read_bytes(), b"Existing file")
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)

    def test_invalid_output_suffix_does_not_change_manifest(self):
        with self.assertRaises(ValueError):
            builder.build(self.base / "release.txt")
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)

    def test_readonly_checksum_never_leaves_a_replaced_archive_with_stale_metadata(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"Existing archive")
        sidecar = self.output.with_name(self.output.name + ".sha256")
        sidecar.write_bytes(b"Existing checksum")
        sidecar.chmod(0o444)
        write_text = Path.write_text

        def deny_checksum_write(path, *args, **kwargs):
            if path == sidecar:
                raise PermissionError("Synthetic non-root write to read-only checksum")
            return write_text(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", deny_checksum_write):
            try:
                self.clean_manifest()
                builder.build(self.output)
            except PermissionError:
                self.assertEqual(self.output.read_bytes(), b"Existing archive")
                self.assertEqual(sidecar.read_bytes(), b"Existing checksum")
            else:
                digest = hashlib.sha256(self.output.read_bytes()).hexdigest()
                self.assertEqual(sidecar.read_text(), f"{digest}  release.zip\n")

    def test_checksum_commit_failure_restores_previous_archive(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"Existing archive")
        sidecar = self.output.with_name(self.output.name + ".sha256")
        sidecar.write_bytes(b"Existing checksum")
        replace = builder.os.replace

        def fail_checksum(source, destination):
            if destination == sidecar:
                raise OSError("Synthetic checksum commit failure")
            return replace(source, destination)

        with mock.patch.object(builder.os, "replace", side_effect=fail_checksum):
            self.clean_manifest()
            with self.assertRaisesRegex(OSError, "Synthetic checksum commit failure"):
                builder.build(self.output)
        self.assertEqual(self.output.read_bytes(), b"Existing archive")
        self.assertEqual(sidecar.read_bytes(), b"Existing checksum")

    def test_external_and_dist_outputs_remain_deterministic(self):
        self.clean_manifest()
        outputs = (self.output, self.root / "dist/release.zip")
        archives = []
        for output in outputs:
            result = builder.build(output)
            self.assertEqual(result["status"], "PASS")
            data = output.read_bytes()
            archives.append(data)
            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(result["sha256"], digest)
            self.assertEqual(output.with_name(output.name + ".sha256").read_text(encoding="utf-8"),
                             f"{digest}  release.zip\n")
            self.assertEqual(builder.build(output, check=True)["status"], "PASS")
        self.assertEqual(archives[0], archives[1])
        with zipfile.ZipFile(outputs[0]) as archive:
            self.assertEqual(archive.read("ui-design-studio-v1.4.1/MANIFEST.sha256"), self.manifest.read_bytes())
            self.assertTrue(all(info.date_time == (2026, 11, 14, 0, 0, 0) for info in archive.infolist()))


class MilestoneRunnerTests(unittest.TestCase):
    def test_rejects_external_absolute_and_traversal_test_paths(self):
        runner = ROOT / "tools/run_prism_milestone_tests.py"
        receipt = ROOT / ".prism-state/m3-workflow-tests.txt"
        previous = receipt.read_bytes() if receipt.exists() else None
        arguments = (
            str(ROOT / "tests/test_prism_m3.py"),
            str(ROOT.parent / "test_prism_m3.py"),
            "../tests/test_prism_m3.py",
            "tests/../tests/test_prism_m3.py",
        )
        try:
            for argument in arguments:
                with self.subTest(argument=argument):
                    result = subprocess.run(
                        [sys.executable, str(runner), argument],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("unsupported milestone test path", result.stderr)
        finally:
            if previous is None:
                self.assertFalse(receipt.exists())
            else:
                self.assertEqual(receipt.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
