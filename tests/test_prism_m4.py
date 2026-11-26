from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import unittest

from ui_design_studio.domain.governance import BudgetAccount, BudgetError, BudgetLedger, GovernanceError, InstructionSnapshot, LeaseManager, Money, build_worker_packet, resolve_model
from ui_design_studio.domain.provider import ProviderAttempt, ProviderReconciler


class GovernanceTests(unittest.TestCase):
    def test_budget_contention_unknown_and_duplicate_settlement(self):
        ledger = BudgetLedger(BudgetAccount("run", Money(70, "USD", 2), "hard"))
        amount = Money(50, "USD", 2)

        def reserve(key):
            try:
                ledger.reserve(key, amount)
                return "accepted"
            except BudgetError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(reserve, ("a", "b"))), ["accepted", "rejected"])
        ledger.reserve("uncertain", Money(10, "USD", 2))
        ledger.dispatch("uncertain")
        ledger.settle("uncertain", None)
        self.assertEqual(ledger.snapshot()["reservedDesignMinor"], 60)
        ledger.settle("uncertain", Money(15, "USD", 2), provider_receipt="receipt-1")
        ledger.settle("uncertain", Money(15, "USD", 2), provider_receipt="receipt-1")
        self.assertEqual(ledger.snapshot()["settledDesignMinor"], 15)
        self.assertEqual(ledger.snapshot()["reservations"]["uncertain"]["discrepancyMinor"], 5)
    def test_model_precedence_and_unavailable_assignment(self):
        explicit = resolve_model(explicit="model-explicit", persisted_run="model-run", project_default="model-project", personal_default="model-personal", available={"model-explicit", "model-run"})
        persisted = resolve_model(persisted_run="model-run", project_default="model-project", available={"model-run", "model-project"})
        current = resolve_model(explicit="current", current_model="model-current", available={"model-current"})
        unknown = resolve_model(explicit="missing", available={"known"})
        self.assertEqual((explicit.source, explicit.resolved), ("explicit", "model-explicit"))
        self.assertEqual((persisted.source, persisted.resolved), ("persisted_run", "model-run"))
        self.assertEqual(current.resolved, "model-current")
        self.assertEqual((unknown.status, unknown.resolved), ("unavailable", None))
    def test_worker_packet_keeps_instructions_and_rejects_traversal(self):
        model = resolve_model(explicit="model-a", available={"model-a"})
        packet = build_worker_packet(task_id="task-1", objective="Update component", input_versions={"artifact": "v1"}, owned_paths=["components/content.html"], instructions=[InstructionSnapshot("AGENTS.md", "a" * 64, "Read-only", "project")], model=model, allowed_actions={"read", "write-owned"})
        self.assertEqual(packet.as_dict()["instructions"][0]["content"], "Read-only")
        with self.assertRaises(GovernanceError):
            build_worker_packet(task_id="task-2", objective="Bad", input_versions={}, owned_paths=["../escape"], instructions=list(packet.instructions), model=model, allowed_actions={"read"})
    def test_lease_fencing_orphans_stale_outcomes_and_blocks_cancelled_heartbeat(self):
        manager = LeaseManager()
        first = manager.acquire("task", "attempt-1")
        second = manager.acquire("task", "attempt-2")
        self.assertEqual(manager.record_outcome("task", "attempt-1", first.fencing_token, "succeeded")["status"], "orphaned")
        self.assertEqual(manager.record_outcome("task", "attempt-2", second.fencing_token, "succeeded")["status"], "accepted")
        current = manager.acquire("task-3", "attempt-3")
        self.assertEqual(manager.cancel("task-3").status, "cancel_requested")
        with self.assertRaises(GovernanceError):
            manager.heartbeat("task-3", "attempt-3", current.fencing_token)
    def test_provider_reconciliation_keeps_unknown_and_duplicate_receipt_idempotent(self):
        reconciler = ProviderReconciler()
        attempt = reconciler.prepare(ProviderAttempt("attempt-1", "request-1", "fixture", "model-a", None, "reservation-1"))
        reconciler.mark_unknown(attempt.attempt_id)
        settled = reconciler.reconcile(attempt.attempt_id, "receipt-1", Money(55, "USD", 2), reserved_minor=50)
        duplicate = reconciler.reconcile(attempt.attempt_id, "receipt-1", Money(55, "USD", 2), reserved_minor=50)
        self.assertEqual((settled.execution_state, settled.billing_state, settled.discrepancy_minor), ("succeeded", "settled", 5))
        self.assertIs(duplicate, settled)


if __name__ == "__main__":
    unittest.main()
