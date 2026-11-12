"""Meaningful fixture tests for theme isolation, compilation, evidence and lifecycle.

All passing review artifacts below are explicitly synthetic test fixtures. They
are never shipped as evidence for a real application's usability or performance.
"""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / ".omp/skills/ui-design-studio/scripts/studio.py"
spec = importlib.util.spec_from_file_location("studio", SCRIPT)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def color(hex_value):
    value = hex_value.lstrip("#")
    return {"$type": "color", "$value": {"colorSpace": "srgb", "components": [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)], "alpha": 1}}


def fixture_theme(repo, theme_id="fixture"):
    theme = repo / "themes" / theme_id
    theme.mkdir(parents=True)
    tokens = {"color": {name: color("#ffffff" if name in ("background", "surface", "on-primary", "on-danger", "on-success") else "#111111") for name in ("background", "surface", "text", "muted", "primary", "on-primary", "border", "focus", "danger", "on-danger", "success", "on-success")},
              "space": {str(x): {"$type": "dimension", "$value": {"value": x / 4, "unit": "rem"}} for x in (1, 2, 3, 4, 6, 8)},
              "radius": {key: {"$type": "dimension", "$value": {"value": n, "unit": "px"}} for key, n in (("sm", 2), ("md", 4), ("lg", 8))},
              "motion": {"fast": {"$type": "duration", "$value": {"value": 120, "unit": "ms"}}},
              "font": {"family": {"$type": "fontFamily", "$value": ["system-ui", "Segoe UI", "sans-serif"]}}}
    manifest = {"schemaVersion": "1.0", "id": theme_id, "name": "Fixture theme", "version": "1.0.0", "description": "Synthetic validation fixture", "author": "Test suite", "license": "MIT", "tokens": "tokens.json", "styles": ["tokens.css", "theme.css"], "icons": "icons.svg", "preview": "preview.html", "compatibility": {"themeApi": "1", "framework": "any"}, "budgets": {"maxRawBytes": 131072, "maxGzipBytes": 40960}, "contrastPairs": [{"foreground": f, "background": b, "minimum": m} for f, b, m in studio.REQUIRED_CONTRASTS]}
    write_json(theme / "tokens.json", tokens)
    write_json(theme / "theme.json", manifest)
    (theme / "theme.css").write_text(f'[data-ui-theme="{theme_id}"] .button {{ color: var(--ui-color-text); }}\n', encoding="utf-8")
    (theme / "icons.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><symbol id="check" viewBox="0 0 24 24"><path d="M4 12l5 5L20 6"/></symbol></svg>', encoding="utf-8")
    (theme / "preview.html").write_text(f'<!doctype html><title>Fixture</title><main data-ui-theme="{theme_id}">Synthetic fixture</main>', encoding="utf-8")
    for file in ("README.md", "LICENSE.txt", "CHANGELOG.md"):
        (theme / file).write_text("Synthetic test fixture\n", encoding="utf-8")
    studio.build_theme(theme)
    return theme


def fixture_run(repo, theme, mode="guided", action="new"):
    theme_id = studio.read_json(theme / "theme.json")["id"]
    result = studio.init_run(repo, mode=mode, action=action, theme_id=theme_id)
    root = Path(result["run"])
    run = studio.read_json(root / "run.json")
    run.update(status="passed", phase="finalize", implementer="fixture-implementer", themeDigest=studio.check_theme(theme)["themeDigest"])
    (root / "project-context.md").write_text("Synthetic project requirements for unit tests. Offline operation is required. Source: fixture requirements.\n", encoding="utf-8")
    run["projectContext"].update(status="resolved", offline="required", sources=["fixture requirements"], sha256=studio.sha_file(root / "project-context.md"))
    (root / "model-routing.md").write_text("Synthetic routing fixture; no actual model calls were made.\n", encoding="utf-8")
    run["modelRouting"].update(status="resolved", sessionModel="fixture/model", sessionThinking="high",
        assignments=[{"agent": name, "model": "fixture/model", "thinking": "high", "rationale": "Synthetic model-routing fixture"} for name in sorted(studio.SPECIALIST_AGENTS)],
        sha256=studio.sha_file(root / "model-routing.md"))
    evidence = []
    for kind in sorted(studio.REQUIRED_EVIDENCE):
        path = root / f"{kind}.md"
        path.write_text(f"Synthetic {kind} evidence for unit tests, not a real browser result.\n", encoding="utf-8")
        evidence.append({"id": kind, "kind": kind, "path": path.name, "sha256": studio.sha_file(path), "status": "passed", "reviewer": "fixture-independent-reviewer", "recordedAt": studio.now()})
    run["evidence"] = evidence
    for file in ("plan.html", "mockup.html", "implementation.md"):
        (root / file).write_text("Synthetic fixture, not a real application result.\n", encoding="utf-8")
    coverage = {"schemaVersion": "1.0", "inventoryComplete": True, "surfaces": [{"id": "settings", "kind": "page", "route": "/settings", "states": ["ready", "error"], "viewports": ["mobile", "desktop"], "cases": [{"state": state, "viewport": viewport, "mockup": "mockup.html", "implementation": "implementation.md", "qaEvidence": ["visual", "integration"]} for state in ("ready", "error") for viewport in ("mobile", "desktop")]}]}
    decisions = {"schemaVersion": "1.0", "decisions": [{"stage": stage, "actor": "user" if mode == "guided" else "agent-yolo", "outcome": "approved", "rationale": "Synthetic test fixture decision", "inputs": files, "inputsDigest": studio.file_digest(root, files)} for stage, files in (("plan", ["plan.html"]), ("design", ["plan.html", "mockup.html"]))]}
    write_json(root / "run.json", run)
    write_json(root / "coverage.json", coverage)
    write_json(root / "decisions.json", decisions)
    review = studio.check_run(root)
    decisions["decisions"].append({"stage": "finalize", "actor": "director" if mode == "guided" else "agent-yolo", "outcome": "approved", "rationale": "Synthetic independent-review fixture", "inputsDigest": review["reviewDigest"]})
    write_json(root / "decisions.json", decisions)
    return root


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ui-studio-tests-")
        self.repo = Path(self.temp.name)
        self.theme = fixture_theme(self.repo)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_theme_compile_and_repeat(self):
        check = studio.check_theme(self.theme)
        self.assertEqual(check["status"], "PASS")
        original = (self.theme / "tokens.css").read_bytes()
        studio.build_theme(self.theme)
        self.assertEqual(original, (self.theme / "tokens.css").read_bytes())
        self.assertIn(b'"Segoe UI"', original)
        self.assertEqual(len(check["contrast"]), len(studio.REQUIRED_CONTRASTS))

    def test_alias_cycle_fails(self):
        tokens = studio.read_json(self.theme / "tokens.json")
        tokens["color"]["text"]["$value"] = "{color.muted}"
        tokens["color"]["muted"]["$value"] = "{color.text}"
        write_json(self.theme / "tokens.json", tokens)
        with self.assertRaisesRegex(studio.StudioError, "alias cycle"):
            studio.build_theme(self.theme)

    def test_alias_type_mismatch_fails(self):
        tokens = studio.read_json(self.theme / "tokens.json")
        tokens["color"]["text"]["$value"] = "{space.1}"
        write_json(self.theme / "tokens.json", tokens)
        with self.assertRaisesRegex(studio.StudioError, "type mismatch"):
            studio.build_theme(self.theme)

    def test_css_variable_name_collision_fails(self):
        tokens = studio.read_json(self.theme / "tokens.json")
        tokens["color-text"] = color("#111111")
        write_json(self.theme / "tokens.json", tokens)
        with self.assertRaisesRegex(studio.StudioError, "collide"):
            studio.build_theme(self.theme)

    def test_font_injection_fails(self):
        tokens = studio.read_json(self.theme / "tokens.json")
        tokens["font"]["family"]["$value"] = ["system-ui; } body { display:none"]
        write_json(self.theme / "tokens.json", tokens)
        with self.assertRaisesRegex(studio.StudioError, "fontFamily"):
            studio.build_theme(self.theme)

    def test_low_contrast_fails(self):
        tokens = studio.read_json(self.theme / "tokens.json")
        tokens["color"]["text"] = color("#bbbbbb")
        write_json(self.theme / "tokens.json", tokens)
        studio.build_theme(self.theme)
        with self.assertRaisesRegex(studio.StudioError, "Contrast failure"):
            studio.check_theme(self.theme)

    def test_alpha_contrast_not_claimed(self):
        tokens = studio.read_json(self.theme / "tokens.json")
        tokens["color"]["text"]["$value"]["alpha"] = 0.5
        write_json(self.theme / "tokens.json", tokens)
        studio.build_theme(self.theme)
        with self.assertRaisesRegex(studio.StudioError, "opaque"):
            studio.check_theme(self.theme)

    def test_missing_required_contrast_fails(self):
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["contrastPairs"] = manifest["contrastPairs"][:-1]
        write_json(self.theme / "theme.json", manifest)
        with self.assertRaisesRegex(studio.StudioError, "Required contrast"):
            studio.check_theme(self.theme)

    def test_stale_generated_css_fails(self):
        (self.theme / "tokens.css").write_text("/* edited */", encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "stale"):
            studio.check_theme(self.theme)

    def test_external_css_and_unscoped_rules_fail(self):
        for css in ('@import "https://example.org/a.css";', '@\\import "https://example.org/a.css";', 'body { margin: 0; }', '[data-ui-theme="fixture"] { background: url(https://example.org/a.png); }', '[data-ui-theme="fixture"] { behavior: url(local.htc); }'):
            with self.subTest(css=css):
                (self.theme / "theme.css").write_text(css, encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_scroll_behavior_and_real_fieldstone_are_supported(self):
        (self.theme / "theme.css").write_text('[data-ui-theme="fixture"] { scroll-behavior: auto; }', encoding="utf-8")
        self.assertEqual(studio.check_theme(self.theme)["status"], "PASS")
        specimen = SCRIPT.parent.parent / "assets/example-theme"
        self.assertTrue(specimen.is_dir(), "Distribution must contain the real Fieldstone specimen")
        self.assertEqual(studio.check_theme(specimen)["status"], "PASS")

    def test_real_specimen_scaffolds_with_new_scope_and_no_registration(self):
        result = studio.theme_new(self.repo, "coastal-test", "Coastal Test")
        target = Path(result["theme"])
        check = studio.check_theme(target)
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(check["themeId"], "coastal-test")
        self.assertIn('[data-ui-theme="coastal-test"]', (target / "theme.css").read_text())
        self.assertNotIn('[data-ui-theme="fieldstone"]', (target / "theme.css").read_text())
        self.assertFalse((self.repo / "themes/registry.json").exists())

    def test_css_asset_resolves_relative_to_stylesheet_directory(self):
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["styles"].append("nested/cards.css")
        manifest["assets"] = ["pattern.svg"]
        write_json(self.theme / "theme.json", manifest)
        (self.theme / "nested").mkdir()
        (self.theme / "nested/cards.css").write_text('[data-ui-theme="fixture"] .card { background-image: url("pattern.svg"); }', encoding="utf-8")
        (self.theme / "pattern.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "Missing referenced file: nested/pattern.svg"):
            studio.check_theme(self.theme)
        (self.theme / "nested/pattern.svg").write_bytes((self.theme / "pattern.svg").read_bytes())
        manifest["assets"].append("nested/pattern.svg")
        write_json(self.theme / "theme.json", manifest)
        self.assertEqual(studio.check_theme(self.theme)["status"], "PASS")

    def test_uppercase_svg_asset_is_scanned(self):
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["assets"] = ["extra.SVG"]
        write_json(self.theme / "theme.json", manifest)
        (self.theme / "extra.SVG").write_text('<svg><script>alert(1)</script></svg>', encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "passive-vector"):
            studio.check_theme(self.theme)

    def test_active_svg_fails(self):
        for svg in ('<svg><script>alert(1)</script></svg>', '<svg onload="alert(1)"/>', '<svg><use href="https://example.org/icon.svg"/></svg>', '<!DOCTYPE svg><svg/>'):
            with self.subTest(svg=svg):
                (self.theme / "icons.svg").write_text(svg, encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_path_traversal_and_symlink_fail(self):
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["icons"] = "../outside.svg"
        write_json(self.theme / "theme.json", manifest)
        with self.assertRaisesRegex(studio.StudioError, "Unsafe relative"):
            studio.check_theme(self.theme)
        manifest["icons"] = "icons.svg"
        write_json(self.theme / "theme.json", manifest)
        outside = self.repo / "outside.svg"
        outside.write_text("<svg/>", encoding="utf-8")
        (self.theme / "icons.svg").unlink()
        (self.theme / "icons.svg").symlink_to(outside)
        with self.assertRaisesRegex(studio.StudioError, "Symlink"):
            studio.check_theme(self.theme)

    def test_budget_enforced(self):
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["budgets"]["maxRawBytes"] = 10
        write_json(self.theme / "theme.json", manifest)
        with self.assertRaisesRegex(studio.StudioError, "exceeded"):
            studio.check_theme(self.theme)

    def test_package_reproducible_and_no_unrelated_files(self):
        (self.theme / "secret.env").write_text("SYNTHETIC=not-packaged", encoding="utf-8")
        one, two = self.repo / "one.zip", self.repo / "two.zip"
        studio.package_theme(self.theme, one)
        studio.package_theme(self.theme, two)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        with zipfile.ZipFile(one) as archive:
            self.assertNotIn("fixture/secret.env", archive.namelist())
            self.assertIn("fixture/checksums.sha256", archive.namelist())

    def test_new_run_is_blocked_and_does_not_register(self):
        run = studio.init_run(self.repo, theme_id="fixture")
        self.assertEqual(studio.check_run(run["run"])["status"], "BLOCKED")
        self.assertFalse((self.repo / "themes/registry.json").exists())
        record = studio.read_json(Path(run["run"]) / "run.json")
        self.assertEqual(record["schemaVersion"], "1.1")
        self.assertNotIn("profile", record)
        self.assertEqual(record["modelPolicy"], "auto-models")
        self.assertEqual(record["modelRouting"]["status"], "pending")
        self.assertEqual(record["projectContext"]["offline"], "unknown")

    def test_profile_free_cli_and_model_policy_precedence(self):
        args = studio.parser().parse_args(["init-run", "--repo", str(self.repo), "--theme-id", "fixture"])
        self.assertIsNone(args.profile)
        self.assertIsNone(args.models)
        write_json(self.repo / "ui-design-studio.json", {"profile": "tada", "modelPolicy": "current-model"})
        root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
        record = studio.read_json(root / "run.json")
        self.assertEqual(record["modelPolicy"], "current-model")
        self.assertNotIn("profile", record)
        self.assertEqual(record["projectContext"]["offline"], "unknown")
        override = Path(studio.init_run(self.repo, theme_id="fixture", model_policy="auto-models")["run"])
        self.assertEqual(studio.read_json(override / "run.json")["modelPolicy"], "auto-models")
        with self.assertRaisesRegex(studio.StudioError, "Model policy"):
            studio.init_run(self.repo, theme_id="fixture", model_policy="invented-policy")

    def test_unresolved_project_context_blocks_complete_fixture(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        record["projectContext"].update(status="pending", offline="unknown", sources=[], sha256=None)
        write_json(root / "run.json", record)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        result = studio.check_run(root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("Project requirements" in message for message in result["pending"]))
        self.assertTrue(any("offline requirement" in message for message in result["pending"]))

    def test_project_context_bytes_and_fields_invalidate_final_approval(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        (root / "project-context.md").write_text("Changed synthetic requirement\n", encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "Project context changed"):
            studio.check_run(root)
        result = studio.context_digest(root)
        self.assertEqual(result["sha256"], studio.sha_file(root / "project-context.md"))
        record["projectContext"]["sha256"] = result["sha256"]
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "Stale/missing finalize"):
            studio.check_run(root)

    def test_pending_model_routing_blocks_complete_fixture(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        record["modelRouting"]["status"] = "pending"
        write_json(root / "run.json", record)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        result = studio.check_run(root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("model routing" in message for message in result["pending"]))

    def test_current_model_rejects_model_or_thinking_changes(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        record["modelPolicy"] = "current-model"
        record["modelRouting"]["assignments"][0]["model"] = "fixture/other-model"
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "current-model must retain"):
            studio.check_run(root)
        record["modelRouting"]["assignments"][0].update(model="fixture/model", thinking="medium")
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "current-model must retain"):
            studio.check_run(root)

    def test_model_routing_requires_every_role_and_exact_identity(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        original = copy.deepcopy(record["modelRouting"]["assignments"])
        record["modelRouting"]["assignments"].pop()
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "all seven"):
            studio.check_run(root)
        record["modelRouting"]["assignments"] = original
        record["modelRouting"]["assignments"][0]["model"] = "@task"
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "exact provider/model"):
            studio.check_run(root)
        record["modelRouting"]["assignments"][0] = copy.deepcopy(original[1])
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "duplicate"):
            studio.check_run(root)

    def test_model_routing_content_and_policy_bound_to_approval(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        (root / "model-routing.md").write_text("Changed synthetic routing evidence\n", encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "Model routing changed"):
            studio.check_run(root)
        record["modelRouting"]["sha256"] = studio.models_digest(root)["sha256"]
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "Stale/missing finalize"):
            studio.check_run(root)

    def test_offline_waiver_follows_resolved_project_requirement(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        offline = next(entry for entry in record["evidence"] if entry["kind"] == "offline")
        offline.update(status="not-applicable", reason="Synthetic project brief requires an online-only integration")
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "explicitly non-required offline"):
            studio.check_run(root)
        record["projectContext"]["offline"] = "not-required"
        write_json(root / "run.json", record)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        self.assertEqual(studio.check_run(root)["pending"], ["Missing approved finalize decision"])

    def test_legacy_run_approvals_remain_readable_and_tada_offline_cannot_be_waived(self):
        root = fixture_run(self.repo, self.theme)
        record = studio.read_json(root / "run.json")
        record.update(schemaVersion="1.0", profile="tada")
        record.pop("projectContext")
        record.pop("modelPolicy")
        record.pop("modelRouting")
        write_json(root / "run.json", record)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        result = studio.check_run(root)
        decisions["decisions"].append({"stage": "finalize", "actor": "director", "outcome": "approved", "rationale": "Synthetic legacy approval", "inputsDigest": result["reviewDigest"]})
        write_json(root / "decisions.json", decisions)
        self.assertEqual(studio.check_run(root)["status"], "PASS")
        offline = next(entry for entry in record["evidence"] if entry["kind"] == "offline")
        offline.update(status="not-applicable", reason="Attempted synthetic waiver")
        write_json(root / "run.json", record)
        with self.assertRaisesRegex(studio.StudioError, "explicitly non-required offline"):
            studio.check_run(root)

    def test_complete_fixture_passes_and_independent_review_required(self):
        root = fixture_run(self.repo, self.theme)
        self.assertEqual(studio.check_run(root)["status"], "PASS")
        run = studio.read_json(root / "run.json")
        run["implementer"] = "fixture-independent-reviewer"
        write_json(root / "run.json", run)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [item for item in decisions["decisions"] if item["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        self.assertEqual(studio.check_run(root)["status"], "BLOCKED")

    def test_latest_decision_supersedes_prior_approval(self):
        root = fixture_run(self.repo, self.theme)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"].append({"stage": "plan", "actor": "user", "outcome": "rejected", "rationale": "User changed their mind"})
        decisions["decisions"] = [item for item in decisions["decisions"] if item["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        result = studio.check_run(root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Missing approved plan decision", result["pending"])

    def test_reapproved_plan_invalidates_downstream_design(self):
        root = fixture_run(self.repo, self.theme)
        (root / "plan.html").write_text("Updated concept fixture", encoding="utf-8")
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"].append({"stage": "plan", "actor": "user", "outcome": "approved", "rationale": "Synthetic re-review", "inputs": ["plan.html"], "inputsDigest": studio.file_digest(root, ["plan.html"])})
        write_json(root / "decisions.json", decisions)
        with self.assertRaisesRegex(studio.StudioError, "Stale/missing (design|finalize)"):
            studio.check_run(root)
        decisions["decisions"] = [item for item in decisions["decisions"] if item["stage"] != "finalize"]
        decisions["decisions"].append({"stage": "design", "actor": "user", "outcome": "approved", "rationale": "Synthetic downstream re-review", "inputs": ["plan.html", "mockup.html"], "inputsDigest": studio.file_digest(root, ["plan.html", "mockup.html"])})
        write_json(root / "decisions.json", decisions)
        result = studio.check_run(root)
        self.assertEqual(result["status"], "BLOCKED")
        decisions["decisions"].append({"stage": "finalize", "actor": "director", "outcome": "approved", "rationale": "Synthetic updated final review", "inputsDigest": result["reviewDigest"]})
        write_json(root / "decisions.json", decisions)
        self.assertEqual(studio.check_run(root)["status"], "PASS")

    def test_evidence_tamper_invalidates_run(self):
        root = fixture_run(self.repo, self.theme)
        (root / "integration.md").write_text("Changed fixture", encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "Evidence changed"):
            studio.check_run(root)

    def test_missing_coverage_case_blocks(self):
        root = fixture_run(self.repo, self.theme)
        coverage = studio.read_json(root / "coverage.json")
        coverage["surfaces"][0]["cases"].pop()
        write_json(root / "coverage.json", coverage)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [x for x in decisions["decisions"] if x["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        result = studio.check_run(root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("missing case" in item for item in result["pending"]))

    def test_plan_input_change_invalidates_approval(self):
        root = fixture_run(self.repo, self.theme)
        (root / "plan.html").write_text("Different concept fixture", encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "Stale/missing plan"):
            studio.check_run(root)

    def test_guided_cannot_fake_yolo_plan_approval(self):
        root = fixture_run(self.repo, self.theme)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"][0]["actor"] = "agent-yolo"
        write_json(root / "decisions.json", decisions)
        with self.assertRaisesRegex(studio.StudioError, "Guided runs"):
            studio.check_run(root)

    def test_first_registration_default_later_preserves_and_explicit_changes(self):
        first_run = fixture_run(self.repo, self.theme)
        first = studio.register_theme(self.repo, "fixture", first_run)
        self.assertEqual(first["defaultTheme"], "fixture")
        other = fixture_theme(self.repo, "second")
        second_run = fixture_run(self.repo, other)
        second = studio.register_theme(self.repo, "second", second_run)
        self.assertEqual(second["defaultTheme"], "fixture")
        repeat = studio.register_theme(self.repo, "second", second_run, make_default=True)
        self.assertEqual(repeat["defaultTheme"], "fixture")
        self.assertTrue(repeat["alreadyRegistered"])
        third = fixture_theme(self.repo, "third")
        third_run = fixture_run(self.repo, third)
        changed = studio.register_theme(self.repo, "third", third_run, make_default=True)
        self.assertEqual(changed["defaultTheme"], "third")
        self.assertTrue(Path(changed["backup"]).is_file())

    def test_new_registration_collision_is_rechecked_at_finalization(self):
        first_run = fixture_run(self.repo, self.theme)
        overlapping_run = fixture_run(self.repo, self.theme)
        studio.register_theme(self.repo, "fixture", first_run)
        with self.assertRaisesRegex(studio.StudioError, "New theme ID is already registered"):
            studio.register_theme(self.repo, "fixture", overlapping_run)

    def test_changed_default_requires_version_bump_and_rejects_old_replay(self):
        first_run = fixture_run(self.repo, self.theme)
        studio.register_theme(self.repo, "fixture", first_run)
        original_css = (self.theme / "theme.css").read_text(encoding="utf-8")
        (self.theme / "theme.css").write_text(original_css + '[data-ui-theme="fixture"] .new { padding: 1rem; }', encoding="utf-8")
        same_version_run = fixture_run(self.repo, self.theme, action="modify-default")
        with self.assertRaisesRegex(studio.StudioError, "newer semantic version"):
            studio.register_theme(self.repo, "fixture", same_version_run)
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["version"] = "1.0.1"
        write_json(self.theme / "theme.json", manifest)
        bumped_run = fixture_run(self.repo, self.theme, action="modify-default")
        self.assertEqual(studio.register_theme(self.repo, "fixture", bumped_run)["status"], "PASS")
        manifest["version"] = "1.0.0"
        write_json(self.theme / "theme.json", manifest)
        with self.assertRaisesRegex(studio.StudioError, "newer semantic version"):
            studio.register_theme(self.repo, "fixture", same_version_run)

    def test_registration_requires_manifest_id_to_match_directory(self):
        root = fixture_run(self.repo, self.theme)
        other = fixture_theme(self.repo, "different")
        for file in ("theme.json", "theme.css", "tokens.css"):
            (self.theme / file).write_bytes((other / file).read_bytes())
        with self.assertRaisesRegex(studio.StudioError, "must match theme.json"):
            studio.register_theme(self.repo, "fixture", root)

    def test_guided_later_run_must_choose_action(self):
        root = fixture_run(self.repo, self.theme)
        studio.register_theme(self.repo, "fixture", root)
        with self.assertRaisesRegex(studio.StudioError, "must choose"):
            studio.init_run(self.repo, "guided", "generic", "auto", "second")
        result = studio.init_run(self.repo, "yolo", "generic", "auto", "second")
        self.assertEqual(result["themeAction"], "new")

    def test_registration_rejects_changed_theme(self):
        root = fixture_run(self.repo, self.theme)
        (self.theme / "theme.css").write_text('[data-ui-theme="fixture"] .button { padding: 1rem; }', encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "digest does not match"):
            studio.register_theme(self.repo, "fixture", root)

    def test_malformed_registry_is_never_overwritten(self):
        root = fixture_run(self.repo, self.theme)
        path = self.repo / "themes/registry.json"
        path.write_text("{malformed", encoding="utf-8")
        with self.assertRaises(studio.StudioError):
            studio.register_theme(self.repo, "fixture", root)
        self.assertEqual(path.read_text(), "{malformed")

    def test_registration_respects_project_budget_and_concurrent_lock(self):
        root = fixture_run(self.repo, self.theme)
        write_json(self.repo / "ui-design-studio.json", {"schemaVersion": "1.0", "budgets": {"maxThemeRawBytes": 10}})
        with self.assertRaisesRegex(studio.StudioError, "Project maxThemeRawBytes exceeded"):
            studio.register_theme(self.repo, "fixture", root)
        (self.repo / "ui-design-studio.json").unlink()
        lock = self.repo / "themes/.registry.lock"
        lock.write_text("Synthetic active finalization", encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "Registry is locked"):
            studio.register_theme(self.repo, "fixture", root)
        self.assertTrue(lock.exists())


class ModelRoutingTests(unittest.TestCase):
    """Exercise reversible native files using synthetic provider metadata."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ui-model-routing-tests-")
        self.repo = Path(self.temp.name)
        self.root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
        self.record = studio.read_json(self.root / "run.json")
        self.record["modelRouting"].update(sessionModel="fixture/director", sessionThinking="high",
            assignments=[{"agent": name, "model": "fixture/design", "thinking": "high", "rationale": "Synthetic available-model fixture"} for name in sorted(studio.SPECIALIST_AGENTS)])
        write_json(self.root / "run.json", self.record)
        self.original = {}
        for name in sorted(studio.SPECIALIST_AGENTS):
            path = self.repo / ".omp/agents" / f"{name}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            data = (f"---\nname: {name}\ndescription: Synthetic specialist\nmodel:\n  - legacy/model\nthinking-level: low\ntools: read, edit\n---\n\nKeep this exact agent body.\n").encode()
            path.write_bytes(data)
            path.chmod(0o640)
            self.original[path] = (data, 0o640)
        self.which = mock.patch.object(studio.shutil, "which", return_value="/fixture/omp").start()
        self.native = mock.patch.object(studio.subprocess, "run", return_value=subprocess.CompletedProcess([], 0,
            stdout=json.dumps({"key": "task.agentModelOverrides", "value": {}, "type": "record", "description": "Synthetic effective settings"}), stderr="")).start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(self.temp.cleanup)

    def snapshot(self):
        return {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in self.original}

    def test_apply_is_idempotent_and_restore_recovers_exact_bytes_and_modes(self):
        before_run = (self.root / "run.json").read_bytes()
        result = studio.models_apply(self.repo, self.root)
        self.assertFalse(result["alreadyApplied"])
        for path in self.original:
            data = path.read_bytes()
            self.assertIn(b'model: "fixture/design"', data)
            self.assertIn(b'thinking: "high"', data)
            self.assertNotIn(b"legacy/model", data)
            self.assertIn(b"tools: read, edit", data)
            self.assertTrue(data.endswith(b"---\n\nKeep this exact agent body.\n"))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertEqual((self.root / "run.json").read_bytes(), before_run)
        applied = self.snapshot()
        self.assertTrue(studio.models_apply(self.repo, self.root)["alreadyApplied"])
        self.assertEqual(applied, self.snapshot())
        restored = studio.models_restore(self.repo, self.root)
        self.assertFalse(restored["alreadyRestored"])
        self.assertEqual(self.snapshot(), self.original)
        self.assertTrue(studio.models_restore(self.repo, self.root)["alreadyRestored"])

    def test_current_model_and_provider_default_are_applied_without_thinking_override(self):
        self.record["modelPolicy"] = "current-model"
        self.record["modelRouting"]["sessionThinking"] = "provider-default"
        for item in self.record["modelRouting"]["assignments"]:
            item.update(model="fixture/director", thinking="provider-default")
        write_json(self.root / "run.json", self.record)
        studio.models_apply(self.repo, self.root)
        for path in self.original:
            self.assertIn(b'model: "fixture/director"', path.read_bytes())
            self.assertNotIn(b"thinking", path.read_bytes())
        studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)

    def test_later_user_edit_blocks_restore_and_reapply_without_partial_writes(self):
        studio.models_apply(self.repo, self.root)
        path = next(iter(self.original))
        path.write_bytes(path.read_bytes() + b"Later user instruction\n")
        before = self.snapshot()
        with self.assertRaisesRegex(studio.StudioError, "changed after routing"):
            studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), before)
        with self.assertRaisesRegex(studio.StudioError, "changed after routing"):
            studio.models_apply(self.repo, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_other_run_and_changed_mapping_cannot_replace_active_routing(self):
        studio.models_apply(self.repo, self.root)
        other = Path(studio.init_run(self.repo, theme_id="second")["run"])
        record = studio.read_json(other / "run.json")
        record["modelRouting"] = copy.deepcopy(self.record["modelRouting"])
        write_json(other / "run.json", record)
        before = self.snapshot()
        with self.assertRaisesRegex(studio.StudioError, "Another run"):
            studio.models_apply(self.repo, other)
        with self.assertRaisesRegex(studio.StudioError, "Another run"):
            studio.models_restore(self.repo, other)
        self.record["modelRouting"]["assignments"][0]["model"] = "fixture/revised"
        write_json(self.root / "run.json", self.record)
        with self.assertRaisesRegex(studio.StudioError, "mapping changed"):
            studio.models_apply(self.repo, self.root)
        self.assertEqual(self.snapshot(), before)
        studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)

    def test_apply_and_restore_write_failures_roll_back_whole_file_change(self):
        original_write = studio.atomic_bytes
        calls = {"count": 0}
        def fail_second(path, data, mode):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("Synthetic atomic write failure")
            return original_write(path, data, mode)
        with mock.patch.object(studio, "atomic_bytes", side_effect=fail_second):
            with self.assertRaises(OSError):
                studio.models_apply(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)
        self.assertFalse((self.repo / studio.ROUTING_DIRECTORY / "active.json").exists())
        studio.models_apply(self.repo, self.root)
        applied = self.snapshot()
        calls["count"] = 0
        with mock.patch.object(studio, "atomic_bytes", side_effect=fail_second):
            with self.assertRaises(OSError):
                studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), applied)
        self.assertTrue((self.repo / studio.ROUTING_DIRECTORY / "active.json").exists())
        studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)

    def test_effective_agent_override_or_unreadable_settings_blocks_apply(self):
        self.native.return_value.stdout = json.dumps({"key": "task.agentModelOverrides", "value": {"ui-art-director": "@operator-choice"}})
        with self.assertRaisesRegex(studio.StudioError, "Higher-priority"):
            studio.models_apply(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)
        self.assertFalse((self.repo / studio.ROUTING_DIRECTORY).exists())
        self.native.return_value.stdout = "not JSON"
        with self.assertRaisesRegex(studio.StudioError, "not valid JSON"):
            studio.models_apply(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)

    def test_symlinks_invalid_thinking_and_aliases_are_refused(self):
        first = self.record["modelRouting"]["assignments"][0]
        first["thinking"] = "invented-effort"
        write_json(self.root / "run.json", self.record)
        with self.assertRaisesRegex(studio.StudioError, "Unsupported OMP thinking"):
            studio.models_apply(self.repo, self.root)
        first.update(thinking="high", model="@task")
        write_json(self.root / "run.json", self.record)
        with self.assertRaisesRegex(studio.StudioError, "exact provider/model"):
            studio.models_apply(self.repo, self.root)
        first["model"] = "fixture/design"
        write_json(self.root / "run.json", self.record)
        path = next(iter(self.original))
        outside = self.repo / "unrelated-agent.md"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(studio.StudioError, "Symlink"):
            studio.models_apply(self.repo, self.root)
        self.assertEqual(outside.read_bytes(), self.original[path][0])

    def test_prepared_journal_can_recover_an_interrupted_application(self):
        result = studio.models_apply(self.repo, self.root)
        path = Path(result["journal"])
        journal = studio.read_json(path)
        journal["status"] = "prepared"
        write_json(path, journal)
        with self.assertRaisesRegex(studio.StudioError, "interrupted"):
            studio.models_apply(self.repo, self.root)
        studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)

    def test_advisory_lock_blocks_live_operation_but_reuses_retained_lockfile(self):
        with studio.routing_lock(self.repo) as directory:
            self.assertTrue((directory / "operation.lock").is_file())
            with self.assertRaisesRegex(studio.StudioError, "live operation"):
                with studio.routing_lock(self.repo):
                    self.fail("A concurrent routing operation acquired the lock")
        self.assertTrue((directory / "operation.lock").is_file())
        # Retained metadata is not an active lock; OS ownership controls access.
        (directory / "operation.lock").write_text("pid=99999999\n")
        studio.models_apply(self.repo, self.root)
        studio.models_restore(self.repo, self.root)
        self.assertEqual(self.snapshot(), self.original)


if __name__ == "__main__":
    unittest.main()
