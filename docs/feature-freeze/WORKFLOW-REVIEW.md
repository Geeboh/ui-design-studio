# Workflow remediation design and verification

The existing dossier carries a `scope` enum and separate `scopedCompletion` record. No new state type or API is needed.

Two correction shapes were evaluated. A registration-only guard blocks the last writer but leaves CLI, MCP and dashboard full-theme checks reporting PASS for bounded work. A shared `check_run` pending reason preserves one acceptance authority for all callers. The latter was selected. `complete_scope` remains independently able to return PASS while its full-theme check remains BLOCKED.

Critical coverage uses declared state/viewport pairs. Every declared critical state must have at least one applicable viewport. An exclusion can narrow a viewport combination, not erase the entire declared failure state.

The worker action contract distinguishes None from an explicitly empty list. None receives the existing default. Empty means no actions. This does not create a sandbox or change the tool permissions of a running worker.

Before corrections, the new scope test failed for all six bounded scopes, the critical recovery-state test raised no error, and an empty worker action list expanded to write access. After corrections, all three regression methods passed. They exercise the real CLI as well as engine and registry paths. Sixty-six existing Studio tests, 72 design server tests, and 17 MCP tests passed.

Tests are in `tests/test_feature_freeze.py`. Detailed local logs are under `/tmp/ui-design-freeze-baseline/`. Fresh final runtime review reported no remaining concrete defect. The complete final Python gates passed on 3.10 and 3.13; see [TEST-MATRIX.md](TEST-MATRIX.md).
