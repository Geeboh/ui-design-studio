"""Transactional local state and immutable artifact storage for PRISM Studio."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from typing import Callable, Iterator


SCHEMA_VERSION = "2.0.0"
MAX_JSON_BYTES = 8 * 1024 * 1024


class StateError(RuntimeError):
    """Base class for state-store failures."""


class IdempotencyConflict(StateError):
    """The same key was reused for different command semantics."""


class IntegrityError(StateError):
    """Stored artifact bytes no longer match their declared digest."""


class VersionConflict(StateError):
    """A conditional update observed a newer revision."""


class OperationRejected(StateError):
    """A deterministic domain rejection that can be replayed safely."""

    def __init__(self, code: str, message: str, *, retry: str = "none") -> None:
        super().__init__(message)
        self.code = code
        self.retry = retry


@dataclass(frozen=True)
class EventDraft:
    stream_id: str
    event_type: str
    payload: dict


@dataclass(frozen=True)
class OperationResult:
    result: dict
    events: tuple[EventDraft, ...] = ()


@dataclass(frozen=True)
class OperationReceipt:
    operation_id: str
    command: str
    status: str
    request_fingerprint: str
    result: dict
    event_ids: tuple[str, ...]
    committed_at: str
    replayed: bool = False

    def as_dict(self) -> dict:
        return {
            "operationId": self.operation_id,
            "command": self.command,
            "status": self.status,
            "requestFingerprint": self.request_fingerprint,
            "result": self.result,
            "eventIds": list(self.event_ids),
            "committedAt": self.committed_at,
            "replayed": self.replayed,
        }


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _identifier(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    source_root TEXT NOT NULL,
    state_root TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
    digest TEXT PRIMARY KEY CHECK (length(digest) = 64),
    blob_path TEXT NOT NULL UNIQUE,
    byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
    mime_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
    decision_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    artifact_digest TEXT NOT NULL REFERENCES artifacts(digest),
    request_revision INTEGER NOT NULL CHECK (request_revision >= 1),
    dependency_fingerprint TEXT NOT NULL,
    actor TEXT NOT NULL,
    mode TEXT NOT NULL,
    outcome TEXT NOT NULL,
    feedback TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
    operation_id TEXT PRIMARY KEY,
    realm TEXT NOT NULL,
    actor TEXT NOT NULL,
    command TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT NOT NULL,
    event_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(realm, actor, command, idempotency_key)
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    stream_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_flight', 'acked')),
    attempts INTEGER NOT NULL CHECK (attempts >= 0),
    claimed_by TEXT,
    claimed_at TEXT
);
CREATE TABLE IF NOT EXISTS run_projection (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
    source_revision INTEGER NOT NULL CHECK (source_revision >= 1),
    payload_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('current', 'rebuilding', 'stale')),
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_stream_idx ON events(stream_id, created_at);
CREATE INDEX IF NOT EXISTS outbox_status_idx ON outbox(status, attempts, event_id);
"""


