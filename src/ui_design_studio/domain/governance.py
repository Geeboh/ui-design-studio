"""Design spend, model routing, and worker governance primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import threading
import time
from typing import Any


class GovernanceError(RuntimeError):
    """Governance policy rejected an operation."""


class BudgetError(GovernanceError):
    """Budget admission or reconciliation failed."""


@dataclass(frozen=True)
class Money:
    amount_minor: int
    currency_code: str
    currency_exponent: int

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int) or self.amount_minor < 0:
            raise BudgetError("amount_minor must be a nonnegative integer")
        if not isinstance(self.currency_code, str) or not re.fullmatch(r"[A-Z]{3}", self.currency_code):
            raise BudgetError("currency_code must be an uppercase three-letter code")
        if isinstance(self.currency_exponent, bool) or not isinstance(self.currency_exponent, int) or not 0 <= self.currency_exponent <= 9:
            raise BudgetError("currency_exponent must be an integer from 0 through 9")


@dataclass(frozen=True)
class BudgetAccount:
    account_id: str
    cap: Money | None
    enforcement: str = "advisory"
    critique_billable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, str) or not self.account_id.strip():
            raise BudgetError("account_id is required")
        if self.enforcement not in {"hard", "advisory", "unbounded"}:
            raise BudgetError("unsupported budget enforcement mode")
        if self.enforcement == "hard" and self.cap is None:
            raise BudgetError("hard budgets require a cap")


@dataclass
class Reservation:
    reservation_id: str
    amount: Money
    category: str
    status: str = "held"
    observed: Money | None = None
    provider_receipt: str | None = None
    discrepancy_minor: int = 0


class BudgetLedger:
    """Thread-safe in-process ledger used by controlled dispatch and tests."""

    def __init__(self, account: BudgetAccount) -> None:
        self.account = account
        self._reservations: dict[str, Reservation] = {}
        self._settled_design_minor = 0
        self._implementation_minor = 0
        self._receipts: set[str] = set()
        self._lock = threading.RLock()

    def _check_currency(self, money: Money) -> None:
        if self.account.cap is not None and (money.currency_code, money.currency_exponent) != (self.account.cap.currency_code, self.account.cap.currency_exponent):
            raise BudgetError("mixed currency is not supported without an explicit conversion")

    def _held_design(self) -> int:
        return sum(item.amount.amount_minor for item in self._reservations.values() if item.category == "design" and item.status in {"held", "dispatched", "unknown"})

    def reserve(self, reservation_id: str, amount: Money, *, category: str = "design") -> Reservation:
        with self._lock:
            if reservation_id in self._reservations:
                existing = self._reservations[reservation_id]
                if existing.amount != amount or existing.category != category:
                    raise BudgetError("reservation identity was reused with different input")
                return existing
            self._check_currency(amount)
            if category not in {"design", "implementation", "pack"}:
                raise BudgetError("unsupported cost category")
            if category == "design" and self.account.cap is not None:
                available = self.account.cap.amount_minor - self._settled_design_minor - self._held_design()
                if amount.amount_minor > available:
                    raise BudgetError("design budget is insufficient for this reservation")
            reservation = Reservation(reservation_id, amount, category)
            self._reservations[reservation_id] = reservation
            return reservation

    def dispatch(self, reservation_id: str) -> Reservation:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise BudgetError("reservation not found")
            if reservation.status != "held":
                raise BudgetError("only held reservations can dispatch")
            reservation.status = "dispatched"
            return reservation

    def settle(self, reservation_id: str, observed: Money | None, *, provider_receipt: str | None = None) -> Reservation:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise BudgetError("reservation not found")
            if provider_receipt is not None and provider_receipt in self._receipts:
                return reservation
            if observed is None:
                reservation.status = "unknown"
                return reservation
            self._check_currency(observed)
            reservation.observed = observed
            reservation.status = "settled"
            reservation.provider_receipt = provider_receipt
            if provider_receipt is not None:
                self._receipts.add(provider_receipt)
            if reservation.category == "design":
                self._settled_design_minor += observed.amount_minor
            else:
                self._implementation_minor += observed.amount_minor
            reservation.discrepancy_minor = observed.amount_minor - reservation.amount.amount_minor
            return reservation

    def release(self, reservation_id: str) -> Reservation:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise BudgetError("reservation not found")
            if reservation.status != "held":
                raise BudgetError("only undispatched reservations can release")
            reservation.status = "released"
            return reservation

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            cap = self.account.cap.amount_minor if self.account.cap is not None else None
            available = None if cap is None else cap - self._settled_design_minor - self._held_design()
            return {"accountId": self.account.account_id, "enforcement": self.account.enforcement, "currency": None if self.account.cap is None else {"code": self.account.cap.currency_code, "exponent": self.account.cap.currency_exponent}, "capMinor": cap, "settledDesignMinor": self._settled_design_minor, "implementationMinor": self._implementation_minor, "reservedDesignMinor": self._held_design(), "availableMinor": available, "reservations": {key: {"status": value.status, "category": value.category, "amountMinor": value.amount.amount_minor, "observedMinor": None if value.observed is None else value.observed.amount_minor, "discrepancyMinor": value.discrepancy_minor} for key, value in self._reservations.items()}}

@dataclass(frozen=True)
class ModelAssignment:
    requested: str | None
    resolved: str | None
    observed: str | None
    source: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {"requested": self.requested, "resolved": self.resolved, "observed": self.observed, "source": self.source, "status": self.status}


def resolve_model(*, explicit: str | None = None, persisted_run: str | None = None, project_default: str | None = None, personal_default: str | None = None, available: set[str] | None = None, current_model: str | None = None) -> ModelAssignment:
    available = available or set()
    requested = explicit or persisted_run or project_default or personal_default or "auto"
    source = "explicit" if explicit else "persisted_run" if persisted_run else "project_default" if project_default else "personal_default" if personal_default else "auto"
    if requested == "current":
        resolved = current_model if current_model in available else None
    elif requested == "auto":
        resolved = sorted(available)[0] if available else None
    else:
        resolved = requested if requested in available else None
    return ModelAssignment(requested, resolved, None, source, "resolved" if resolved else "unavailable")

@dataclass(frozen=True)
class InstructionSnapshot:
    path: str
    sha256: str
    content: str
    source: str


@dataclass(frozen=True)
class WorkerPacket:
    task_id: str
    objective: str
    input_versions: dict[str, Any]
    owned_paths: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    instructions: tuple[InstructionSnapshot, ...]
    model: ModelAssignment
    dependencies: tuple[str, ...] = ()
    reservation_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "objective": self.objective,
            "inputVersions": self.input_versions,
            "ownedPaths": list(self.owned_paths),
            "allowedActions": list(self.allowed_actions),
            "instructions": [{"path": item.path, "sha256": item.sha256, "content": item.content, "source": item.source} for item in self.instructions],
            "model": self.model.as_dict(),
            "dependencies": list(self.dependencies),
            "reservationId": self.reservation_id,
        }


def build_worker_packet(*, task_id: str, objective: str, input_versions: dict[str, Any], owned_paths: list[str], instructions: list[InstructionSnapshot], model: ModelAssignment, allowed_actions: set[str], dependencies: list[str] | None = None, reservation_id: str | None = None) -> WorkerPacket:
    if not isinstance(task_id, str) or not task_id.strip() or not isinstance(objective, str) or not objective.strip():
        raise GovernanceError("worker task identity and objective are required")
    if not isinstance(input_versions, dict) or not isinstance(owned_paths, list) or not owned_paths or any(not isinstance(path, str) or not path.strip() or path.startswith("/") or ".." in path.split("/") for path in owned_paths):
        raise GovernanceError("worker owned paths must be nonempty repository-relative paths")
    if len(owned_paths) != len(set(owned_paths)) or not isinstance(instructions, list) or not instructions:
        raise GovernanceError("worker owned paths and instruction snapshots must be unique and present")
    actions = tuple(sorted(action for action in allowed_actions if isinstance(action, str) and action.strip()))
    if not actions:
        raise GovernanceError("worker allowed actions are required")
    return WorkerPacket(task_id, objective.strip(), dict(input_versions), tuple(owned_paths), actions, tuple(instructions), model, tuple(dependencies or ()), reservation_id)
@dataclass
class WorkerLease:
    task_id: str
    attempt_id: str
    fencing_token: int
    status: str = "active"
    expires_at: float = field(default_factory=lambda: time.monotonic() + 60)


class LeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, WorkerLease] = {}
        self._tokens: dict[str, int] = {}
        self._lock = threading.RLock()

    def acquire(self, task_id: str, attempt_id: str) -> WorkerLease:
        with self._lock:
            token = self._tokens.get(task_id, 0) + 1
            self._tokens[task_id] = token
            lease = WorkerLease(task_id, attempt_id, token)
            self._leases[task_id] = lease
            return lease

    def heartbeat(self, task_id: str, attempt_id: str, fencing_token: int) -> WorkerLease:
        with self._lock:
            lease = self._leases.get(task_id)
            if lease is None or lease.attempt_id != attempt_id or lease.fencing_token != fencing_token or lease.status != "active":
                raise GovernanceError("stale worker lease")
            lease.expires_at = time.monotonic() + 60
            return lease

    def record_outcome(self, task_id: str, attempt_id: str, fencing_token: int, outcome: str) -> dict[str, Any]:
        with self._lock:
            lease = self._leases.get(task_id)
            if lease is None or lease.attempt_id != attempt_id or lease.fencing_token != fencing_token or lease.status != "active":
                return {"status": "orphaned", "taskId": task_id, "attemptId": attempt_id, "outcome": outcome}
            lease.status = "completed" if outcome in {"succeeded", "failed", "cancelled"} else outcome
            return {"status": "accepted", "taskId": task_id, "attemptId": attempt_id, "outcome": outcome}

    def cancel(self, task_id: str) -> WorkerLease:
        with self._lock:
            lease = self._leases.get(task_id)
            if lease is None:
                raise GovernanceError("worker lease not found")
            if lease.status == "active":
                lease.status = "cancel_requested"
            return lease
