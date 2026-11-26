"""Exact-image annotation and focused revision contracts."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .contracts import CommandFailure, DomainError


MAX_ANNOTATIONS = 256
MAX_POINTS = 128
MAX_ANNOTATION_TEXT = 4000
TOOLS = {"arrow", "line", "rectangle", "ellipse", "pin", "text", "freehand"}
TWO_POINT_TOOLS = {"arrow", "line", "rectangle", "ellipse"}
ONE_POINT_TOOLS = {"pin", "text"}


@dataclass(frozen=True)
class AnnotationSet:
    annotation_set_id: str
    revision: int
    base_artifact_digest: str
    image_width: int
    image_height: int
    annotations: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "annotationSetId": self.annotation_set_id,
            "revision": self.revision,
            "baseArtifactDigest": self.base_artifact_digest,
            "imageSize": {"widthPx": self.image_width, "heightPx": self.image_height},
            "coordinateSpace": "normalized_image",
            "annotations": [dict(item) for item in self.annotations],
        }


@dataclass(frozen=True)
class RevisionRequest:
    revision_request_id: str
    base_artifact_digest: str
    annotation_set_id: str
    annotation_revision: int
    component_ids: tuple[str, ...]
    instructions: str
    retained_constraints: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "revisionRequestId": self.revision_request_id,
            "baseArtifactDigest": self.base_artifact_digest,
            "annotationSetId": self.annotation_set_id,
            "annotationRevision": self.annotation_revision,
            "componentIds": list(self.component_ids),
            "instructions": self.instructions,
            "retainedConstraints": list(self.retained_constraints),
        }


def _failure(path: str, message: str) -> CommandFailure:
    return CommandFailure(DomainError("VALIDATION_ERROR", message, field_errors=({"path": path, "code": "invalid", "message": message},)))


def _point(value: Any, path: str) -> list[float]:
    if isinstance(value, dict):
        value = [value.get("x"), value.get("y")]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise _failure(path, "point must contain x and y")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item) or not 0 <= item <= 1 for item in value):
        raise _failure(path, "point coordinates must be finite normalized values")
    return [float(value[0]), float(value[1])]


def simplify_freehand(points: list[Any], limit: int = MAX_POINTS) -> list[list[float]]:
    if not isinstance(limit, int) or limit < 2:
        raise ValueError("point limit must be at least two")
    normalized = [_point(point, "points") for point in points]
    if len(normalized) <= limit:
        return normalized
    indices = [round(index * (len(normalized) - 1) / (limit - 1)) for index in range(limit)]
    return [normalized[index] for index in indices]


def validate_annotation_set(*, annotation_set_id: str, revision: int, base_artifact_digest: str, image_size: dict[str, Any], annotations: Any) -> AnnotationSet:
    if not isinstance(annotation_set_id, str) or not annotation_set_id.strip():
        raise _failure("annotationSetId", "annotation set identity is required")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise _failure("revision", "annotation revision must be positive")
    if not isinstance(base_artifact_digest, str) or len(base_artifact_digest) != 64:
        raise _failure("baseArtifactDigest", "annotation base digest is required")
    if not isinstance(image_size, dict):
        raise _failure("imageSize", "image size is required")
    width, height = image_size.get("widthPx"), image_size.get("heightPx")
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (width, height)):
        raise _failure("imageSize", "image dimensions must be positive integers")
    if not isinstance(annotations, list) or len(annotations) > MAX_ANNOTATIONS:
        raise _failure("annotations", f"annotation count must be between zero and {MAX_ANNOTATIONS}")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(annotations):
        path = f"annotations[{index}]"
        if not isinstance(item, dict) or item.get("tool") not in TOOLS:
            raise _failure(path, "annotation tool is unsupported")
        tool = item["tool"]
        points = item.get("points")
        if not isinstance(points, list):
            raise _failure(path + ".points", "annotation points must be a list")
        if tool in TWO_POINT_TOOLS and len(points) != 2:
            raise _failure(path + ".points", "line-like annotations need pointer-down and final endpoint")
        if tool in ONE_POINT_TOOLS and len(points) != 1:
            raise _failure(path + ".points", "point annotations need one point")
        if tool == "freehand" and not 2 <= len(points) <= MAX_POINTS:
            raise _failure(path + ".points", f"freehand annotations need between 2 and {MAX_POINTS} points")
        normalized_points = [_point(point, path + ".points") for point in points]
        text = item.get("text", "")
        if not isinstance(text, str) or len(text) > MAX_ANNOTATION_TEXT or (tool == "text" and not text.strip()):
            raise _failure(path + ".text", "annotation text is invalid")
        normalized.append({"tool": tool, "points": normalized_points, "text": text})
    return AnnotationSet(annotation_set_id, revision, base_artifact_digest, width, height, tuple(normalized))


def create_revision_request(*, revision_request_id: str, base_artifact_digest: str, annotation_set: AnnotationSet, component_ids: list[str], instructions: str, retained_constraints: list[str] | None = None) -> RevisionRequest:
    if not isinstance(revision_request_id, str) or not revision_request_id.strip():
        raise _failure("revisionRequestId", "revision request identity is required")
    if not isinstance(component_ids, list) or len(component_ids) != len(set(component_ids)) or any(not isinstance(item, str) or not item.strip() for item in component_ids):
        raise _failure("componentIds", "component IDs must be unique nonempty strings")
    if base_artifact_digest != annotation_set.base_artifact_digest:
        raise _failure("baseArtifactDigest", "revision base does not match annotation image")
    if not isinstance(instructions, str) or not instructions.strip():
        raise _failure("instructions", "revision instructions are required")
    constraints = retained_constraints or []
    if any(not isinstance(item, str) or not item.strip() for item in constraints):
        raise _failure("retainedConstraints", "retained constraints must be nonempty strings")
    return RevisionRequest(revision_request_id, base_artifact_digest, annotation_set.annotation_set_id, annotation_set.revision, tuple(component_ids), instructions.strip(), tuple(constraints))

@dataclass(frozen=True)
class RevisionLineage:
    revision_id: str
    parent_ids: tuple[str, ...]
    changed_components: tuple[str, ...]
    merge_outcome: str
    conflicts: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "revisionId": self.revision_id,
            "parentIds": list(self.parent_ids),
            "changedComponents": list(self.changed_components),
            "mergeOutcome": self.merge_outcome,
            "conflicts": [dict(item) for item in self.conflicts],
        }


def merge_revision_lineage(revision_id: str, left: dict[str, Any], right: dict[str, Any]) -> RevisionLineage:
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise _failure("revisionId", "revision identity is required")
    left_changes = left.get("changes", {}) if isinstance(left, dict) else {}
    right_changes = right.get("changes", {}) if isinstance(right, dict) else {}
    if not isinstance(left_changes, dict) or not isinstance(right_changes, dict):
        raise _failure("changes", "revision changes must be objects")
    conflicts = []
    for key in sorted(set(left_changes) & set(right_changes)):
        if left_changes[key] != right_changes[key]:
            conflicts.append({"path": key, "left": left_changes[key], "right": right_changes[key], "code": "SHARED_DEPENDENCY_CHANGED"})
    components = sorted(set(left.get("componentIds", [])) | set(right.get("componentIds", [])))
    return RevisionLineage(revision_id, (left.get("revisionId", ""), right.get("revisionId", "")), tuple(components), "conflict" if conflicts else "merged", tuple(conflicts))
