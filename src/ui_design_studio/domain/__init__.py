"""PRISM Studio domain contracts and invariant helpers."""

from .contracts import (
    Actor,
    CommandEnvelope,
    CommandFailure,
    ContractError,
    DomainError,
    Scope,
    VersionRef,
    canonical_request,
    request_fingerprint,
)
from .decisions import allowed_actions, approval_applicability, approval_fingerprint, canonical_approval_manifest, normalize_feedback, validate_decision
from .revisions import AnnotationSet, RevisionLineage, RevisionRequest, create_revision_request, merge_revision_lineage, simplify_freehand, validate_annotation_set
from .components import Component, evaluate_batch, validate_components

__all__ = [
    "Actor",
    "CommandEnvelope",
    "CommandFailure",
    "ContractError",
    "DomainError",
    "Scope",
    "VersionRef",
    "canonical_request",
    "request_fingerprint",
    "normalize_feedback",
    "validate_decision",
    "allowed_actions",
    "approval_applicability",
    "approval_fingerprint",
    "canonical_approval_manifest",
    "AnnotationSet",
    "RevisionRequest",
    "create_revision_request",
    "simplify_freehand",
    "validate_annotation_set",
    "RevisionLineage",
    "merge_revision_lineage",
    "Component",
    "evaluate_batch",
    "validate_components",
]
