"""Typed command envelopes and stable domain errors."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any


class ContractError(ValueError):
    """Input does not satisfy the shared command contract."""


@dataclass(frozen=True)
class Actor:
    principal: str
    kind: str = "human"
    mode: str = "guided"

    @classmethod
    def from_value(cls, value: Any) -> "Actor":
        if not isinstance(value, dict) or set(value) - {"principal", "kind", "mode"}:
            raise ContractError("actor must contain only principal, kind, and mode")
        principal = value.get("principal")
        kind = value.get("kind", "human")
        mode = value.get("mode", "guided")
        if not all(isinstance(item, str) and item.strip() for item in (principal, kind, mode)):
            raise ContractError("actor principal, kind, and mode are required strings")
        if kind not in {"human", "agent"} or mode not in {"guided", "yolo"}:
            raise ContractError("actor kind or mode is unsupported")
        return cls(principal.strip(), kind, mode)

    def as_dict(self) -> dict[str, str]:
        return {"principal": self.principal, "kind": self.kind, "mode": self.mode}


@dataclass(frozen=True)
class Scope:
    project_id: str | None = None
    run_id: str | None = None
    artifact_digest: str | None = None
    stage: str | None = None

    @classmethod
    def from_value(cls, value: Any) -> "Scope":
        if not isinstance(value, dict) or set(value) - {"projectId", "runId", "artifactDigest", "stage"}:
            raise ContractError("scope contains an unsupported field")
        values = {key: value.get(key) for key in ("projectId", "runId", "artifactDigest", "stage")}
        if any(item is not None and (not isinstance(item, str) or not item.strip()) for item in values.values()):
            raise ContractError("scope values must be nonempty strings or null")
        return cls(values["projectId"], values["runId"], values["artifactDigest"], values["stage"])

    def as_dict(self) -> dict[str, str | None]:
        return {"projectId": self.project_id, "runId": self.run_id, "artifactDigest": self.artifact_digest, "stage": self.stage}


@dataclass(frozen=True)
class VersionRef:
    entity: str
    identity: str
    revision: int

    @classmethod
    def from_value(cls, value: Any) -> "VersionRef":
        if not isinstance(value, dict) or set(value) != {"entity", "identity", "revision"}:
            raise ContractError("expectedVersions entries must contain entity, identity, and revision")
        revision = value["revision"]
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ContractError("expected version revision must be a positive integer")
        if not all(isinstance(value[key], str) and value[key].strip() for key in ("entity", "identity")):
            raise ContractError("expected version identity fields are required strings")
        return cls(value["entity"], value["identity"], revision)

    def as_dict(self) -> dict[str, str | int]:
        return {"entity": self.entity, "identity": self.identity, "revision": self.revision}


@dataclass(frozen=True)
class CommandEnvelope:
    command: str
    operation_id: str
    idempotency_key: str | None
    actor: Actor
    scope: Scope
    expected_versions: tuple[VersionRef, ...]
    payload: dict[str, Any]

    @classmethod
    def from_value(cls, value: Any) -> "CommandEnvelope":
        required = {"command", "operationId", "actor", "scope", "expectedVersions", "payload"}
        optional = {"idempotencyKey"}
        if not isinstance(value, dict) or not required.issubset(value) or set(value) - required - optional:
            raise ContractError("command envelope has missing or unsupported fields")
        command = value["command"]
        operation_id = value["operationId"]
        key = value.get("idempotencyKey")
        if not all(isinstance(item, str) and item.strip() for item in (command, operation_id)):
            raise ContractError("command and operationId are required strings")
        if key is not None and (not isinstance(key, str) or not key.strip()):
            raise ContractError("idempotencyKey must be a nonempty string when supplied")
        versions = value["expectedVersions"]
        if not isinstance(versions, list):
            raise ContractError("expectedVersions must be a list")
        if not isinstance(value["payload"], dict):
            raise ContractError("payload must be an object")
        return cls(command.strip(), operation_id.strip(), key.strip() if key else None, Actor.from_value(value["actor"]), Scope.from_value(value["scope"]), tuple(VersionRef.from_value(item) for item in versions), dict(value["payload"]))

    def request(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "actor": self.actor.as_dict(),
            "scope": self.scope.as_dict(),
            "expectedVersions": [item.as_dict() for item in self.expected_versions],
            "payload": self.payload,
        }


@dataclass(frozen=True)
class DomainError:
    code: str
    message: str
    retry: str = "none"
    field_errors: tuple[dict[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "retry": self.retry, "fieldErrors": list(self.field_errors)}


class CommandFailure(RuntimeError):
    """Stable adapter-neutral command failure."""

    def __init__(self, error: DomainError) -> None:
        super().__init__(error.message)
        self.error = error


def canonical_request(envelope: CommandEnvelope) -> bytes:
    return json.dumps(envelope.request(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def request_fingerprint(envelope: CommandEnvelope) -> str:
    return hashlib.sha256(canonical_request(envelope)).hexdigest()


def require_finite_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("NaN and Infinity are not valid command values")
    if isinstance(value, dict):
        for child in value.values():
            require_finite_json(child)
    elif isinstance(value, list):
        for child in value:
            require_finite_json(child)
