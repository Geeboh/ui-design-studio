# Defect register

| ID | Severity | Category | Component | Status | Related commit |
| --- | --- | --- | --- | --- | --- |
| FF-001 | High | Correctness and release safety | `studio.py` scope acceptance | Confirmed, open | Not committed |
| FF-002 | Medium | Coverage correctness | `studio.py` critical-state applicability | Confirmed, open | Not committed |
| FF-003 | Medium | Worker boundary | `studio.py` action allowlist | Confirmed, open | Not committed |

## FF-001

A component-scoped dossier passes full-theme validation and registers a default theme after all other fixture gates are populated. Root cause: `check_run` validates the scope enum but does not block full release for bounded scopes. Impact: an assessment or component task can receive unintended full-theme acceptance. Proposed fix: keep scoped completion separate and block non-full-redesign scopes in shared full-theme validation. Regression risk: callers relying on the defective PASS result receive BLOCKED. Verify through engine, CLI and registration using an otherwise complete dossier.

## FF-002

A ready/error/recovery surface with only ready/error applicable cases accepts a wholly excluded recovery state. Root cause: the critical-state check uses an existential test across all critical states. Impact: declared failure/recovery coverage disappears. Proposed fix: require at least one applicable viewport for each declared critical state. Regression risk: previously accepted incomplete applicability records require correction. Verify multiple distinct critical states and a valid sparse case.

## FF-003

`worker_packet(..., allowed_actions=[])` produces `["read", "write-owned", "publish-evidence"]`. Root cause: a truthiness default replaces an explicit empty list. Impact: the emitted worker contract grants actions the caller withheld. Proposed fix: default only when the argument is None. Regression risk: none for omitted/default calls; explicit empty lists retain their meaning. Verify default, empty and read-only lists. The original checkout contains an independent uncommitted correction for this defect and remains untouched.
