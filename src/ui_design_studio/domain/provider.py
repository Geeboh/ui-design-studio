"""Controlled provider attempts and uncertain-outcome reconciliation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .governance import Money


class ProviderError(RuntimeError):
    """Provider lifecycle transition rejected."""


@dataclass
class ProviderAttempt:
    attempt_id: str
    request_fingerprint: str
    provider: str
    model_requested: str
    model_observed: str | None
    reservation_id: str
    execution_state: str = "prepared"
    billing_state: str = "unknown"
    charge: Money | None = None
    discrepancy_minor: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "attemptId": self.attempt_id,
            "requestFingerprint": self.request_fingerprint,
            "provider": self.provider,
            "modelRequested": self.model_requested,
            "modelObserved": self.model_observed,
            "reservationId": self.reservation_id,
            "executionState": self.execution_state,
            "billingState": self.billing_state,
            "charge": None if self.charge is None else {"amountMinor": self.charge.amount_minor, "currencyCode": self.charge.currency_code, "currencyExponent": self.charge.currency_exponent},
            "discrepancyMinor": self.discrepancy_minor,
        }


class ProviderReconciler:
    def __init__(self) -> None:
        self.attempts: dict[str, ProviderAttempt] = {}
        self.receipts: dict[str, str] = {}

    def prepare(self, attempt: ProviderAttempt) -> ProviderAttempt:
        existing = self.attempts.get(attempt.attempt_id)
        if existing is not None:
            if existing.request_fingerprint != attempt.request_fingerprint:
                raise ProviderError("attempt identity was reused with a different request")
            return existing
        self.attempts[attempt.attempt_id] = attempt
        return attempt

    def mark_unknown(self, attempt_id: str) -> ProviderAttempt:
        attempt = self._get(attempt_id)
        if attempt.billing_state == "settled" or attempt.execution_state in {"succeeded", "failed", "cancelled"}:
            raise ProviderError("provider attempt is terminal")
        if attempt.execution_state == "outcome_unknown":
            return attempt
        attempt.execution_state = "outcome_unknown"
        attempt.billing_state = "unknown"
        return attempt

    def reconcile(self, attempt_id: str, provider_receipt: str, charge: Money, *, reserved_minor: int) -> ProviderAttempt:
        if not isinstance(provider_receipt, str) or not provider_receipt.strip():
            raise ProviderError("provider receipt is required")
        attempt = self._get(attempt_id)
        bound_attempt = self.receipts.get(provider_receipt)
        if bound_attempt is not None:
            if bound_attempt != attempt_id:
                raise ProviderError("provider receipt belongs to a different attempt")
            if attempt.charge != charge:
                raise ProviderError("attempt was reconciled with a different charge")
            return attempt
        if attempt.charge is not None or attempt.billing_state == "settled":
            raise ProviderError("provider attempt is already reconciled")
        attempt.charge = charge
        attempt.billing_state = "settled"
        if attempt.execution_state in {"prepared", "outcome_unknown"}:
            attempt.execution_state = "succeeded"
        attempt.discrepancy_minor = charge.amount_minor - reserved_minor
        self.receipts[provider_receipt] = attempt_id
        return attempt

    def _get(self, attempt_id: str) -> ProviderAttempt:
        try:
            return self.attempts[attempt_id]
        except KeyError as exc:
            raise ProviderError("provider attempt not found") from exc
