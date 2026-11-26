"""Stable component identities and dependency graph validation."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any
from .contracts import CommandFailure, DomainError


@dataclass(frozen=True)
class Component:
    component_id: str
    name: str
    owner: str
    dependencies: tuple[str, ...]
    owned_paths: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"componentId": self.component_id, "name": self.name, "owner": self.owner, "dependencies": list(self.dependencies), "ownedPaths": list(self.owned_paths)}


def _error(message: str) -> CommandFailure:
    return CommandFailure(DomainError("VALIDATION_ERROR", message))


def validate_components(items: list[dict[str, Any]]) -> tuple[Component, ...]:
    if not isinstance(items, list):
        raise _error("components must be a list")
    ids = {item.get("componentId") for item in items if isinstance(item, dict)}
    if len(ids) != len(items) or None in ids:
        raise _error("component IDs must be unique nonempty values")
    components = []
    paths: dict[str, str] = {}
    for item in items:
        if not all(isinstance(item.get(key), str) and item[key].strip() for key in ("componentId", "name", "owner")):
            raise _error("component identity, name, and owner are required")
        dependencies = item.get("dependencies", [])
        owned_paths = item.get("ownedPaths", [])
        if not isinstance(dependencies, list) or len(dependencies) != len(set(dependencies)) or any(not isinstance(value, str) or not value.strip() for value in dependencies):
            raise _error(f"component dependencies are invalid: {item['componentId']}")
        if not isinstance(owned_paths, list) or len(owned_paths) != len(set(owned_paths)) or any(not isinstance(value, str) or not value.strip() for value in owned_paths):
            raise _error(f"component owned paths are invalid: {item['componentId']}")
        for path in owned_paths:
            other = paths.setdefault(path, item["componentId"])
            if other != item["componentId"]:
                raise _error(f"ownership conflict for path: {path}")
        components.append(Component(item["componentId"], item["name"], item["owner"], tuple(dependencies), tuple(owned_paths)))
    component_ids = {item.component_id for item in components}
    graph = {item.component_id: set(item.dependencies) for item in components}
    if any(dependency not in component_ids for values in graph.values() for dependency in values):
        raise _error("component dependency references an unknown component")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(component_id: str) -> None:
        if component_id in visiting:
            raise _error("component dependency cycle detected")
        if component_id in visited:
            return
        visiting.add(component_id)
        for dependency in graph[component_id]:

            visit(dependency)
        visiting.remove(component_id)
        visited.add(component_id)

    for component_id in graph:
        visit(component_id)
    return tuple(components)
def evaluate_batch(items: list[dict[str, Any]], current_revisions: dict[str, int], *, allowed_components: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(items, list) or not items:
        raise _error("batch items must be a nonempty list")
    allowed_components = allowed_components if allowed_components is not None else set(current_revisions)
    outcomes = []
    for item in items:
        component_id = item.get("componentId") if isinstance(item, dict) else None
        expected = item.get("expectedRevision") if isinstance(item, dict) else None
        if not isinstance(component_id, str) or not component_id.strip() or not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            outcomes.append({"componentId": component_id, "status": "Invalid", "reason": {"code": "INVALID_ITEM"}})
        elif component_id not in allowed_components:
            outcomes.append({"componentId": component_id, "status": "Forbidden", "reason": {"code": "COMPONENT_FORBIDDEN"}})
        elif current_revisions.get(component_id) != expected:
            outcomes.append({"componentId": component_id, "status": "Conflict", "reason": {"code": "VERSION_CONFLICT", "currentRevision": current_revisions.get(component_id)}})
        else:
            outcomes.append({"componentId": component_id, "status": "Applied", "reason": None})
    fingerprint = hashlib.sha256(json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"batchFingerprint": fingerprint, "items": outcomes, "applied": [item["componentId"] for item in outcomes if item["status"] == "Applied"]}
