#!/usr/bin/env python3
"""Measure bounded knowledge selection and dashboard snapshot work."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from ui_design_studio.knowledge import load_rules, select_rules
from test_studio import fixture_theme, studio
from test_design_server import backend


parser = argparse.ArgumentParser()
parser.add_argument("--iterations", type=int, default=50)
parser.add_argument("--rules", default=".prism-rebuild/knowledge/rules.json")
parser.add_argument("--snapshot-files", type=int, default=40)
args = parser.parse_args()
if not 1 <= args.iterations <= 1000:
    raise SystemExit("iterations must be between 1 and 1000")
if not 1 <= args.snapshot_files <= 500:
    raise SystemExit("snapshot-files must be between 1 and 500")


def percentile(samples, value):
    ordered = sorted(samples)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * value))
    return ordered[index]


path = Path(args.rules).resolve()
content = path.read_bytes()
rules = load_rules(path)
knowledge_samples = []
for _ in range(args.iterations):
    started = time.perf_counter()
    selected = select_rules(rules, "bounded worker instructions approval accessibility", limit=8)
    knowledge_samples.append((time.perf_counter() - started) * 1000)
assert selected

with tempfile.TemporaryDirectory(prefix="prism-performance-") as temporary:
    repo = Path(temporary)
    fixture_theme(repo)
    root = Path(studio.init_run(repo, theme_id="fixture")["run"])
    for index in range(args.snapshot_files):
        (root / f"artifact-{index:03d}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>\n',
            encoding="utf-8",
        )
    server = backend.DesignServer(studio, root, interval=60).start()
    try:
        server.state.snapshot()
        snapshot_samples = []
        for _ in range(args.iterations):
            started = time.perf_counter()
            snapshot = server.state.snapshot()
            snapshot_samples.append((time.perf_counter() - started) * 1000)
            assert snapshot["statistics"]["artworks"] >= args.snapshot_files
    finally:
        server.close()

print(json.dumps({
    "status": "PASS",
    "fixture": str(path),
    "fixtureSha256": hashlib.sha256(content).hexdigest(),
    "rules": len(rules),
    "iterations": len(knowledge_samples),
    "errors": 0,
    "knowledge": {"p50Ms": percentile(knowledge_samples, 0.5), "p95Ms": percentile(knowledge_samples, 0.95), "samplesMs": knowledge_samples},
    "snapshot": {"fixtureFiles": args.snapshot_files, "p50Ms": percentile(snapshot_samples, 0.5), "p95Ms": percentile(snapshot_samples, 0.95), "samplesMs": snapshot_samples},
}, sort_keys=True))
