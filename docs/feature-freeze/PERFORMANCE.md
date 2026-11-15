# Performance review

No performance optimization has been made. No speedup is claimed.

The existing `scripts/remediation_benchmark.py` has synthetic timing and structural comparisons. Its compact-status baseline times JSON serialization while its changed side times object projection. Those timings are not comparable end-to-end paths. Hash timings use three samples per side without alternation and ignore returned validity. Treat historical timing ratios as inconclusive. Structural byte counts and hash-call counts have narrower meanings.

The baseline full Python suite completed 232 tests in 71.325 seconds under coverage. The Node runner reported 49 tests in 13.435 seconds. These are validation durations, not product performance measurements. Concurrent review and shared-host activity prevent interpreting them as a controlled performance baseline.

A source-based performance/resource review remains in progress. Any new measurement must validate outputs and state fixture, work count, samples, limits and observation scope.
