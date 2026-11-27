from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from ui_design_studio.application import dispatch
from ui_design_studio.storage import EventDraft, IntegrityError, OperationResult, StateError, StateStore


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
    def test_schema_rejects_newer_metadata_and_state_symlink(self):
        newer = self.root / "newer.sqlite3"
        connection = sqlite3.connect(newer)
        connection.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO schema_meta VALUES ('schemaVersion', '99.0.0')")
        connection.commit()
        connection.close()
        with self.assertRaises(StateError):
            StateStore(newer)
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "state-link"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(StateError):
            StateStore(link / "state.sqlite3")

    def test_outbox_order_and_expired_lease_reclaim(self):
        for index in (1, 2):
            self.store.run_operation(
                realm="project",
                actor="tester",
                command=f"run.note.{index}",
                idempotency_key=f"note-{index}",
                request={"runId": "run", "note": str(index)},
                callback=lambda connection, index=index: OperationResult({"ok": True}, (EventDraft("run", "RunNoted", {"text": str(index)}),)),
            )
        first = self.store.claim_outbox(limit=1, consumer="consumer-a", lease_seconds=0.001)
        self.assertEqual(len(first), 1)
        time.sleep(0.01)
        reclaimed = self.store.claim_outbox(limit=1, consumer="consumer-b", lease_seconds=60)
        self.assertEqual(reclaimed[0]["sequence"], first[0]["sequence"])
        self.store.acknowledge_outbox(reclaimed[0]["eventId"], "consumer-b")
        second = self.store.claim_outbox(limit=1, consumer="consumer-c")
        self.assertGreater(second[0]["sequence"], reclaimed[0]["sequence"])

    def test_corrupt_artifact_blocks_approval(self):
        artifact = self.store.publish_artifact(b"approval", "application/octet-stream")
        Path(artifact["path"]).write_bytes(b"tampered")
        response = dispatch(self.store, {
            "command": "approval.decide",
            "operationId": "corrupt-approval",
            "idempotencyKey": "corrupt-approval",
            "actor": self.actor,
            "scope": {"projectId": "project", "runId": "run", "artifactDigest": artifact["digest"]},
            "expectedVersions": [{"entity": "run", "identity": "run", "revision": 1}],
            "payload": {"decisionId": "corrupt-approval", "runId": "run", "artifactDigest": artifact["digest"], "dependencyFingerprint": "deps-v1", "outcome": "approved"},
        })
        self.assertEqual(response["status"], "FAIL")
        self.assertEqual(response["error"]["code"], "BLOB_CORRUPT")
    def test_rationale_type_and_size_are_rejected(self):
        base = {
            "command": "approval.decide",
            "actor": self.actor,
            "scope": {"projectId": "project", "runId": "run", "artifactDigest": self.artifact},
            "expectedVersions": [{"entity": "run", "identity": "run", "revision": 1}],
        }
        malformed = dispatch(self.store, {**base, "operationId": "bad-rationale", "idempotencyKey": "bad-rationale", "payload": {"decisionId": "bad-rationale", "runId": "run", "artifactDigest": self.artifact, "dependencyFingerprint": "deps-v1", "outcome": "approved", "rationale": None}})
        self.assertEqual(malformed["receipt"]["result"]["error"]["code"], "VALIDATION_ERROR")
        oversized = dispatch(self.store, {**base, "operationId": "large-rationale", "idempotencyKey": "large-rationale", "payload": {"decisionId": "large-rationale", "runId": "run", "artifactDigest": self.artifact, "dependencyFingerprint": "deps-v1", "outcome": "approved", "rationale": "x" * (16 * 1024 + 1)}})
        self.assertEqual(oversized["receipt"]["result"]["error"]["code"], "VALIDATION_ERROR")

if __name__ == "__main__":
    unittest.main()
