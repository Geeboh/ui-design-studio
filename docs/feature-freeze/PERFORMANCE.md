# Performance review

No performance optimization was made. No speedup or field-performance claim is made.

The current offline benchmark was executed with CPython 3.13.16. The table reports serialized fixture bytes, not request latency:

| Artwork/evidence items per collection | Full fixture bytes | Compact fixture bytes |
| --- | ---: | ---: |
| 0 | 394 | 388 |
| 100 | 37,298 | 394 |
| 1,000 | 369,401 | 397 |

The same synthetic validation fixture recorded six SHA calls without shared cache reuse and two with reuse across three checks. This describes existing behavior, not a new improvement. Six workload-shape records passed their existing deterministic assertions.

Reproduce with `python scripts/remediation_benchmark.py`. Local output is retained at `/tmp/ui-design-freeze-baseline/release-benchmark.json`.

Timing comparisons remain inconclusive. The full-status side measures JSON serialization, while the compact side measures object projection without serialization. Hash timings use three non-interleaved samples and do not validate results inside the timed region. Historical prose now states these limits rather than implying comparable work.

The source review found probe starvation under a shared timeout. Selected/owned-first scheduling corrects liveness without multiplying the deadline by run count. Its regression uses actual stalled HTTP owners. No uncontrolled duration is interpreted as a product-performance target.

The host had 16 logical CPUs and load averages near 2.7 to 2.9 during the audit. Parallel checks and other work preclude controlled latency conclusions. Benchmark redesign and speculative micro-optimizations were skipped because no measured product bottleneck justified them.

