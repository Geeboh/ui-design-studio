#!/usr/bin/env python3
"""Measure deterministic remediation deltas with one offline synthetic fixture."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


studio = load("remediation_studio", ROOT / ".omp/skills/ui-design-studio/scripts/studio.py")
design = load("remediation_design_server", ROOT / ".omp/skills/ui-design-studio/scripts/design_server.py")


def snapshot(count):
    return {
        "revision": "fixture-1",
        "observedAt": "2026-01-01T00:00:00+00:00",
        "run": {"id": "fixture", "phase": "produce", "status": "pending", "scope": "component"},
        "gates": [{"id": "assessment", "status": "PASS"}],
        "coverage": {"surfaces": 1, "cases": count},
        "statistics": {"artworks": count, "evidence": count},
        "nextAction": "Review bounded synthetic state",
        "blockers": [],
        "warnings": [],
        "workers": [],
        "tasks": [],
        "artworks": [{"id": f"art-{index:04d}", "path": f"art/{index:04d}.html", "html": "x" * 128} for index in range(count)],
        "evidence": [{"id": f"evidence-{index:04d}", "path": f"evidence/{index:04d}.md", "details": "x" * 128} for index in range(count)],
    }


def measure(function, samples=5):
    values = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        function()
        values.append((time.perf_counter_ns() - started) / 1_000_000)
    return {"samples": samples, "meanMs": round(statistics.mean(values), 4),
            "stdevMs": round(statistics.pstdev(values), 4), "minMs": round(min(values), 4),
            "maxMs": round(max(values), 4)}


def status_measurements():
    results = []
    for count in (0, 100, 1000):
        value = snapshot(count)
        legacy = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        compact = json.dumps(design.compact_status(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        results.append({"items": count, "baselineBytes": len(legacy), "changedBytes": len(compact),
                        "baseline": measure(lambda: json.dumps(value, sort_keys=True, separators=(",", ":"))),
                        "changed": measure(lambda: design.compact_status(value))})
    return results


def hash_measurement():
    with tempfile.TemporaryDirectory(prefix="ui-remediation-bench-") as directory:
        root = Path(directory)
        shared = root / "shared.md"
        report = root / "report.md"
        shared.write_text("shared fixture input\n", encoding="utf-8")
        report.write_text("shared fixture report\n", encoding="utf-8")
        shared_hash = studio.sha_file(shared)
        report_hash = studio.sha_file(report)
        entry = {"id": "evidence", "kind": "integration", "path": "report.md", "sha256": report_hash,
                 "inputs": ["shared.md"], "inputsDigest": studio.digest_bytes(studio.canonical({"shared.md": shared_hash})),
                 "status": "passed", "reviewer": "bench-reviewer", "recordedAt": studio.now()}
        calls = {"count": 0}
        original = studio.sha_file

        def counted(path):
            calls["count"] += 1
            return original(path)

        studio.sha_file = counted
        try:
            uncached = measure(lambda: studio.validate_evidence_entry(root, entry, {}), samples=3)
            uncached_calls = calls["count"]
            calls["count"] = 0
            cache = {}
            cached = measure(lambda: studio.validate_evidence_entry(root, entry, cache), samples=3)
            cached_calls = calls["count"]
        finally:
            studio.sha_file = original
        return {"baseline": {**uncached, "shaCalls": uncached_calls},
                "changed": {**cached, "shaCalls": cached_calls},
                "fixture": "one report and one shared bound input"}


def phase_measurement():
    router = (ROOT / ".omp/skills/ui-design-studio/SKILL.md").read_text(encoding="utf-8")
    public = [path.read_text(encoding="utf-8") for path in sorted((ROOT / ".omp/skills").glob("ui-*/SKILL.md"))]
    hot_path = router + (ROOT / ".omp/skills/ui-design-studio/references/workflow.md").read_text(encoding="utf-8")
    return {"baseline": {"bytes": sum(len(text.encode()) for text in public), "words": sum(len(text.split()) for text in public),
                         "description": "all public phase skills preloaded"},
            "changed": {"bytes": len(hot_path.encode()), "words": len(hot_path.split()),
                        "description": "director router plus workflow reference"},
            "caveat": "Baseline is a same-revision full-preload proxy, not an unmodified archive measurement."}


def scoped_measurement():
    domain = 2 * 2
    applicable = 3
    return {"baseline": {"requiredCases": domain, "description": "legacy Cartesian state x viewport grid"},
            "changed": {"requiredCases": applicable, "description": "explicit applicable cases with one explained exclusion"},
            "fixture": "one surface, two states, two viewports"}

FIXTURE_REQUIREMENTS = {
    "platform": "web",
    "offline": "required",
    "quality": "WCAG-2.2-AA",
    "states": ["ready", "error"],
    "viewports": ["mobile", "desktop"],
}

WORKLOADS = (
    ("tiny-component-fix", "Fix one existing component state.", "fix", 9, 4,
     ("affected state coverage", "independent review", "no unrelated concepts")),
    ("new-page-established-system", "Add one page using the existing system.", "component", 9, 7,
     ("page coverage", "responsive states", "independent review")),
    ("reference-inspired-flow", "Adapt one reference-driven flow.", "reference-adaptation", 9, 7,
     ("reference interpretation", "flow recovery", "accessibility checks")),
    ("dense-offline-appliance-screen", "Add a dense offline appliance screen.", "single-flow", 9, 7,
     ("offline cold/WAN/warm checks", "long-content handling", "recovery state")),
    ("full-multi-page-redesign", "Redesign multiple pages across the system.", "full-redesign", 9, 9,
     ("two concepts", "early host feasibility", "full applicable coverage")),
    ("resume-after-token-change", "Resume after a shared token changes.", "component", 9, 4,
     ("changed dependency stale", "unrelated work retained", "re-review required")),
)


def workload_measurements():
    return {
        "fixtureRequirements": FIXTURE_REQUIREMENTS,
        "simulation": "Deterministic orchestration shape only; no provider or user run was executed.",
        "workloads": [
            {
                "id": workload_id,
                "request": request,
                "scope": scope,
                "expectedAcceptance": list(acceptance),
                "baseline": {"orchestrationSteps": baseline_steps, "description": "full workflow shape"},
                "changed": {"orchestrationSteps": changed_steps, "description": "scope-aware workflow shape"},
            }
            for workload_id, request, scope, baseline_steps, changed_steps, acceptance in WORKLOADS
        ],
    }


def validate_workload_measurements(value):
    workloads = value["workloads"]
    assert len(workloads) == 6
    assert len({item["id"] for item in workloads}) == 6
    assert all(item["expectedAcceptance"] for item in workloads)
    return value


def workload_suite():
    return validate_workload_measurements(workload_measurements())


def main():
    result = {"schemaVersion": "1.0", "status": "PASS", "mode": "offline-synthetic",
              "python": sys.version.split()[0], "fixture": "fixed in scripts/remediation_benchmark.py",
              "compactStatus": status_measurements(), "validationHashReuse": hash_measurement(),
              "phaseContext": phase_measurement(), "scopedWorkflow": scoped_measurement(),
              "workloadSuite": workload_suite(),
              "limitations": ["No live provider, browser, device, or user data was used.",
                              "Timing values are local synthetic measurements, not field performance.",
                              "Workload suite values are deterministic orchestration-shape simulations."]}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


