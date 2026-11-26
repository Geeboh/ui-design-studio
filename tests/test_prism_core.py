from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ui_design_studio.application import dispatch
from ui_design_studio.storage import EventDraft, IntegrityError, OperationResult, StateStore


class PrismCoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="prism-core-")
        self.root = Path(self.temporary.name)
        self.store = StateStore(self.root / "state.sqlite3")
        self.store.create_project("project", self.root, self.root)
        self.store.create_run("run", "project", {"title": "fixture"})
        self.artifact = self.store.publish_artifact(b"fixture", "application/octet-stream")["digest"]
        self.actor = {"principal": "tester", "kind": "human", "mode": "guided"}

    def tearDown(self):
        self.temporary.cleanup()

    def approval(self, *, key: str, operation: str, revision: int, outcome: str = "approved", feedback=None):
        return dispatch(self.store, {
            "command": "approval.decide",
            "operationId": operation,
            "idempotencyKey": key,
            "actor": self.actor,
            "scope": {"projectId": "project", "runId": "run", "artifactDigest": self.artifact},
            "expectedVersions": [{"entity": "run", "identity": "run", "revision": revision}],
            "payload": {"decisionId": operation, "runId": "run", "artifactDigest": self.artifact, "dependencyFingerprint": "deps-v1", "outcome": outcome, "feedback": feedback},
        })

    def test_stale_revision_rejects_without_partial_state(self):
        rejected = self.approval(key="reject", operation="reject", revision=1, outcome="changes")
        self.assertEqual(rejected["status"], "REJECTED")
        self.assertEqual(self.store.get_run("run")["revision"], 1)
        accepted = self.approval(key="accept", operation="accept", revision=1)
        self.assertEqual(accepted["status"], "PASS")
        stale = self.approval(key="stale", operation="stale", revision=1)
        self.assertEqual(stale["status"], "REJECTED")
        self.assertEqual(stale["receipt"]["result"]["error"]["code"], "VERSION_CONFLICT")
        self.assertEqual(self.store.get_run("run")["revision"], 2)

    def test_replay_returns_one_receipt_and_changed_key_rejects(self):
        first = self.approval(key="replay", operation="replay", revision=1)
        replay = self.approval(key="replay", operation="replay", revision=1)
        self.assertEqual(first["status"], "PASS")
        self.assertTrue(replay["receipt"]["replayed"])
        self.assertEqual(replay["receipt"]["operationId"], first["receipt"]["operationId"])
        changed = self.approval(key="replay", operation="changed", revision=1)
        self.assertEqual(changed["status"], "FAIL")
        self.assertEqual(changed["error"]["code"], "IDEMPOTENCY_CONFLICT")
    def test_outbox_ack_and_projection_rebuild(self):
        result = self.store.run_operation(
            realm="project",
            actor="tester",
            command="run.note",
            idempotency_key="note-1",
            request={"runId": "run", "note": "hello"},
            callback=lambda connection: OperationResult({"ok": True}, (EventDraft("run", "RunNoted", {"text": "hello"}),)),
        )
        self.assertEqual(result.status, "committed")
        claimed = self.store.claim_outbox()
        self.assertEqual(len(claimed), 1)
        self.store.acknowledge_outbox(claimed[0]["eventId"], claimed[0]["consumer"])
        self.assertEqual(self.store.claim_outbox(), [])
        projection = self.store.rebuild_run_projection("run")
        self.assertEqual(projection["revision"], self.store.get_run("run")["revision"])
    def test_artifact_digest_deduplicates_and_rejects_corruption(self):
        first = self.store.publish_artifact(b"same", "application/octet-stream")
        second = self.store.publish_artifact(b"same", "application/octet-stream")
        self.assertEqual(first["digest"], second["digest"])
        Path(first["path"]).write_bytes(b"corrupt")
        with self.assertRaises(IntegrityError):
            self.store.read_artifact(first["digest"])

if __name__ == "__main__":
    unittest.main()
