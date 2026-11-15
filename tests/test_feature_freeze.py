"""Behavioral regressions for feature-freeze workflow acceptance defects."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_studio import SCRIPT, fixture_run, fixture_theme, studio, write_json


class FreezeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ui-freeze-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.theme = fixture_theme(self.repo)

    def test_bounded_scopes_cannot_finalize_or_register_complete_theme(self):
        for scope in studio.SCOPE_VALUES:
            if scope == "full-redesign":
                continue
            with self.subTest(scope=scope):
                root = fixture_run(self.repo, self.theme)
                record = studio.read_json(root / "run.json")
                record["scope"] = scope
                write_json(root / "run.json", record)
                decisions = studio.read_json(root / "decisions.json")
                decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
                write_json(root / "decisions.json", decisions)
                decisions["decisions"].append({"stage": "finalize", "actor": "director", "outcome": "approved",
                    "rationale": "Synthetic bounded-scope regression", "inputsDigest": studio.check_run(root)["reviewDigest"]})
                write_json(root / "decisions.json", decisions)
                self.assertEqual(studio.check_run(root)["status"], "BLOCKED")
                result = subprocess.run([sys.executable, str(SCRIPT), "check-run", str(root)],
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["status"], "BLOCKED")
                with self.assertRaisesRegex(studio.StudioError, "Run is BLOCKED"):
                    studio.register_theme(self.repo, "fixture", root)
                self.assertFalse((self.repo / "themes/registry.json").exists())
                completion = studio.complete_scope(root, "Bounded fixture task", ["implementation.md"])
                self.assertEqual(completion["status"], "PASS")
                self.assertEqual(completion["fullThemeCheck"]["status"], "BLOCKED")

    def test_each_declared_critical_state_needs_an_applicable_viewport(self):
        root = fixture_run(self.repo, self.theme)
        coverage = studio.read_json(root / "coverage.json")
        surface = coverage["surfaces"][0]
        surface["states"].append("recovery")
        surface["applicableCases"] = [{"state": case["state"], "viewport": case["viewport"]} for case in surface["cases"]]
        surface["excludedCases"] = [{"state": "recovery", "viewport": viewport,
                                    "reason": "Synthetic omission of an entire declared recovery state"}
                                   for viewport in surface["viewports"]]
        write_json(root / "coverage.json", coverage)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        with self.assertRaisesRegex(studio.StudioError, "Critical state has no applicable case: recovery"):
            studio.check_run(root)

    def test_empty_worker_action_allowlist_is_not_replaced_with_write_access(self):
        root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
        (root / "component.md").write_text("Synthetic owned artifact\n", encoding="utf-8")
        for supplied, expected in ((None, ["read", "write-owned", "publish-evidence"]), ([], []), (["read"], ["read"])):
            with self.subTest(actions=supplied):
                packet = studio.worker_packet(root, "ui-implementer", "Inspect the component", ["component.md"],
                                              allowed_actions=supplied)
                self.assertEqual(packet["allowedActions"], expected)

    def test_changed_requirement_source_invalidates_dependent_work(self):
        contract = self.repo / "UI-Design-Studio-v1.4.0-Cortex-Remediation.md"
        contract.write_text("Synthetic original requirements\n", encoding="utf-8")
        root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
        contract.write_text("Synthetic changed requirements\n", encoding="utf-8")
        for legacy in (False, True):
            with self.subTest(legacy_manifest=legacy):
                if legacy:
                    manifest = studio.read_json(root / "manifest.json")
                    manifest["graph"] = [node for node in manifest["graph"] if node["id"] != "remediation-contract"]
                    for node in manifest["graph"]:
                        node["dependsOn"] = [parent for parent in node["dependsOn"] if parent != "remediation-contract"]
                    write_json(root / "manifest.json", manifest)
                resumed = studio.resume_check(root)
                self.assertEqual(resumed["status"], "BLOCKED")
                self.assertEqual(set(resumed["staleNodes"]),
                    {"remediation-contract", "project-context", "model-routing", "run", "coverage",
                     "evidence", "assessment", "approvals"})

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Requires POSIX FIFO support")
    def test_nonregular_record_and_hash_reads_fail_without_waiting_for_a_writer(self):
        path = self.repo / "record.json"
        os.mkfifo(path)
        for reader in ("read_json", "sha_file"):
            with self.subTest(reader=reader):
                code = ("from test_studio import studio\n"
                        "try:\n"
                        f"    studio.{reader}({str(path)!r})\n"
                        "except studio.StudioError as exc:\n"
                        "    print(exc)\n"
                        "else:\n"
                        "    raise SystemExit('Nonregular record was accepted')\n")
                result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parent,
                                        capture_output=True, text=True, timeout=2, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Not a regular file", result.stdout)


if __name__ == "__main__":
    unittest.main()
