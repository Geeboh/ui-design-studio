import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workflow_has_host_feasibility_before_contract_freeze():
    workflow = (ROOT / ".omp/skills/ui-design-studio/references/workflow.md").read_text(encoding="utf-8")
    feasibility = workflow.index("early host-feasibility slice")
    freeze = workflow.index("freezes `design/contract.md`")
    assert feasibility < freeze
    assert "narrow viewport" in workflow[feasibility:freeze]
    assert "failure or recovery state" in workflow[feasibility:freeze]


def test_offline_quality_policy_is_conditional():
    performance = (ROOT / ".omp/agents/ui-performance-reviewer.md").read_text(encoding="utf-8")
    gates = (ROOT / ".omp/skills/ui-design-studio/references/quality-gates.md").read_text(encoding="utf-8")
    review = (ROOT / ".omp/skills/ui-review/SKILL.md").read_text(encoding="utf-8")
    for text in (performance, gates, review):
        assert "offline: \"required\"" in text or "`required`" in text
        assert "offline: \"not-required\"" in text or "`not-required`" in text
        assert "unknown" in text.lower()
    assert "do not invent an offline product gate" in performance
    assert "network failure and recovery" in gates

def test_quality_review_rounds_are_bounded():
    gates = (ROOT / ".omp/skills/ui-design-studio/references/quality-gates.md").read_text(encoding="utf-8")
    assert "maxReviewIterations" in gates
    assert "remain `BLOCKED`" in gates


def test_original_remediation_contract_is_preserved():
    contract = ROOT / "UI-Design-Studio-v1.4.0-Cortex-Remediation.md"
    assert contract.is_file()
    text = contract.read_text(encoding="utf-8")
    assert "R00 PREFLIGHT / BASELINE" in text
    assert "R15 FINISH / CONTINUATION" in text
    assert "HUMAN/UAT explicitly deferred" in text

def test_benchmark_covers_required_offline_workload_shapes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/remediation_benchmark.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    workloads = payload["workloadSuite"]["workloads"]
    assert {item["id"] for item in workloads} == {
        "tiny-component-fix",
        "new-page-established-system",
        "reference-inspired-flow",
        "dense-offline-appliance-screen",
        "full-multi-page-redesign",
        "resume-after-token-change",
    }
    assert payload["workloadSuite"]["fixtureRequirements"]["offline"] == "required"
    assert all(item["expectedAcceptance"] for item in workloads)
