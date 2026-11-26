#!/usr/bin/env python3
"""Measure bounded knowledge selection on a reproducible local fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from ui_design_studio.knowledge import load_rules, select_rules


parser = argparse.ArgumentParser()
parser.add_argument("--iterations", type=int, default=50)
parser.add_argument("--rules", default=".prism-rebuild/knowledge/rules.json")
args = parser.parse_args()
if not 1 <= args.iterations <= 1000:
    raise SystemExit("iterations must be between 1 and 1000")
path = Path(args.rules).resolve()
content = path.read_bytes()
rules = load_rules(path)
samples = []
for _ in range(args.iterations):
    started = time.perf_counter()
    selected = select_rules(rules, "bounded worker instructions approval accessibility", limit=8)
    samples.append((time.perf_counter() - started) * 1000)
assert selected
ordered = sorted(samples)
def percentile(value: float) -> float:
    index = min(len(ordered) - 1, round((len(ordered) - 1) * value))
    return ordered[index]
print(json.dumps({"status": "PASS", "fixture": str(path), "fixtureSha256": hashlib.sha256(content).hexdigest(), "rules": len(rules), "iterations": len(samples), "errors": 0, "p50Ms": percentile(0.5), "p95Ms": percentile(0.95), "samplesMs": samples}, sort_keys=True))
