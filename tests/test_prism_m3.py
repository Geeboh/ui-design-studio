from __future__ import annotations

import unittest

from ui_design_studio.domain import CommandFailure, allowed_actions, approval_applicability, approval_fingerprint, create_revision_request, evaluate_batch, merge_revision_lineage, simplify_freehand, validate_annotation_set, validate_components, validate_decision

class ApprovalSemanticsTests(unittest.TestCase):
    def test_approved_feedback_is_optional_but_changes_need_a_reason(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                self.assertEqual(validate_decision(outcome="approved", feedback=value, annotations=[], actor_kind="human", mode="guided"), "")
        with self.assertRaises(CommandFailure):
            validate_decision(outcome="changes", feedback=None, annotations=[], actor_kind="human", mode="guided")

    def test_progress_is_excluded_but_dependency_change_is_targeted(self):
        manifest = {"artifactDigest": "a", "dependencyFingerprint": "d", "componentIds": ["content"], "progress": 1}
        decision = {"outcome": "approved", "scopeFingerprint": approval_fingerprint(manifest), "artifactDigest": "a", "dependencyFingerprint": "d"}
        unchanged = {**manifest, "progress": 2}
        self.assertTrue(approval_applicability(decision, unchanged)["applicable"])
        changed = {**manifest, "dependencyFingerprint": "d2"}
        reasons = {item["code"] for item in approval_applicability(decision, changed)["reasons"]}
        self.assertEqual(reasons, {"SCOPE_CHANGED", "DEPENDENCY_CHANGED"})
    def test_allowed_action_reason_codes_are_stable(self):
        agent = allowed_actions(state="reviewable", actor_kind="agent", mode="guided")
        terminal = allowed_actions(state="approved", actor_kind="human", mode="guided")
        self.assertEqual(agent["approve"]["reason"]["code"], "HUMAN_DECISION_REQUIRED")
        self.assertEqual(terminal["approve"]["reason"]["code"], "NOT_REVIEWABLE")
    def test_annotation_geometry_preserves_endpoints_and_rejects_invalid_points(self):
        raw = [[index / 129, index / 129] for index in range(130)]
        reduced = simplify_freehand(raw)
        self.assertEqual(len(reduced), 128)
        self.assertEqual(reduced[0], [0.0, 0.0])
        self.assertEqual(reduced[-1], [1.0, 1.0])
        with self.assertRaises(CommandFailure):
            validate_annotation_set(annotation_set_id="bad", revision=1, base_artifact_digest="a" * 64, image_size={"widthPx": 100, "heightPx": 50}, annotations=[{"tool": "line", "points": [[0, 0], [2, 1]]}])
    def test_focused_revision_pins_exact_base_and_annotation_revision(self):
        annotation_set = validate_annotation_set(annotation_set_id="set-1", revision=3, base_artifact_digest="a" * 64, image_size={"widthPx": 640, "heightPx": 480}, annotations=[])
        request = create_revision_request(revision_request_id="revision-1", base_artifact_digest="a" * 64, annotation_set=annotation_set, component_ids=["content"], instructions="Tighten spacing", retained_constraints=["Keep focus order"])
        self.assertEqual(request.annotation_revision, 3)
        self.assertEqual(request.component_ids, ("content",))
        with self.assertRaises(CommandFailure):
            create_revision_request(revision_request_id="bad", base_artifact_digest="b" * 64, annotation_set=annotation_set, component_ids=["content"], instructions="Retarget")
    def test_component_graph_rejects_cycles_and_ownership_conflicts(self):
        valid = validate_components([{"componentId": "nav", "name": "Navigation", "owner": "ui", "dependencies": [], "ownedPaths": ["nav/"]}])
        self.assertEqual(valid[0].component_id, "nav")
        with self.assertRaises(CommandFailure):
            validate_components([{"componentId": "a", "name": "A", "owner": "one", "dependencies": ["b"], "ownedPaths": []}, {"componentId": "b", "name": "B", "owner": "two", "dependencies": ["a"], "ownedPaths": []}])
    def test_batch_retains_independent_outcomes_and_fingerprint(self):
        result = evaluate_batch([{"componentId": "a", "expectedRevision": 1}, {"componentId": "b", "expectedRevision": 1}, {"componentId": "c", "expectedRevision": 1}, {"componentId": "", "expectedRevision": True}], {"a": 1, "b": 2}, allowed_components={"a", "b"})
        self.assertEqual([item["status"] for item in result["items"]], ["Applied", "Conflict", "Forbidden", "Invalid"])
        self.assertEqual(result["applied"], ["a"])
        self.assertTrue(result["batchFingerprint"])
    def test_lineage_reports_shared_conflict_and_merges_independent_changes(self):
        conflict = merge_revision_lineage("r3", {"revisionId": "r1", "componentIds": ["nav"], "changes": {"token.color": "blue"}}, {"revisionId": "r2", "componentIds": ["content"], "changes": {"token.color": "red"}})
        merged = merge_revision_lineage("r4", {"revisionId": "r1", "componentIds": ["nav"], "changes": {"nav.spacing": 2}}, {"revisionId": "r2", "componentIds": ["content"], "changes": {"content.copy": "new"}})
        self.assertEqual(conflict.merge_outcome, "conflict")
        self.assertEqual(conflict.conflicts[0]["code"], "SHARED_DEPENDENCY_CHANGED")
        self.assertEqual(merged.merge_outcome, "merged")

if __name__ == "__main__":
    unittest.main()
