#!/usr/bin/env python3
"""Standard-library regression tests for the implementation-handoff helpers.

These tests verify pack tooling, not PRISM product acceptance. All Git repositories,
gate plans, synthetic review records, command outputs and receipts are disposable
TOOL_HARNESS_ONLY fixtures under TemporaryDirectory. A selected-G0 fixture success
must never be presented as implementation, browser, host or release qualification.

Run after the pack owner has regenerated MANIFEST.sha256:
    python tools/test_tools.py -v

No real project checkout, global Git configuration, installed OMP context, provider
account, browser, network service or live budget is modified or exercised here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
PACK = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from prism_pack import SKIP_PARTS, read_json, safe_child, state_path, verify_manifest


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_documents(output: str) -> list[dict]:
    """The helpers emit consecutive pretty-printed JSON objects, not JSONL."""
    decoder = json.JSONDecoder()
    position = 0
    values = []
    while position < len(output):
        while position < len(output) and output[position].isspace():
            position += 1
        if position == len(output):
            break
        value, position = decoder.raw_decode(output, position)
        if not isinstance(value, dict):
            raise AssertionError("Helper output must contain JSON objects")
        values.append(value)
    if not values:
        raise AssertionError("Helper emitted no JSON result")
    return values


@unittest.skipUnless(shutil.which("git"), "Git is required for disposable tool fixtures")
class HandoffToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fail clearly if the test file or any helper changed after finalization.
        # Never repair or rewrite the actual pack's manifest from the test suite.
        verify_manifest(PACK)
        cls.gates = {
            row["id"]: row
            for row in read_json(PACK / "contracts/gates.json")["gates"]
        }
        cls.release_case_ids = sorted({
            case
            for gate in cls.gates.values()
            if "release" in gate["requiredProfiles"]
            for case in gate["caseIds"]
        })

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="prism-tool-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.serial = 0
        # Remove inherited Git destinations/config injection. Only temporary local
        # repositories are configured; HOME and user/global settings are untouched.
        self.environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_") and key != "PYTHONPATH"
        }
        self.environment.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
            "PYTHONDONTWRITEBYTECODE": "1",
        })

    def unique(self, label: str) -> Path:
        self.serial += 1
        return self.base / f"{self.serial:02d}-{label}"

    def git(self, repo: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            env=self.environment, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def commit(self, repo: Path, message: str = "TOOL_HARNESS_ONLY fixture"):
        self.git(repo, "add", "--all")
        self.git(
            repo, "-c", "user.name=PRISM Tool Fixture",
            "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message,
        )

    def repository(self, label: str = "repo") -> Path:
        repo = self.unique(label)
        repo.mkdir()
        self.git(repo, "init", "--quiet", "--template=")
        self.git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
        self.git(repo, "config", "--local", "core.autocrlf", "false")
        (repo / "source.txt").write_text("TOOL_HARNESS_ONLY source version 1\n")
        (repo / "AGENTS.md").write_text("# Existing instructions\nPreserve this fixture.\n")
        (repo / ".gitignore").write_text(".prism-state/\n")
        existing = repo / ".omp/skills/existing-fixture/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("---\nname: existing-fixture\ndescription: Existing fixture.\n---\n")
        self.commit(repo)
        return repo

    def copy_pack(self, destination: Path) -> Path:
        shutil.copytree(
            PACK, destination,
            ignore=lambda _directory, names: [
                name for name in names
                if name in SKIP_PARTS or name.endswith((".pyc", ".pyo"))
            ],
        )
        verify_manifest(destination)
        return destination

    def tool(self, filename: str, *arguments, expect: int = 0):
        result = subprocess.run(
            [sys.executable, str(TOOLS / filename), *map(str, arguments)],
            cwd=self.base, env=self.environment, capture_output=True,
            text=True, timeout=45,
        )
        self.assertEqual(
            result.returncode, expect,
            f"{filename} exit {result.returncode}; expected {expect}\n"
            f"stdout:\n{result.stdout[-6000:]}\nstderr:\n{result.stderr[-6000:]}",
        )
        values = json_documents(result.stdout)
        return result, values[-1], values

    def write_json(self, path: Path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n")

    @staticmethod
    def working_files(root: Path) -> dict:
        """Snapshot working files/modes, deliberately excluding Git metadata."""
        result = {}
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if ".git" in relative.parts:
                continue
            if path.is_symlink():
                result[relative.as_posix()] = ("symlink", os.readlink(path))
            elif path.is_file():
                result[relative.as_posix()] = (
                    "file", path.read_bytes(), path.stat().st_mode & 0o777,
                )
        return result

    @staticmethod
    def output_script(relative: str = ".prism-state/outputs/G0.txt") -> str:
        return (
            "from pathlib import Path\nimport os\n"
            f"target = Path({relative!r})\n"
            "target.parent.mkdir(parents=True, exist_ok=True)\n"
            "target.write_text('TOOL_HARNESS_ONLY\\n' + os.environ['PRISM_GATE_RUN_ID'])\n"
            "print('TOOL_HARNESS_ONLY: helper behavior, not product acceptance')\n"
        )

    def plan(
        self, repo: Path, *, code: str | None = None, profile: str = "core",
        artifacts: list[str] | None = None, timeout: int = 5,
        path: Path | None = None,
    ) -> tuple[Path, dict]:
        path = path or repo / ".prism-state/plans/tool-harness.json"
        record = {
            "schemaVersion": "1.0.0",
            "targetProfile": profile,
            "description": "TOOL_HARNESS_ONLY; synthetic coverage, no product acceptance claim.",
            "source": {"requireCleanTree": True},
            "gates": [{
                "id": "G0",
                "commands": [{
                    "id": "tool-harness-g0",
                    "argv": [sys.executable, "-c", code if code is not None else self.output_script()],
                    "cwd": ".",
                    "timeoutSeconds": timeout,
                    "expectedExitCodes": [0],
                    "coversAcceptanceIds": list(self.gates["G0"]["caseIds"]),
                    "evidenceArtifacts": artifacts if artifacts is not None else [".prism-state/outputs/G0.txt"],
                }],
            }],
        }
        if profile == "release":
            record["review"] = {
                "independent": True, "reviewer": "TOOL_HARNESS_ONLY reviewer",
                "evidencePath": ".prism-state/review.json",
            }
        self.write_json(path, record)
        return path, record

    def run_g0(self, repo: Path, plan: Path, *, profile="core", expect=0):
        return self.tool(
            "run-gates.py", "--repo", repo, "--plan", plan,
            "--profile", profile, "--gate", "G0", expect=expect,
        )

    def receipt(self, summary: dict) -> dict:
        path = Path(summary["receipt"])
        self.assertTrue(path.is_relative_to(self.base))
        return read_json(path)

    def require_symlink(self, target: Path, link: Path):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"This platform cannot create the required symlink fixture: {exc}")

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(self):
        path = self.unique("input.json")
        bad_inputs = [
            '{"x": 1, "x": 2}', '{"nested": {"x": 1, "x": 2}}',
            '{"x": NaN}', '{"x": Infinity}', '{"x": -Infinity}',
            '{"x": 1e999}', '{"nested": [-1e999]}',
        ]
        for payload in bad_inputs:
            with self.subTest(payload=payload):
                path.write_text(payload)
                with self.assertRaises(ValueError):
                    read_json(path)
        path.write_text('{"amount": 0, "unknown": null, "finite": 1.25e2}')
        self.assertEqual(read_json(path), {"amount": 0, "unknown": None, "finite": 125.0})

    def test_safe_child_and_private_state_reject_escape_paths(self):
        repo = self.repository()
        valid = safe_child(repo, "source.txt", must_exist=True)
        self.assertEqual(valid, repo / "source.txt")
        for value in ["", " ", "../outside", "nested/../source.txt", str(self.base / "absolute")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_child(repo, value)
        outside = self.unique("outside")
        outside.mkdir()
        self.require_symlink(outside, repo / "escape")
        with self.assertRaises(ValueError):
            safe_child(repo, "escape/new-file")
        self.require_symlink(outside, repo / ".prism-state")
        with self.assertRaises(ValueError):
            state_path(repo, "receipt.json")
        self.assertEqual(list(outside.iterdir()), [])

    def test_manifest_detects_tampering_missing_and_unexpected_files(self):
        mini = self.unique("mini-pack")
        mini.mkdir()
        first = mini / "first.txt"
        second = mini / "second.txt"
        first.write_bytes(b"first\n")
        second.write_bytes(b"second\n")
        manifest = mini / "MANIFEST.sha256"
        manifest.write_text(f"{sha256(first)}  first.txt\n{sha256(second)}  second.txt\n")
        self.assertEqual(verify_manifest(mini)["files"], 2)
        first.write_bytes(b"changed\n")
        with self.assertRaisesRegex(ValueError, "Hash mismatch"):
            verify_manifest(mini)
        first.write_bytes(b"first\n")
        second.unlink()
        with self.assertRaisesRegex(ValueError, "Missing pack file"):
            verify_manifest(mini)
        second.write_bytes(b"second\n")
        (mini / "unexpected.txt").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "Unexpected pack file"):
            verify_manifest(mini)

    def test_prepare_preserves_dirty_source_and_activates_only_rebuild_context(self):
        source = self.repository("dirty-source")
        original_commit = self.git(source, "rev-parse", "HEAD").strip()
        (source / "source.txt").write_text("Uncommitted user change\n")
        (source / "untracked-user.txt").write_text("Untracked user work\n")
        before_files = self.working_files(source)
        before_status = self.git(source, "status", "--porcelain")
        destination = self.unique("prepared worktree")
        _, result, _ = self.tool(
            "prepare-worktree.py", "--repo", source, "--dest", destination,
            "--branch", "overhaul/tool-fixture",
        )
        self.assertEqual(result["status"], "PREPARED")
        self.assertTrue(result["sourceHadUncommittedChanges"])
        self.assertFalse(result["sourceUncommittedChangesIncluded"])
        self.assertEqual(self.working_files(source), before_files)
        self.assertEqual(self.git(source, "status", "--porcelain"), before_status)
        self.assertEqual(self.git(source, "rev-parse", "HEAD").strip(), original_commit)
        self.assertEqual(self.git(source, "branch", "--show-current").strip(), "main")
        self.assertEqual((destination / "source.txt").read_text(), "TOOL_HARNESS_ONLY source version 1\n")
        self.assertFalse((destination / "untracked-user.txt").exists())
        self.assertIn("Preserve this fixture.", (destination / "AGENTS.md").read_text())
        active = {p.parent.name for p in (destination / ".omp/skills").glob("*/SKILL.md")}
        self.assertEqual(active, {"existing-fixture", "prism-rebuild"})
        self.assertEqual(len(list((destination / ".prism-rebuild/blueprints/omp/skills").glob("*/SKILL.md.in"))), 10)
        verify_manifest(destination / ".prism-rebuild")

    def test_context_install_is_idempotent_and_restore_preserves_original_bytes(self):
        repo = self.repository()
        self.copy_pack(repo / ".prism-rebuild")
        agents = repo / "AGENTS.md"
        agents.chmod(0o640)
        before_agents = agents.read_bytes()
        exclude = repo / ".git/info/exclude"
        before_exclude = exclude.read_bytes() if exclude.exists() else None
        _, installed, _ = self.tool("install-rebuild-context.py", "--repo", repo)
        self.assertEqual(installed["status"], "INSTALLED")
        after_agents = agents.read_bytes()
        after_exclude = exclude.read_bytes()
        skill = repo / ".omp/skills/prism-rebuild/SKILL.md"
        skill_bytes = skill.read_bytes()
        _, repeated, _ = self.tool("install-rebuild-context.py", "--repo", repo)
        self.assertEqual(repeated["status"], "ALREADY_INSTALLED")
        self.assertEqual(agents.read_bytes(), after_agents)
        self.assertEqual(exclude.read_bytes(), after_exclude)
        self.assertEqual(skill.read_bytes(), skill_bytes)
        self.assertEqual(agents.read_text().count("<!-- PRISM-REBUILD:BEGIN v1 -->"), 1)
        _, restored, _ = self.tool("install-rebuild-context.py", "--repo", repo, "--restore")
        self.assertEqual(restored["status"], "RESTORED")
        self.assertEqual(agents.read_bytes(), before_agents)
        if os.name == "posix":
            self.assertEqual(agents.stat().st_mode & 0o777, 0o640)
        self.assertEqual(exclude.read_bytes() if exclude.exists() else None, before_exclude)
        self.assertFalse(skill.exists())
        self.assertTrue((repo / ".prism-rebuild/MANIFEST.sha256").is_file())
        _, again, _ = self.tool("install-rebuild-context.py", "--repo", repo, "--restore")
        self.assertEqual(again["status"], "NOT_INSTALLED")

    def test_context_conflict_blocks_retry_and_restore_before_any_partial_write(self):
        repo = self.repository()
        self.copy_pack(repo / ".prism-rebuild")
        self.tool("install-rebuild-context.py", "--repo", repo)
        agents = repo / "AGENTS.md"
        agents.write_bytes(agents.read_bytes() + b"Later user instruction\n")
        paths = [agents, repo / ".omp/skills/prism-rebuild/SKILL.md", repo / ".git/info/exclude"]
        before = {str(p): p.read_bytes() for p in paths}
        for arguments in [[], ["--restore"]]:
            with self.subTest(arguments=arguments):
                _, result, _ = self.tool("install-rebuild-context.py", "--repo", repo, *arguments, expect=2)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual({str(p): p.read_bytes() for p in paths}, before)

    def test_missing_or_damaged_local_pack_does_not_install_context(self):
        for mode in ["missing-pack", "missing-pack-context", "existing-unmanaged-skill"]:
            with self.subTest(mode=mode):
                repo = self.repository(mode)
                original = (repo / "AGENTS.md").read_bytes()
                if mode != "missing-pack":
                    self.copy_pack(repo / ".prism-rebuild")
                if mode == "missing-pack-context":
                    (repo / ".prism-rebuild/AGENTS.md").unlink()
                if mode == "existing-unmanaged-skill":
                    skill = repo / ".omp/skills/prism-rebuild/SKILL.md"
                    skill.parent.mkdir(parents=True)
                    skill.write_text("Unmanaged user-owned skill\n")
                _, result, _ = self.tool("install-rebuild-context.py", "--repo", repo, expect=2)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual((repo / "AGENTS.md").read_bytes(), original)
                self.assertFalse((repo / ".prism-state/rebuild-context.json").exists())

    def test_git_exclude_leaf_or_parent_symlink_cannot_redirect_context_writes(self):
        for placement in ["leaf", "parent"]:
            with self.subTest(placement=placement):
                repo = self.repository(placement)
                self.copy_pack(repo / ".prism-rebuild")
                original_agents = (repo / "AGENTS.md").read_bytes()
                outside = self.unique("outside-exclude")
                outside.mkdir()
                (outside / "exclude").write_text("User-owned external exclude\n")
                before = self.working_files(outside)
                info = repo / ".git/info"
                if placement == "leaf":
                    info.mkdir(exist_ok=True)
                    target = info / "exclude"
                    if target.exists():
                        target.unlink()
                    self.require_symlink(outside / "exclude", target)
                else:
                    if info.exists():
                        shutil.rmtree(info)
                    self.require_symlink(outside, info)
                _, result, _ = self.tool("install-rebuild-context.py", "--repo", repo, expect=2)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("redirected git exclude path", result["error"].lower())
                self.assertEqual(self.working_files(outside), before)
                self.assertEqual((repo / "AGENTS.md").read_bytes(), original_agents)
                self.assertFalse((repo / ".prism-state/rebuild-context.json").exists())

    def test_private_state_symlinks_block_all_affected_tools_without_external_writes(self):
        for placement in ["root", "evidence-child", "committed-prepare-root"]:
            with self.subTest(placement=placement):
                repo = self.repository(placement)
                outside = self.unique("outside-state")
                outside.mkdir()
                (outside / "sentinel.txt").write_text("Must remain unchanged\n")
                before = self.working_files(outside)
                plan_path, _ = self.plan(repo, path=self.unique("external-plan.json"))
                if placement == "evidence-child":
                    (repo / ".prism-state").mkdir()
                    self.require_symlink(outside, repo / ".prism-state/evidence")
                    invocations = [("run-gates.py", ["--plan", plan_path, "--profile", "core", "--gate", "G0"])]
                else:
                    self.require_symlink(outside, repo / ".prism-state")
                    if placement == "committed-prepare-root":
                        self.git(repo, "add", "--force", ".prism-state")
                        self.commit(repo)
                        invocations = [("prepare-worktree.py", ["--dest", self.unique("blocked-worktree"), "--branch", "overhaul/state-link-test"])]
                    else:
                        invocations = [
                            ("install-rebuild-context.py", []), ("status.py", []),
                            ("run-gates.py", ["--plan", plan_path, "--profile", "core", "--gate", "G0"]),
                        ]
                for filename, arguments in invocations:
                    _, result, _ = self.tool(filename, "--repo", repo, *arguments, expect=2)
                    self.assertEqual(result["status"], "BLOCKED")
                    self.assertIn("symlink", result["error"].lower())
                    self.assertEqual(self.working_files(outside), before)

    def test_child_cannot_redirect_parent_receipt_or_log_writes(self):
        repo = self.repository()
        outside = self.unique("outside-after-child")
        outside.mkdir()
        (outside / "sentinel.txt").write_text("Must remain unchanged\n")
        probe = self.unique("symlink-probe")
        self.require_symlink(outside, probe)
        probe.unlink()
        before = self.working_files(outside)
        script = (
            "from pathlib import Path\nimport os\n"
            "directory = Path(os.environ['PRISM_GATE_EVIDENCE_DIR'])\n"
            "moved = directory.with_name(directory.name + '-moved')\n"
            "directory.rename(moved)\n"
            f"directory.symlink_to(Path({str(outside)!r}), target_is_directory=True)\n"
            "print('TOOL_HARNESS_ONLY attempted evidence redirect')\n"
        )
        plan, _ = self.plan(repo, code=script, artifacts=[])
        _, result, _ = self.run_g0(repo, plan, expect=2)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("symlink", result["error"].lower())
        self.assertEqual(self.working_files(outside), before)

    def test_placeholder_plan_cannot_qualify_a_product(self):
        repo = self.repository()
        example = PACK / "config/verification-plan.example.json"
        _, result, _ = self.tool(
            "run-gates.py", "--repo", repo, "--plan", example,
            "--profile", "release", expect=2,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("no implemented verification commands", result["error"])
        self.assertFalse((repo / ".prism-state/latest-release.json").exists())

    def test_selected_g0_success_captures_exact_receipt_and_remains_partial(self):
        repo = self.repository()
        plan, _ = self.plan(repo)
        _, result, _ = self.run_g0(repo, plan)
        self.assertEqual(result["status"], "PASSED_SELECTED_GATES")
        self.assertTrue(result["selectedGatesOnly"])
        receipt = self.receipt(result)
        self.assertEqual(receipt["humanValidation"], "DEFERRED")
        self.assertTrue(receipt["sourceUnchanged"])
        self.assertEqual(receipt["planSha256"], sha256(plan))
        self.assertEqual(set(receipt["acceptanceIds"]), set(self.gates["G0"]["caseIds"]))
        command = receipt["commands"][0]
        self.assertEqual(command["exitCode"], 0)
        self.assertEqual(command["status"], "passed")
        self.assertEqual(command["logSha256"], sha256(repo / command["log"]))
        self.assertEqual(receipt["sourceSnapshotSha256"], sha256(repo / receipt["sourceSnapshot"]))
        self.assertEqual(len(command["artifacts"]), 1)
        captured = command["artifacts"][0]
        self.assertEqual(captured["sha256"], sha256(repo / captured["path"]))
        self.assertIn("TOOL_HARNESS_ONLY", (repo / captured["path"]).read_text())
        _, status, _ = self.tool("status.py", "--repo", repo)
        self.assertTrue(status["observedVerification"]["core"]["current"])
        self.assertTrue(status["observedVerification"]["core"]["selectedGatesOnly"])
        self.assertEqual(status["observedVerification"]["release"]["status"], "NOT_RUN")

    def test_nonzero_timeout_missing_and_unchanged_artifact_fail(self):
        for mode in ["nonzero", "timeout", "missing-artifact", "unchanged-artifact"]:
            with self.subTest(mode=mode):
                repo = self.repository(mode)
                code = self.output_script()
                timeout = 5
                if mode == "nonzero":
                    code += "import sys\nsys.exit(7)\n"
                elif mode == "timeout":
                    code += "import time\ntime.sleep(30)\n"
                    timeout = 1
                else:
                    code = "print('TOOL_HARNESS_ONLY: no new output artifact')\n"
                    if mode == "unchanged-artifact":
                        artifact = repo / ".prism-state/outputs/G0.txt"
                        artifact.parent.mkdir(parents=True)
                        artifact.write_text("TOOL_HARNESS_ONLY stale output\n")
                plan, _ = self.plan(repo, code=code, timeout=timeout)
                _, result, _ = self.run_g0(repo, plan, expect=1)
                self.assertEqual(result["status"], "FAILED")
                command = self.receipt(result)["commands"][0]
                self.assertEqual(command["status"], "failed")
                if mode == "nonzero":
                    self.assertEqual(command["exitCode"], 7)
                elif mode == "timeout":
                    self.assertTrue(command["timedOut"])
                    self.assertNotEqual(command["exitCode"], 0)
                elif mode == "missing-artifact":
                    self.assertEqual(command["missingArtifacts"], [".prism-state/outputs/G0.txt"])
                else:
                    self.assertEqual(command["staleArtifacts"], [".prism-state/outputs/G0.txt"])

    def test_source_mutation_invalidates_successful_command(self):
        repo = self.repository()
        script = self.output_script() + "Path('source.txt').write_text('TOOL_HARNESS_ONLY changed source\\n')\n"
        plan, _ = self.plan(repo, code=script)
        _, result, _ = self.run_g0(repo, plan, expect=1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["sourceUnchanged"])
        receipt = self.receipt(result)
        self.assertEqual(receipt["commands"][0]["exitCode"], 0)
        self.assertNotEqual(receipt["sourceFingerprintSha256"], receipt["finalSourceFingerprintSha256"])
        _, status, _ = self.tool("status.py", "--repo", repo)
        self.assertFalse(status["observedVerification"]["core"]["current"])

    def test_status_invalidates_changed_plan_log_snapshot_or_captured_artifact(self):
        for target in ["plan", "log", "source-snapshot", "captured-artifact"]:
            with self.subTest(target=target):
                repo = self.repository(target)
                plan, content = self.plan(repo)
                _, result, _ = self.run_g0(repo, plan)
                receipt = self.receipt(result)
                if target == "plan":
                    content["description"] += " CHANGED AFTER RUN"
                    self.write_json(plan, content)
                else:
                    relative = (
                        receipt["commands"][0]["log"] if target == "log"
                        else receipt["sourceSnapshot"] if target == "source-snapshot"
                        else receipt["commands"][0]["artifacts"][0]["path"]
                    )
                    path = repo / relative
                    path.write_bytes(path.read_bytes() + b"\nTOOL_HARNESS_ONLY tampered\n")
                _, status, _ = self.tool("status.py", "--repo", repo)
                observed = status["observedVerification"]["core"]
                self.assertFalse(observed["current"])
                self.assertTrue(observed["evidenceErrors"])
                self.assertEqual(observed["status"], "PASSED_SELECTED_GATES")

    def test_release_missing_stale_or_misattributed_review_is_blocked(self):
        for mode in ["missing", "same-actor", "wrong-plan-reviewer", "stale-fingerprint"]:
            with self.subTest(mode=mode):
                repo = self.repository(mode)
                plan, content = self.plan(repo, profile="release")
                if mode != "missing":
                    evidence = repo / ".prism-state/synthetic-review-input.txt"
                    evidence.write_text("TOOL_HARNESS_ONLY; not product acceptance evidence.\n")
                    _, fingerprint, _ = self.tool(
                        "run-gates.py", "--repo", repo, "--plan", plan, "--fingerprint",
                    )
                    review = {
                        "schemaVersion": "1.0.0",
                        "sourceFingerprintSha256": fingerprint["sourceFingerprintSha256"],
                        "reviewedPlanSha256": fingerprint["reviewedPlanSha256"],
                        "reviewer": {
                            "identity": content["review"]["reviewer"],
                            "actorId": "harness-reviewer", "independent": True,
                            "implementationActorIds": ["harness-implementer"],
                            "method": "independent", "fallbackReason": None,
                        },
                        "findings": {"severeOpen": 0, "items": []},
                        "checkedAcceptance": [{
                            "acceptanceId": case, "result": "passed",
                            "evidencePaths": [str(evidence.relative_to(repo))],
                            "note": "TOOL_HARNESS_ONLY deliberately synthetic validator input; no real product assertion.",
                        } for case in self.release_case_ids],
                        "recommendation": "ready",
                    }
                    if mode == "same-actor":
                        review["reviewer"]["actorId"] = "harness-implementer"
                    elif mode == "wrong-plan-reviewer":
                        review["reviewer"]["identity"] = "A different synthetic reviewer"
                    else:
                        review["sourceFingerprintSha256"] = "0" * 64
                    self.write_json(repo / content["review"]["evidencePath"], review)
                _, result, _ = self.run_g0(repo, plan, profile="release", expect=2)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertFalse((repo / ".prism-state/latest-release.json").exists())
                self.assertFalse((repo / ".prism-state/outputs/G0.txt").exists())

    def test_large_command_log_is_retained_without_truncation(self):
        repo = self.repository()
        size = 2 * 1024 * 1024 + 257
        marker = "END-OF-TOOL-HARNESS-LARGE-LOG"
        code = self.output_script() + f"import sys\nsys.stdout.write('H' * {size} + '\\n{marker}\\n')\n"
        plan, _ = self.plan(repo, code=code, timeout=15)
        _, result, _ = self.run_g0(repo, plan)
        command = self.receipt(result)["commands"][0]
        log = repo / command["log"]
        self.assertGreater(command["rawOutputBytes"], 2 * 1024 * 1024)
        self.assertGreater(log.stat().st_size, 2 * 1024 * 1024)
        self.assertFalse(command["outputTruncated"])
        self.assertTrue(log.read_text().endswith(marker + "\n"))
        self.assertEqual(command["logSha256"], sha256(log))

    def test_deterministic_zip_ignores_root_name_and_mtime_and_rejects_in_place_output(self):
        copy = self.copy_pack(self.unique("pack-copy"))
        first, second = self.unique("first.zip"), self.unique("second.zip")
        _, initial, _ = self.tool("build-pack.py", "--root", copy, "--output", first)
        installed = self.unique("installed-repo") / ".prism-rebuild"
        installed.parent.mkdir()
        copy.rename(installed)
        copy = installed
        for path in copy.rglob("*"):
            if path.is_file():
                os.utime(path, (946684800, 946684800))
        _, repeated, _ = self.tool("build-pack.py", "--root", copy, "--output", second)
        self.assertEqual(initial["status"], "BUILT")
        self.assertEqual(initial["sha256"], repeated["sha256"])
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            self.assertIn("PRISM-Studio-Rebuild-Pack-v1.0.0/MANIFEST.sha256", names)
            self.assertEqual(len({item.date_time for item in archive.infolist()}), 1)
            self.assertFalse(any("__pycache__" in name or ".prism-state" in name or name.endswith(".pdf") for name in names))
        forbidden = copy / "nested-output.zip"
        _, blocked, _ = self.tool("build-pack.py", "--root", copy, "--output", forbidden, expect=2)
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertFalse(forbidden.exists())

    def test_invalid_gate_bindings_are_rejected_before_execution(self):
        for mode in ["shell-string", "nonzero-expected", "missing-case", "unknown-gate", "profile-mismatch", "escaping-cwd"]:
            with self.subTest(mode=mode):
                repo = self.repository(mode)
                plan, content = self.plan(repo)
                command = content["gates"][0]["commands"][0]
                if mode == "shell-string":
                    command["argv"] = "echo a shell string is not an argv array"
                elif mode == "nonzero-expected":
                    command["expectedExitCodes"] = [0, 7]
                elif mode == "missing-case":
                    command["coversAcceptanceIds"] = []
                elif mode == "unknown-gate":
                    content["gates"].append({"id": "G999", "commands": []})
                elif mode == "profile-mismatch":
                    content["targetProfile"] = "web"
                else:
                    command["cwd"] = "../"
                self.write_json(plan, content)
                _, result, _ = self.run_g0(repo, plan, expect=2)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertFalse((repo / ".prism-state/outputs/G0.txt").exists())


if __name__ == "__main__":
    unittest.main()
