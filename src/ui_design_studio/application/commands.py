"""One command path shared by CLI, MCP, and HTTP adapters."""
from __future__ import annotations

import base64
import re
from typing import Any
import sqlite3

from ui_design_studio.domain.contracts import (
    CommandEnvelope,
    CommandFailure,
    ContractError,
    DomainError,
    require_finite_json,
)
from ui_design_studio.domain.decisions import validate_decision
from ui_design_studio.storage import (
    EventDraft,
    IdempotencyConflict,
    IntegrityError,
    OperationRejected,
    OperationResult,
    StateError,
    StateStore,
    VersionConflict,
)


MUTATIONS = {"project.initialize", "run.create", "approval.decide"}
MAX_RATIONALE_BYTES = 16 * 1024


class CommandDispatcher:
    """Validate commands once and route them to the authoritative StateStore."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def dispatch(self, value: CommandEnvelope | dict[str, Any]) -> dict[str, Any]:
        try:
            envelope = value if isinstance(value, CommandEnvelope) else CommandEnvelope.from_value(value)
            require_finite_json(envelope.payload)
            if envelope.command not in MUTATIONS and envelope.command not in {"run.get", "artifact.read", "capabilities.get"}:
                raise CommandFailure(DomainError("UNSUPPORTED_COMMAND", "Command is not supported"))
            if envelope.command in MUTATIONS and not envelope.idempotency_key:
                raise CommandFailure(DomainError("VALIDATION_ERROR", "Mutations require idempotencyKey"))
            self._project_scope(envelope)
            if envelope.command == "capabilities.get":
                return {"status": "PASS", "capabilities": self.store.capabilities()}
            if envelope.command == "run.get":
                return self._get_run(envelope)
            if envelope.command == "artifact.read":
                return self._read_artifact(envelope)
            return self._mutation(envelope)
        except (ContractError, CommandFailure) as exc:
            error = exc.error if isinstance(exc, CommandFailure) else DomainError("VALIDATION_ERROR", str(exc))
            return {"status": "FAIL", "error": error.as_dict()}
        except IdempotencyConflict as exc:
            return {"status": "FAIL", "error": DomainError("IDEMPOTENCY_CONFLICT", str(exc)).as_dict()}
        except VersionConflict as exc:
            return {"status": "FAIL", "error": DomainError("VERSION_CONFLICT", str(exc), retry="refresh").as_dict()}
        except IntegrityError as exc:
            return {"status": "FAIL", "error": DomainError("BLOB_CORRUPT", str(exc), retry="reconcile").as_dict()}
        except StateError as exc:
            return {"status": "FAIL", "error": DomainError("STATE_ERROR", str(exc), retry="refresh").as_dict()}
        except (OSError, sqlite3.Error) as exc:
            return {"status": "FAIL", "error": DomainError("IO_ERROR", str(exc), retry="backoff").as_dict()}

    def _get_run(self, envelope: CommandEnvelope) -> dict[str, Any]:
        run_id = self._scoped(envelope, envelope.scope.run_id, "runId", "run")
        if not isinstance(run_id, str) or not run_id.strip():
            raise CommandFailure(DomainError("VALIDATION_ERROR", "runId is required", field_errors=({"path": "scope.runId", "code": "required", "message": "Run identity is required"},)))
        run = self.store.get_run(run_id)
        if run is None:
            raise CommandFailure(DomainError("NOT_FOUND", "Run was not found", retry="refresh"))
        if envelope.scope.project_id is not None and run["projectId"] != envelope.scope.project_id:
            raise CommandFailure(DomainError("FORBIDDEN", "Run is outside the requested project scope"))
        return {"status": "PASS", "run": run}

    def _read_artifact(self, envelope: CommandEnvelope) -> dict[str, Any]:
        digest = self._scoped(envelope, envelope.scope.artifact_digest, "digest", "artifact")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CommandFailure(DomainError("VALIDATION_ERROR", "artifact digest is required"))
        content = self.store.read_artifact(digest)
        return {"status": "PASS", "digest": digest, "contentBase64": base64.b64encode(content).decode("ascii"), "bytes": len(content)}

    def _mutation(self, envelope: CommandEnvelope) -> dict[str, Any]:
        realm = self._project_scope(envelope) or f"profile:{envelope.actor.principal}"
        receipt = self.store.run_operation(
            realm=realm,
            actor=envelope.actor.principal,
            command=envelope.command,
            idempotency_key=envelope.idempotency_key or "",
            request=envelope.request(),
            operation_id=envelope.operation_id,
            callback=lambda connection: self._apply(envelope, connection),
        )
        if envelope.command == "approval.decide" and receipt.status == "committed":
            run_id = envelope.scope.run_id or envelope.payload.get("runId")
            if isinstance(run_id, str):
                self.store.rebuild_run_projection(run_id)
        return {"status": "PASS" if receipt.status == "committed" else "REJECTED", "receipt": receipt.as_dict()}

    def _apply(self, envelope: CommandEnvelope, connection) -> OperationResult:
        payload = envelope.payload
        if envelope.command == "project.initialize":
            project_id = self._required(payload, "projectId")
            source_root = self._required(payload, "sourceRoot")
            state_root = self._required(payload, "stateRoot")
            self.store.create_project_in_transaction(connection, project_id, source_root, state_root)
            return OperationResult({"projectId": project_id}, (EventDraft(project_id, "ProjectInitialized", {"projectId": project_id}),))
        if envelope.command == "run.create":
            run_id = self._required(payload, "runId")
            project_id = self._project_scope(envelope) or self._required(payload, "projectId")
            run_payload = payload.get("run", {})
            if not isinstance(run_payload, dict):
                raise OperationRejected("VALIDATION_ERROR", "run must be an object")
            self.store.create_run_in_transaction(connection, run_id, project_id, run_payload, stage=payload.get("stage", "assess"), status=payload.get("status", "pending"))
            return OperationResult({"runId": run_id, "projectId": project_id, "revision": 1}, (EventDraft(run_id, "RunCreated", {"runId": run_id, "projectId": project_id}),))
        if envelope.command == "approval.decide":
            return self._apply_decision(envelope, connection)
        raise OperationRejected("UNSUPPORTED_COMMAND", "Command is not supported")

    def _apply_decision(self, envelope: CommandEnvelope, connection) -> OperationResult:
        payload = envelope.payload
        run_id = self._scoped(envelope, envelope.scope.run_id, "runId", "run") or self._required(payload, "runId")
        artifact_digest = self._scoped(envelope, envelope.scope.artifact_digest, "artifactDigest", "artifact") or self._required(payload, "artifactDigest")
        expected_revision = self._run_revision(envelope, run_id)
        outcome = payload.get("outcome")
        annotations = payload.get("annotations", [])
        if annotations is None:
            annotations = []
        feedback = self._rationale(payload)
        try:
            feedback = validate_decision(
                outcome=outcome,
                feedback=feedback,
                annotations=annotations,
                actor_kind=envelope.actor.kind,
                mode=envelope.actor.mode,
            )
        except CommandFailure as exc:
            raise OperationRejected(exc.error.code, exc.error.message, retry=exc.error.retry) from exc
        decision_id = self._required(payload, "decisionId")
        dependency_fingerprint = self._required(payload, "dependencyFingerprint")
        scope_fingerprint = payload.get("scopeFingerprint", "")
        if not isinstance(scope_fingerprint, str) or len(scope_fingerprint.encode("utf-8")) > MAX_RATIONALE_BYTES:
            raise OperationRejected("VALIDATION_ERROR", "scopeFingerprint must be a bounded string")
        try:
            revision = self.store.record_approval_in_transaction(
                connection,
                decision_id=decision_id,
                run_id=run_id,
                artifact_digest=artifact_digest,
                expected_revision=expected_revision,
                dependency_fingerprint=dependency_fingerprint,
                scope_fingerprint=scope_fingerprint,
                annotations=annotations,
                actor=envelope.actor.principal,
                mode=envelope.actor.mode,
                outcome=outcome,
                feedback=feedback,
                project_id=self._project_scope(envelope),
            )
        except VersionConflict as exc:
            raise OperationRejected("VERSION_CONFLICT", str(exc), retry="refresh") from exc
        return OperationResult(
            {
                "decisionId": decision_id,
                "runId": run_id,
                "artifactDigest": artifact_digest,
                "outcome": outcome,
                "feedback": feedback,
                "annotations": annotations,
                "dependencyFingerprint": dependency_fingerprint,
                "scopeFingerprint": scope_fingerprint,
                "revision": revision,
            },
            (EventDraft(run_id, "DecisionRecorded", {"decisionId": decision_id, "runId": run_id, "revision": revision, "outcome": outcome}),),
        )

    @staticmethod
    def _rationale(payload: dict[str, Any]) -> Any:
        if "rationale" in payload:
            rationale = payload["rationale"]
            if not isinstance(rationale, str):
                raise OperationRejected("VALIDATION_ERROR", "rationale must be a string")
            if len(rationale.encode("utf-8")) > MAX_RATIONALE_BYTES:
                raise OperationRejected("VALIDATION_ERROR", "rationale is too large")
            if "feedback" in payload and payload["feedback"] not in (None, rationale):
                raise OperationRejected("VALIDATION_ERROR", "rationale and feedback disagree")
            return rationale
        feedback = payload.get("feedback")
        if isinstance(feedback, str) and len(feedback.encode("utf-8")) > MAX_RATIONALE_BYTES:
            raise OperationRejected("VALIDATION_ERROR", "feedback is too large")
        return feedback
    @staticmethod
    def _scoped(envelope: CommandEnvelope, scoped_value: str | None, payload_key: str, label: str) -> str | None:
        payload_value = envelope.payload.get(payload_key)
        if scoped_value is not None and payload_value is not None and scoped_value != payload_value:
            raise CommandFailure(DomainError("FORBIDDEN", f"Payload {label} scope does not match the authenticated scope"))
        if payload_value is not None and not isinstance(payload_value, str):
            raise CommandFailure(DomainError("VALIDATION_ERROR", f"{payload_key} must be a string"))
        return scoped_value or payload_value

    @staticmethod
    def _project_scope(envelope: CommandEnvelope) -> str | None:
        scope_project = envelope.scope.project_id
        payload_project = envelope.payload.get("projectId")
        if scope_project is not None and payload_project is not None and scope_project != payload_project:
            raise CommandFailure(DomainError("FORBIDDEN", "Payload project scope does not match the authenticated scope"))
        if payload_project is not None and not isinstance(payload_project, str):
            raise CommandFailure(DomainError("VALIDATION_ERROR", "projectId must be a string"))
        return scope_project or payload_project

    @staticmethod
    def _required(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise OperationRejected("VALIDATION_ERROR", f"{key} is required")
        return value.strip()

    @staticmethod
    def _run_revision(envelope: CommandEnvelope, run_id: str) -> int:
        matches = [item.revision for item in envelope.expected_versions if item.entity == "run" and item.identity == run_id]
        if len(matches) != 1:
            value = envelope.payload.get("expectedRevision")
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise OperationRejected("VALIDATION_ERROR", "one expected run revision is required")
            return value
        return matches[0]


def dispatch(store: StateStore, value: CommandEnvelope | dict[str, Any]) -> dict[str, Any]:
    return CommandDispatcher(store).dispatch(value)
