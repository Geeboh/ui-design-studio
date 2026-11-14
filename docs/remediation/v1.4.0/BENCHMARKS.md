# v1.4.0 remediation benchmarks

Status: PASS for the offline synthetic benchmark. No real-provider or invented historical measurement is accepted.

## Method

`scripts/remediation_benchmark.py` uses one fixed synthetic fixture, Python 3.12.3, the current engine and five samples for timing fields. Baseline is the same-revision legacy/full-preload proxy. Changed is the bounded compact projection, validation cache and lazy hot-path proxy. Values are local lab measurements, not field performance or token billing.

## Results


| Workload | Baseline | Changed | Samples | Variance | Caveat |
| --- | ---: | ---: | ---: | ---: | --- |
| compact status, 0/100/1000 items | 394/37298/369401 bytes | 388/394/397 bytes | 1 byte-size fixture; 5 timing samples | changed range 9 bytes | synthetic JSON; compact excludes detail bodies |
| validation hash reuse | 6 SHA calls | 2 SHA calls | 3 validation samples | local timing in `benchmarks.json` | same report and bound input; cache is per validation cycle |
| phase context | 3929 words | 2900 words | 1 static fixture | byte/word count, no tokenizer | changed value is router plus workflow proxy; baseline is not the unmodified archive |
| scoped workflow | 4 required cases | 3 required cases | 1 coverage fixture | deterministic count | applicable-case fixture has one explained exclusion |

## Deterministic workload suite

The machine-readable benchmark includes six fixed offline workload shapes:
tiny component fix, new page in an established system, reference-inspired flow,
dense offline appliance screen, full multi-page redesign, and resume after a
shared token change. Each records fixed project requirements, expected
acceptance properties, and simulated baseline/changed orchestration steps.
These are shape simulations, not live provider, user, timing, or token-billing
measurements.

Machine-readable results: `docs/remediation/v1.4.0/benchmarks.json`.

No percentage target is treated as an acceptance gate unless reproducibly measured.
