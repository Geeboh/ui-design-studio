"""Behavior regressions for offline CSS assets and resume invalidation."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_studio import fixture_run, fixture_theme, studio, write_json


CATEGORY_NODES = {
    "run", "project-context", "model-routing", "coverage", "evidence", "assessment", "approvals",
}


class FreezeIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ui-freeze-integrity-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.theme = fixture_theme(self.repo)
        self.environment = {
            "python": "fixture-python", "node": None, "platform": "fixture-platform",
            "git": {"revision": None, "dirty": False},
        }
        environment = mock.patch.object(studio, "_environment_facts", return_value=self.environment)
        environment.start()
        self.addCleanup(environment.stop)

    def _approve_current_run(self, root):
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        review = studio.check_run(root)
        self.assertEqual(review["status"], "BLOCKED")
        decisions["decisions"].append({
            "stage": "finalize", "actor": "director", "outcome": "approved",
            "rationale": "Synthetic integrity regression approval",
            "inputsDigest": review["reviewDigest"],
        })
        write_json(root / "decisions.json", decisions)

    def _run_with_evidence_input(self):
        root = fixture_run(self.repo, self.theme)
        (root / "evidence-source.txt").write_text("Synthetic evidence input\n", encoding="utf-8")
        record = studio.read_json(root / "run.json")
        visual = next(entry for entry in record["evidence"] if entry["kind"] == "visual")
        visual["inputs"] = ["evidence-source.txt"]
        visual["inputsDigest"] = studio.file_digest(root, visual["inputs"])
        write_json(root / "run.json", record)
        self._approve_current_run(root)
        return root

    def _run_with_shared_dependency(self, relative):
        root = self._run_with_evidence_input() if relative == "evidence-source.txt" else fixture_run(self.repo, self.theme)
        coverage = studio.read_json(root / "coverage.json")
        for case in coverage["surfaces"][0]["cases"]:
            case["implementation"] = relative
        write_json(root / "coverage.json", coverage)
        decisions = studio.read_json(root / "decisions.json")
        for decision in decisions["decisions"]:
            if decision["stage"] in ("plan", "design"):
                decision["inputs"].append(relative)
                decision["inputsDigest"] = studio.file_digest(root, decision["inputs"])
        write_json(root / "decisions.json", decisions)
        self._approve_current_run(root)
        return root

    def _use_legacy_manifest(self, root, manifest, relative):
        dependencies, seen = [], set()
        for entry in manifest["dependencies"]:
            if entry["path"] not in seen:
                seen.add(entry["path"])
                dependency = {key: entry[key] for key in ("id", "kind", "path", "sha256")}
                if dependency["path"] == relative:
                    dependency["id"] = "legacy-leaf"
                dependencies.append(dependency)
        manifest["dependencies"] = dependencies
        manifest["graph"] = [
            {"id": "project-context", "dependsOn": []},
            {"id": "model-routing", "dependsOn": []},
            {"id": "run", "dependsOn": ["project-context", "model-routing"]},
            {"id": "coverage", "dependsOn": ["project-context", "run"]},
            {"id": "evidence", "dependsOn": ["project-context", "coverage", "run"]},
            {"id": "assessment", "dependsOn": ["project-context", "run"]},
            {"id": "approvals", "dependsOn": ["project-context", "model-routing", "coverage", "assessment", "run"]},
        ]
        write_json(root / "manifest.json", manifest)

    def _snapshot_complete_run(self, root):
        self.assertEqual(studio.check_run(root)["status"], "PASS")
        manifest = studio.write_resume_manifest(root, self.repo)
        resumed = studio.resume_check(root, current_environment=self.environment)
        self.assertEqual(resumed["status"], "PASS")
        self.assertEqual(resumed["changedDependencies"], [])
        self.assertEqual(resumed["staleNodes"], [])
        return manifest
    def test_project_requirement_sources_invalidate_resume(self):
        root = fixture_run(self.repo, self.theme)
        source = self.repo / "requirements.md"
        source.write_text("Synthetic project requirement source\n", encoding="utf-8")
        record = studio.read_json(root / "run.json")
        record["projectContext"]["sources"] = ["requirements.md"]
        write_json(root / "run.json", record)
        self._approve_current_run(root)
        manifest = studio.write_resume_manifest(root, self.repo)
        self.assertIn("requirements.md", {entry["path"] for entry in manifest["sources"]})
        source.write_text("Changed synthetic project requirement source\n", encoding="utf-8")
        resumed = studio.resume_check(root, current_environment=self.environment)
        self.assertEqual(resumed["status"], "BLOCKED")
        self.assertEqual({entry["path"] for entry in resumed["changedDependencies"]}, {"requirements.md"})
        self.assertIn("project-context", resumed["staleNodes"])


    def _assert_changed_consumers(self, root, relative, expected_categories):
        stored_manifest = (root / "manifest.json").read_bytes()
        artifact = root / relative
        artifact.write_bytes(artifact.read_bytes() + b"\nChanged synthetic dependency\n")
        (root / "unrelated.txt").write_text("Unlisted unrelated file\n", encoding="utf-8")
        resumed = studio.resume_check(root, current_environment=self.environment)
        self.assertEqual(resumed["status"], "BLOCKED")
        self.assertEqual({entry["path"] for entry in resumed["changedDependencies"]}, {relative})
        self.assertEqual({entry["reason"] for entry in resumed["changedDependencies"]}, {"changed"})
        self.assertTrue({entry["id"] for entry in resumed["changedDependencies"]}.issubset(resumed["staleNodes"]))
        self.assertEqual(set(resumed["staleNodes"]) & CATEGORY_NODES, expected_categories)
        self.assertEqual((root / "manifest.json").read_bytes(), stored_manifest)
        return resumed

    def test_external_quoted_image_sources_are_rejected(self):
        values = (
            'image-set("https://example.invalid/pixel.svg" 1x)',
            "image-set('https://example.invalid/pixel(2).svg' 1x)",
            'image-set(url("icons.svg") 1x, "//example.invalid/pixel.svg" 2x)',
            'image-set(linear-gradient(black, white) 1x, "https://example.invalid/pixel.svg" type("image/svg+xml") 2x)',
            'IMAGE-SET("https://example.invalid/pixel.svg" 1x)',
            '-webkit-image-set("https://example.invalid/pixel.svg" 1x)',
            '-webkit-image-set("icons.svg" 1x, "//example.invalid/pixel.svg" 2x)',
            'image("https://example.invalid/pixel.svg", black)',
            'image(rtl "https://example.invalid/pixel.svg", black)',
        )
        for value in values:
            with self.subTest(value=value):
                (self.theme / "theme.css").write_text(
                    f'[data-ui-theme="fixture"] .card {{ background-image: {value}; }}\n', encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_quoted_image_sources_in_custom_properties_are_rejected(self):
        (self.theme / "theme.css").write_text(
            '[data-ui-theme="fixture"] .card { --poster: image-set("https://example.invalid/pixel.svg" 1x); '
            'background-image: var(--poster); }\n', encoding="utf-8")
        with self.assertRaises(studio.StudioError):
            studio.check_theme(self.theme)

    def test_indirect_image_source_variables_are_outside_the_audited_subset(self):
        for function in ("image-set", "-webkit-image-set", "image"):
            with self.subTest(function=function):
                (self.theme / "theme.css").write_text(
                    '[data-ui-theme="fixture"] .card { --poster: "https://example.invalid/pixel.svg"; '
                    f'background-image: {function}(var(--poster) 1x); }}\n', encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_quoted_comment_markers_cannot_hide_resource_declarations(self):
        (self.theme / "theme.css").write_text(
            '[data-ui-theme="fixture"] .card { --before: "/*"; '
            'background-image: url("https://example.invalid/pixel.svg"); --after: "*/"; }\n', encoding="utf-8")
        with self.assertRaises(studio.StudioError):
            studio.check_theme(self.theme)

    def test_bad_strings_cannot_hide_resources_after_browser_recovery(self):
        for newline in ("\n", "\r", "\f"):
            with self.subTest(newline=repr(newline)):
                (self.theme / "theme.css").write_text(
                    '[data-ui-theme="fixture"] .card { content: "' + newline
                    + '; background-image: url("https://example.invalid/pixel.svg"); }\n', encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_url_whitespace_cannot_select_a_declared_local_lookalike(self):
        relative = " /example.invalid/pixel.svg"
        asset = self.theme / relative
        asset.parent.mkdir(parents=True)
        asset.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["assets"] = [relative]
        write_json(self.theme / "theme.json", manifest)
        for value in ('url(" //example.invalid/pixel.svg")', 'image-set(" //example.invalid/pixel.svg" 1x)'):
            with self.subTest(value=value):
                (self.theme / "theme.css").write_text(
                    f'[data-ui-theme="fixture"] .card {{ background-image: {value}; }}\n', encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_unquoted_url_comment_markers_cannot_hide_resources(self):
        (self.theme / "theme.css").write_text(
            '[data-ui-theme="fixture"] .card { --before: url(#/*); '
            'background-image: url("https://example.invalid/pixel.svg"); --after: url(#*/); }\n', encoding="utf-8")
        with self.assertRaises(studio.StudioError):
            studio.check_theme(self.theme)

    def test_environment_fallback_cannot_substitute_image_sources(self):
        for function in ("image-set", "-webkit-image-set"):
            with self.subTest(function=function):
                (self.theme / "theme.css").write_text(
                    f'[data-ui-theme="fixture"] .card {{ background-image: {function}('
                    'env(ui-review-unknown-source, "https://example.invalid/pixel.svg") 1x); }\n', encoding="utf-8")
                with self.assertRaises(studio.StudioError):
                    studio.check_theme(self.theme)

    def test_eof_recovery_cannot_hide_unfinished_resource_urls(self):
        (self.theme / "theme.css").write_text(
            '[data-ui-theme="fixture"] .card { background-image: url(https://example.invalid/pixel.svg',
            encoding="utf-8")
        with self.assertRaises(studio.StudioError):
            studio.check_theme(self.theme)

    def test_declared_local_image_sources_remain_supported(self):
        manifest = studio.read_json(self.theme / "theme.json")
        manifest["styles"].append("nested/cards.css")
        manifest["assets"] = ["nested/pattern.svg", "nested/pattern-high.svg"]
        write_json(self.theme / "theme.json", manifest)
        (self.theme / "nested").mkdir()
        for relative in manifest["assets"]:
            (self.theme / relative).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        values = (
            'url("pattern.svg")',
            'image-set("pattern.svg" 1x, "pattern-high.svg" 2x)',
            'image-set(url("pattern.svg") 1x, url("pattern-high.svg") 2x)',
            'image-set("pattern.svg" type("image/svg+xml") 1x, url("pattern-high.svg") type("image/svg+xml") 2x)',
            'image-set(linear-gradient(black, white) 1x, "pattern.svg" 2x)',
            '-webkit-image-set(url("pattern.svg") 1x, url("pattern-high.svg") 2x)',
            '-webkit-image-set("pattern.svg" 1x, "pattern-high.svg" 2x)',
            'linear-gradient(rgb(0 0 0), rgb(255 255 255))',
            'linear-gradient(var(--foreground), var(--background))',
            'image-set(linear-gradient(var(--foreground), var(--background)) 1x, "pattern.svg" 2x)',
        )
        for value in values:
            with self.subTest(value=value):
                (self.theme / "nested/cards.css").write_text(
                    f'[data-ui-theme="fixture"] .card {{ background-image: {value}; }}\n', encoding="utf-8")
                self.assertEqual(studio.check_theme(self.theme)["status"], "PASS")

    def test_image_source_strings_require_existing_declared_assets(self):
        (self.theme / "unlisted.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        for function in ("image-set", "-webkit-image-set"):
            for relative in ("missing.svg", "unlisted.svg"):
                with self.subTest(function=function, relative=relative):
                    (self.theme / "theme.css").write_text(
                        f'[data-ui-theme="fixture"] .card {{ background-image: {function}("{relative}" 1x); }}\n',
                        encoding="utf-8")
                    with self.assertRaises(studio.StudioError):
                        studio.check_theme(self.theme)

    def test_nonfetching_strings_are_not_treated_as_image_sources(self):
        (self.theme / "theme.css").write_text(
            '[data-ui-theme="fixture"] .label::before { '
            'content: \'image-set("https://example.invalid/pixel.svg" 1x)\'; }\n'
            '/* image-set("https://example.invalid/comment.svg" 1x) */\n', encoding="utf-8")
        self.assertEqual(studio.check_theme(self.theme)["status"], "PASS")

    def test_changed_evidence_file_stales_evidence_and_approvals(self):
        root = fixture_run(self.repo, self.theme)
        self._snapshot_complete_run(root)
        self._assert_changed_consumers(root, "visual.md", {"evidence", "approvals"})

    def test_changed_evidence_input_stales_evidence_and_approvals(self):
        root = self._run_with_evidence_input()
        self._snapshot_complete_run(root)
        self._assert_changed_consumers(root, "evidence-source.txt", {"evidence", "approvals"})

    def test_changed_coverage_artifact_stales_coverage_evidence_and_approvals(self):
        root = fixture_run(self.repo, self.theme)
        self._snapshot_complete_run(root)
        self._assert_changed_consumers(root, "implementation.md", {"coverage", "evidence", "approvals"})

    def test_changed_approval_input_stales_only_approvals(self):
        root = fixture_run(self.repo, self.theme)
        self._snapshot_complete_run(root)
        self._assert_changed_consumers(root, "plan.html", {"approvals"})

    def test_shared_path_preserves_every_category_consumer(self):
        for relative in ("visual.md", "evidence-source.txt"):
            with self.subTest(relative=relative):
                root = self._run_with_shared_dependency(relative)
                self._snapshot_complete_run(root)
                self._assert_changed_consumers(root, relative, {"coverage", "evidence", "approvals"})

    def test_legacy_manifest_uses_recorded_kind_for_missing_consumer_edges(self):
        cases = (
            ("visual.md", {"evidence", "approvals"}),
            ("evidence-source.txt", {"evidence", "approvals"}),
            ("implementation.md", {"coverage", "evidence", "approvals"}),
            ("plan.html", {"approvals"}),
        )
        for relative, expected in cases:
            with self.subTest(relative=relative):
                root = self._run_with_evidence_input() if relative == "evidence-source.txt" else fixture_run(self.repo, self.theme)
                manifest = self._snapshot_complete_run(root)
                self._use_legacy_manifest(root, manifest, relative)
                resumed = self._assert_changed_consumers(root, relative, expected)
                self.assertIn("legacy-leaf", resumed["staleNodes"])
                self.assertTrue(resumed["conservative"])
                self.assertRegex(resumed["message"], r"(?i)refresh")

    def test_legacy_manifest_with_current_hashes_still_requires_refresh(self):
        root = fixture_run(self.repo, self.theme)
        manifest = self._snapshot_complete_run(root)
        self._use_legacy_manifest(root, manifest, "visual.md")
        stored_manifest = (root / "manifest.json").read_bytes()
        resumed = studio.resume_check(root, current_environment=self.environment)
        self.assertEqual(resumed["status"], "BLOCKED")
        self.assertTrue(resumed["conservative"])
        self.assertEqual(resumed["changedDependencies"], [])
        self.assertRegex(resumed["message"], r"(?i)refresh")
        self.assertEqual((root / "manifest.json").read_bytes(), stored_manifest)

    def test_legacy_shared_path_requires_explicit_conservative_refresh(self):
        root = self._run_with_shared_dependency("visual.md")
        manifest = self._snapshot_complete_run(root)
        self._use_legacy_manifest(root, manifest, "visual.md")
        artifact = root / "visual.md"
        artifact.write_bytes(artifact.read_bytes() + b"\nChanged shared legacy dependency\n")
        resumed = studio.resume_check(root, current_environment=self.environment)
        self.assertEqual(resumed["status"], "BLOCKED")
        self.assertTrue(resumed["conservative"])
        self.assertIn("legacy-leaf", resumed["staleNodes"])
        self.assertTrue({"evidence", "approvals"}.issubset(resumed["staleNodes"]))
        self.assertRegex(resumed["message"], r"(?i)refresh")

    def test_recorded_context_and_routing_paths_are_resume_dependencies(self):
        for field, relative, categories in (
                ("projectContext", "brief.md", {"project-context", "run", "coverage", "evidence", "assessment", "approvals"}),
                ("modelRouting", "routing-notes.md", {"model-routing", "run", "coverage", "evidence", "assessment", "approvals"})):
            with self.subTest(field=field):
                root = fixture_run(self.repo, self.theme)
                run = studio.read_json(root / "run.json")
                (root / relative).write_bytes((root / run[field]["path"]).read_bytes())
                run[field]["path"] = relative
                run[field]["sha256"] = studio.sha_file(root / relative)
                write_json(root / "run.json", run)
                self._approve_current_run(root)
                self._snapshot_complete_run(root)
                self._assert_changed_consumers(root, relative, categories)

    def test_unrelated_file_does_not_stale_complete_run(self):
        root = fixture_run(self.repo, self.theme)
        self._snapshot_complete_run(root)
        (root / "unrelated.txt").write_text("Unlisted unrelated file\n", encoding="utf-8")
        resumed = studio.resume_check(root, current_environment=self.environment)
        self.assertEqual(resumed["status"], "PASS")
        self.assertEqual(resumed["changedDependencies"], [])
        self.assertEqual(resumed["staleNodes"], [])


if __name__ == "__main__":
    unittest.main()