class StateStore:
    """One local SQLite realm plus its content-addressed blob directory."""

    def __init__(self, path: str | os.PathLike[str], *, blob_root: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.blob_root = Path(blob_root).expanduser().resolve() if blob_root else self.path.parent / "blobs"
        self.blob_root.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            connection.close()
            raise StateError("SQLite foreign-key enforcement is unavailable")
        if connection.execute("PRAGMA journal_mode").fetchone()[0].lower() != "delete":
            connection.close()
            raise StateError("SQLite DELETE journal policy was not applied")
        if connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
            connection.close()
            raise StateError("SQLite FULL synchronous policy was not applied")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(_SCHEMA)
            connection.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schemaVersion', ?)", (SCHEMA_VERSION,))
            connection.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('sqliteVersion', ?)", (sqlite3.sqlite_version,))
            connection.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('sqliteSourceId', ?)", (self.sqlite_source_id(connection),))
        finally:
            connection.close()

    @staticmethod
    def sqlite_source_id(connection: sqlite3.Connection | None = None) -> str:
        owned = connection is None
        if owned:
            connection = sqlite3.connect(":memory:")
        try:
            return str(connection.execute("SELECT sqlite_source_id()").fetchone()[0])
        finally:
            if owned:
                connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def capabilities(self) -> dict:
        connection = self._connect()
        try:
            return {
                "sqliteVersion": sqlite3.sqlite_version,
                "sqliteSourceId": self.sqlite_source_id(connection),
                "journalMode": connection.execute("PRAGMA journal_mode").fetchone()[0],
                "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
                "foreignKeys": connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1,
                "schemaVersion": SCHEMA_VERSION,
            }
        finally:
            connection.close()

    def run_operation(
        self,
        *,
        realm: str,
        actor: str,
        command: str,
        idempotency_key: str,
        request: dict,
        callback: Callable[[sqlite3.Connection], OperationResult],
        operation_id: str | None = None,
    ) -> OperationReceipt:
        if not all(isinstance(value, str) and value.strip() for value in (realm, actor, command, idempotency_key)):
            raise StateError("Operation realm, actor, command, and idempotency key are required")
        request_bytes = _canonical(request)
        if len(request_bytes) > MAX_JSON_BYTES:
            raise StateError("Operation request is too large")
        request_fingerprint = _digest(request_bytes)
        now = _now()
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM operations WHERE realm = ? AND actor = ? AND command = ? AND idempotency_key = ?",
                (realm, actor, command, idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["request_fingerprint"] != request_fingerprint:
                    raise IdempotencyConflict("Idempotency key was reused with different command input")
                return self._receipt(existing, replayed=True)
            operation_id = operation_id or _identifier("op")
            connection.execute(
                "INSERT INTO operations(operation_id, realm, actor, command, idempotency_key, request_fingerprint, status, result_json, event_ids_json, created_at) VALUES (?, ?, ?, ?, ?, ?, 'in_progress', '{}', '[]', ?)",
                (operation_id, realm, actor, command, idempotency_key, request_fingerprint, now),
            )
            try:
                outcome = callback(connection)
                if not isinstance(outcome, OperationResult):
                    raise StateError("Operation callback must return OperationResult")
                event_ids = self._append_events(connection, outcome.events, now)
                result = outcome.result
                status = "committed"
            except OperationRejected as exc:
                event_ids = []
                result = {"error": {"code": exc.code, "message": str(exc), "retry": exc.retry}}
                status = "rejected"
            encoded_result = _canonical(result).decode("utf-8")
            connection.execute(
                "UPDATE operations SET status = ?, result_json = ?, event_ids_json = ? WHERE operation_id = ?",
                (status, encoded_result, json.dumps(event_ids, separators=(",", ":")), operation_id),
            )
            return OperationReceipt(operation_id, command, status, request_fingerprint, result, tuple(event_ids), now)

    def _receipt(self, row: sqlite3.Row, *, replayed: bool) -> OperationReceipt:
        return OperationReceipt(
            operation_id=row["operation_id"],
            command=row["command"],
            status=row["status"],
            request_fingerprint=row["request_fingerprint"],
            result=json.loads(row["result_json"]),
            event_ids=tuple(json.loads(row["event_ids_json"])),
            committed_at=row["created_at"],
            replayed=replayed,
        )

    @staticmethod
    def _append_events(connection: sqlite3.Connection, events: tuple[EventDraft, ...], created_at: str) -> list[str]:
        event_ids = []
        for event in events:
            event_id = _identifier("evt")
            payload = _canonical(event.payload).decode("utf-8")
            connection.execute(
                "INSERT INTO events(event_id, stream_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_id, event.stream_id, event.event_type, payload, created_at),
            )
            connection.execute("INSERT INTO outbox(event_id, status, attempts) VALUES (?, 'pending', 0)", (event_id,))
            event_ids.append(event_id)
        return event_ids

    @staticmethod
    def _insert_project(connection: sqlite3.Connection, project_id: str, source_root: str, state_root: str) -> None:
        connection.execute(
            "INSERT INTO projects(project_id, source_root, state_root, revision, created_at) VALUES (?, ?, ?, 1, ?)",
            (project_id, str(Path(source_root).resolve()), str(Path(state_root).resolve()), _now()),
        )

    @staticmethod
    def _insert_run(connection: sqlite3.Connection, run_id: str, project_id: str, payload: dict, *, stage: str = "assess", status: str = "pending") -> None:
        connection.execute(
            "INSERT INTO runs(run_id, project_id, status, stage, revision, payload_json, created_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (run_id, project_id, status, stage, _canonical(payload).decode("utf-8"), _now()),
        )

    def create_project_in_transaction(self, connection: sqlite3.Connection, project_id: str, source_root: str, state_root: str) -> None:
        self._insert_project(connection, project_id, source_root, state_root)

    def create_run_in_transaction(self, connection: sqlite3.Connection, run_id: str, project_id: str, payload: dict, *, stage: str = "assess", status: str = "pending") -> None:
        self._insert_run(connection, run_id, project_id, payload, stage=stage, status=status)
    def create_project(self, project_id: str, source_root: str, state_root: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO projects(project_id, source_root, state_root, revision, created_at) VALUES (?, ?, ?, 1, ?)",
                (project_id, str(Path(source_root).resolve()), str(Path(state_root).resolve()), _now()),
            )

    def create_run(self, run_id: str, project_id: str, payload: dict, *, stage: str = "assess", status: str = "pending") -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, project_id, status, stage, revision, payload_json, created_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (run_id, project_id, status, stage, _canonical(payload).decode("utf-8"), _now()),
            )

    def record_approval_in_transaction(
        self,
        connection: sqlite3.Connection,
        *,
        decision_id: str,
        run_id: str,
        artifact_digest: str,
        expected_revision: int,
        dependency_fingerprint: str,
        actor: str,
        mode: str,
        outcome: str,
        feedback: str,
    ) -> int:
        row = connection.execute("SELECT revision FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise StateError("Run not found")
        if row["revision"] != expected_revision:
            raise VersionConflict("Run revision is stale")
        connection.execute(
            "INSERT INTO approvals(decision_id, run_id, artifact_digest, request_revision, dependency_fingerprint, actor, mode, outcome, feedback, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (decision_id, run_id, artifact_digest, expected_revision, dependency_fingerprint, actor, mode, outcome, feedback, _now()),
        )
        changed = connection.execute(
            "UPDATE runs SET revision = revision + 1 WHERE run_id = ? AND revision = ?",
            (run_id, expected_revision),
        ).rowcount
        if changed != 1:
            raise VersionConflict("Run revision is stale")
        return expected_revision + 1

    def get_run(self, run_id: str) -> dict | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            return {
                "runId": row["run_id"],
                "projectId": row["project_id"],
                "status": row["status"],
                "stage": row["stage"],
                "revision": row["revision"],
                "payload": json.loads(row["payload_json"]),
            }
        finally:
            connection.close()

    def update_run(self, run_id: str, expected_revision: int, *, status: str | None = None, stage: str | None = None, payload: dict | None = None) -> int:
        if not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1:
            raise StateError("Expected run revision must be a positive integer")
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                raise StateError("Run not found")
            next_status = status if status is not None else row["status"]
            next_stage = stage if stage is not None else row["stage"]
            next_payload = _canonical(payload if payload is not None else json.loads(row["payload_json"])).decode("utf-8")
            changed = connection.execute(
                "UPDATE runs SET status = ?, stage = ?, revision = revision + 1, payload_json = ? WHERE run_id = ? AND revision = ?",
                (next_status, next_stage, next_payload, run_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise VersionConflict("Run revision is stale")
            return expected_revision + 1

    def publish_artifact(self, content: bytes, mime_type: str) -> dict:
        if not isinstance(content, bytes) or not content:
            raise StateError("Artifact content must be nonempty bytes")
        if not isinstance(mime_type, str) or not mime_type.strip():
            raise StateError("Artifact MIME type is required")
        digest = _digest(content)
        target = self.blob_root / "sha256" / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            self._verify_blob(target, digest)
        else:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".stage-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                if target.exists():
                    self._verify_blob(target, digest)
                else:
                    os.replace(temporary, target)
                    directory = os.open(target.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
            finally:
                temporary.unlink(missing_ok=True)
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO artifacts(digest, blob_path, byte_length, mime_type, created_at) VALUES (?, ?, ?, ?, ?)",
                (digest, str(target), len(content), mime_type, _now()),
            )
        return {"digest": digest, "bytes": len(content), "mimeType": mime_type, "path": str(target)}

    def read_artifact(self, digest: str) -> bytes:
        connection = self._connect()
        try:
            row = connection.execute("SELECT blob_path FROM artifacts WHERE digest = ?", (digest,)).fetchone()
        finally:
            connection.close()
        if row is None:
            raise StateError("Artifact not found")
        path = Path(row["blob_path"])
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise IntegrityError("Artifact bytes are unavailable") from exc
        if _digest(content) != digest:
            raise IntegrityError("Artifact bytes do not match their declared digest")
        return content

    @staticmethod
    def _verify_blob(path: Path, digest: str) -> None:
        if _digest(path.read_bytes()) != digest:
            raise IntegrityError("Existing immutable blob is corrupt")

    def rebuild_run_projection(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        if run is None:
            raise StateError("Run not found")
        projection = {"runId": run["runId"], "projectId": run["projectId"], "status": run["status"], "stage": run["stage"], "revision": run["revision"]}
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO run_projection(run_id, source_revision, payload_json, state, updated_at) VALUES (?, ?, ?, 'current', ?) ON CONFLICT(run_id) DO UPDATE SET source_revision = excluded.source_revision, payload_json = excluded.payload_json, state = 'current', updated_at = excluded.updated_at",
                (run_id, run["revision"], _canonical(projection).decode("utf-8"), _now()),
            )
        return projection

    def claim_outbox(self, limit: int = 50, *, consumer: str | None = None) -> list[dict]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise StateError("Outbox limit must be between 1 and 1000")
        claim = consumer or _identifier("consumer")
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT o.event_id, e.stream_id, e.event_type, e.payload_json FROM outbox o JOIN events e ON e.event_id = o.event_id WHERE o.status = 'pending' ORDER BY o.event_id LIMIT ?",
                (limit,),
            ).fetchall()
            now = _now()
            for row in rows:
                connection.execute("UPDATE outbox SET status = 'in_flight', attempts = attempts + 1, claimed_by = ?, claimed_at = ? WHERE event_id = ? AND status = 'pending'", (claim, now, row["event_id"]))
            return [{"eventId": row["event_id"], "streamId": row["stream_id"], "eventType": row["event_type"], "payload": json.loads(row["payload_json"]), "consumer": claim} for row in rows]

    def acknowledge_outbox(self, event_id: str, consumer: str) -> None:
        with self.transaction() as connection:
            changed = connection.execute("UPDATE outbox SET status = 'acked' WHERE event_id = ? AND status = 'in_flight' AND claimed_by = ?", (event_id, consumer)).rowcount
            if changed != 1:
                raise StateError("Outbox item is not owned by this consumer")
