"""Approval feedback normalization and actor/mode rules."""
from __future__ import annotations

from typing import Any
import hashlib
import json

from .contracts import CommandFailure, DomainError


OUTCOMES = {"approved", "changes", "rejected"}


def normalize_feedback(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise CommandFailure(DomainError("VALIDATION_ERROR", "feedback must be a string or null", field_errors=({"path": "payload.feedback", "code": "type", "message": "Expected string or null"},)))
    return value.strip()


def validate_decision(*, outcome: Any, feedback: Any, annotations: Any, actor_kind: str, mode: str) -> str:
    if outcome not in OUTCOMES:
        raise CommandFailure(DomainError("VALIDATION_ERROR", "outcome is unsupported", field_errors=({"path": "payload.outcome", "code": "enum", "message": "Expected approved, changes, or rejected"},)))
    normalized = normalize_feedback(feedback)
    if annotations is not None and (not isinstance(annotations, list) or any(not isinstance(item, dict) for item in annotations)):
        raise CommandFailure(DomainError("VALIDATION_ERROR", "annotations must be a list of objects", field_errors=({"path": "payload.annotations", "code": "type", "message": "Expected object list"},)))
    has_annotations = bool(annotations)
    if outcome == "changes" and not normalized and not has_annotations:
        raise CommandFailure(DomainError("VALIDATION_ERROR", "changes requires feedback or annotations", field_errors=({"path": "payload.feedback", "code": "required", "message": "Provide actionable feedback or an annotation"},)))
    if outcome == "rejected" and not normalized:
        raise CommandFailure(DomainError("VALIDATION_ERROR", "rejected requires feedback", field_errors=({"path": "payload.feedback", "code": "required", "message": "Provide an explanatory reason"},)))
    if outcome == "approved" and mode == "yolo" and actor_kind == "agent" and not normalized:
        raise CommandFailure(DomainError("FORBIDDEN", "delegated agent approval requires an explanation"))
    return normalized

_NON_MATERIAL_FIELDS = {
    "progress", "lastViewedAt", "displayTitle", "pollingAt", "watchTimestamp",
    "updatedAt", "gitRevision", "gitDirty",
}


def _material(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {name: _material(child, name) for name, child in sorted(value.items()) if name not in _NON_MATERIAL_FIELDS}
    if isinstance(value, list):
        items = [_material(child, key) for child in value]
        if key in {"components", "componentIds", "dependencies", "dependencyVersions", "criteria", "requirements"}:
            return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        return items
    return value


def canonical_approval_manifest(manifest: Any) -> bytes:
    if not isinstance(manifest, dict):
        raise CommandFailure(DomainError("VALIDATION_ERROR", "approval manifest must be an object"))
    return json.dumps(_material(manifest), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def approval_fingerprint(manifest: Any) -> str:
    return hashlib.sha256(b"prism-approval-v2\n" + canonical_approval_manifest(manifest)).hexdigest()


def approval_applicability(decision: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    current_fingerprint = approval_fingerprint(manifest)
    if decision.get("outcome") != "approved":
        reasons.append({"code": "DECISION_NOT_APPROVED", "message": "The historical decision is not Approved."})
    if decision.get("scopeFingerprint") != current_fingerprint:
        reasons.append({"code": "SCOPE_CHANGED", "message": "Relevant approval scope or criteria changed."})
    if decision.get("artifactDigest") != manifest.get("artifactDigest"):
        reasons.append({"code": "ARTIFACT_CHANGED", "message": "The approved artifact bytes changed."})
    if decision.get("dependencyFingerprint") != manifest.get("dependencyFingerprint"):
        reasons.append({"code": "DEPENDENCY_CHANGED", "message": "A relevant dependency version changed."})
    return {"applicable": not reasons, "scopeFingerprint": current_fingerprint, "reasons": reasons}

def allowed_actions(*, state: str, actor_kind: str, mode: str) -> dict[str, dict[str, Any]]:
    if state not in {"pending", "reviewable", "approved", "changes", "rejected", "cancelled", "completed"}:
        raise CommandFailure(DomainError("VALIDATION_ERROR", "decision state is unsupported"))
    actions = {
        "approve": {"enabled": False, "reason": {"code": "NOT_REVIEWABLE", "message": "Decision is not currently reviewable."}},
        "request_changes": {"enabled": False, "reason": {"code": "NOT_REVIEWABLE", "message": "Decision is not currently reviewable."}},
        "reject": {"enabled": False, "reason": {"code": "NOT_REVIEWABLE", "message": "Decision is not currently reviewable."}},
        "cancel": {"enabled": state in {"pending", "reviewable", "changes"}, "reason": None if state in {"pending", "reviewable", "changes"} else {"code": "TERMINAL_DECISION", "message": "Terminal decisions cannot be cancelled."}},
    }
    if state == "reviewable":
        for action in ("approve", "request_changes", "reject"):
            actions[action] = {"enabled": True, "reason": None}
        if mode == "guided" and actor_kind == "agent":
            for action in ("approve", "request_changes", "reject"):
                actions[action] = {"enabled": False, "reason": {"code": "HUMAN_DECISION_REQUIRED", "message": "Guided mode requires a human decision."}}
    return actions
