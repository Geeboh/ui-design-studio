"""Behavioral regressions for project-bound, current, independently reviewed acceptance."""
from pathlib import Path
import tempfile
import unittest

from test_studio import fixture_run, fixture_theme, studio, write_json


class FreezeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ui-freeze-acceptance-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "project-a"
        self.theme = fixture_theme(self.repo)

    def approve_current_final_inputs(self, root):
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"] = [entry for entry in decisions["decisions"] if entry["stage"] != "finalize"]
        write_json(root / "decisions.json", decisions)
        review = studio.check_run(root)
        decisions["decisions"].append({"stage": "finalize", "actor": "director", "outcome": "approved",
                                       "rationale": "Synthetic acceptance regression final review",
                                       "inputsDigest": review["reviewDigest"]})
        write_json(root / "decisions.json", decisions)

    def test_registration_rejects_another_projects_passed_run_with_identical_theme(self):
        other_repo = self.root / "project-b"
        other_theme = fixture_theme(other_repo)
        self.assertEqual({path.relative_to(self.theme).as_posix(): path.read_bytes()
                          for path in self.theme.rglob("*") if path.is_file()},
                         {path.relative_to(other_theme).as_posix(): path.read_bytes()
                          for path in other_theme.rglob("*") if path.is_file()})
        roots = []
        for repo, theme in ((self.repo, self.theme), (other_repo, other_theme)):
            root = fixture_run(repo, theme)
            source = repo / "requirements.txt"
            source.write_text(f"Synthetic {repo.name} requirements. Offline operation is required.\n", encoding="utf-8")
            context = root / "project-context.md"
            context.write_text(f"Synthetic context for {repo.name}. Source: {source}. Offline operation is required.\n",
                               encoding="utf-8")
            run = studio.read_json(root / "run.json")
            run["projectContext"].update(sources=[str(source)], sha256=studio.sha_file(context))
            write_json(root / "run.json", run)
            self.approve_current_final_inputs(root)
            self.assertEqual(studio.check_run(root)["status"], "PASS")
            roots.append(root)
        self.assertNotEqual(studio.sha_file(roots[0] / "project-context.md"),
                            studio.sha_file(roots[1] / "project-context.md"))
        registry = other_repo / "themes" / "registry.json"
        self.assertFalse(registry.exists())
        with self.subTest(consumer="register_theme"):
            with self.assertRaises(studio.StudioError):
                studio.register_theme(other_repo, "fixture", roots[0])
        self.assertFalse(registry.exists(), "Another project's approval must not create this project's registry")

    def test_report_mutation_invalidates_final_approval_and_registration(self):
        for mutation in ("alter", "delete"):
            with self.subTest(mutation=mutation):
                repo = self.root / mutation
                theme = fixture_theme(repo)
                root = fixture_run(repo, theme)
                self.assertEqual(studio.check_run(root)["status"], "PASS")
                run = studio.read_json(root / "run.json")
                self.assertTrue(all(entry.get("path") != "report.md"
                                    and "report.md" not in entry.get("inputs", []) for entry in run["evidence"]))
                decisions_path = root / "decisions.json"
                approved_decisions = decisions_path.read_bytes()
                report = root / "report.md"
                if mutation == "alter":
                    report.write_text("Synthetic replacement assessment written after final approval.\n", encoding="utf-8")
                else:
                    report.unlink()
                self.assertEqual(decisions_path.read_bytes(), approved_decisions)
                for consumer, arguments in ((studio.check_run, (root,)),
                                            (studio.register_theme, (repo, "fixture", root))):
                    with self.subTest(consumer=consumer.__name__):
                        try:
                            result = consumer(*arguments)
                        except studio.StudioError:
                            pass
                        else:
                            self.assertIn(result["status"], ("BLOCKED", "FAIL"))
                self.assertFalse((repo / "themes" / "registry.json").exists(),
                                 "An altered or missing approved report must not be registered")

    def test_whitespace_cannot_make_self_review_independent(self):
        for implementer, reviewer in (("alice", "alice "), ("alice ", "alice"), (" alice\t", "\talice ")):
            with self.subTest(implementer=implementer, reviewer=reviewer):
                root = fixture_run(self.repo, self.theme)
                self.assertEqual(studio.check_run(root)["status"], "PASS")
                run = studio.read_json(root / "run.json")
                run["implementer"] = implementer
                for entry in run["evidence"]:
                    if entry["kind"] == "review":
                        entry["reviewer"] = reviewer
                write_json(root / "run.json", run)
                self.approve_current_final_inputs(root)
                result = studio.check_run(root)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["pending"],
                                 ["Independent review must name a reviewer distinct from the implementer"])
                self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
