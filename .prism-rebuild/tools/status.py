#!/usr/bin/env python3
"""Summarize observed rebuild progress; missing or stale results stay explicit."""
import argparse
from pathlib import Path
import sys
from prism_pack import candidate_snapshot, emit, file_digest, read_json, receipt_evidence_errors, repo_root, safe_child, state_path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    root = repo_root(args.repo)
    current = candidate_snapshot(root)
    state = state_path(root)
    progress_path = state_path(root, "progress.json")
    progress = read_json(progress_path) if progress_path.is_file() else {"status": "NOT_STARTED", "milestones": []}
    results = {}
    for profile in ["core", "web", "release"]:
        index = state_path(root, "latest-" + profile + ".json")
        if not index.is_file():
            results[profile] = {"status": "NOT_RUN"}
            continue
        summary = read_json(index)
        if Path(summary["receiptPath"]).parts[:1] != (".prism-state",):
            raise ValueError("Gate receipts must be inside private state")
        state_path(root, Path(*Path(summary["receiptPath"]).parts[1:]))
        receipt_path = safe_child(root, summary["receiptPath"], must_exist=True)
        receipt = read_json(receipt_path)
        errors = receipt_evidence_errors(root, receipt)
        if file_digest(receipt_path) != summary.get("receiptSha256"):
            errors.append("Receipt digest differs from the recorded index")
        fresh = receipt.get("sourceFingerprintSha256") == current["sha256"] and not errors
        results[profile] = {"status": receipt["status"], "current": fresh, "selectedGatesOnly": receipt.get("selectedGatesOnly", False), "receipt": summary["receiptPath"], "planPath": receipt.get("planPath"), "evidenceErrors": errors, "note": "Stale source, changed plans/reviews, or missing/altered evidence are historical, not current qualification."}
    emit({"sourceFingerprintSha256": current["sha256"], "sourceClean": current["clean"], "progress": progress, "observedVerification": results, "humanValidation": "DEFERRED"})

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        emit({"status": "BLOCKED", "error": str(exc)})
        sys.exit(2)
