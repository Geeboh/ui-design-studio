# Independent reviews

## Initial whole-repository review

- `AuditHttpMcp` reviewed the full HTTP/MCP/lifecycle slice and its tests. Six additional source-traced findings were reproduced or verified by the parent before correction.
- `AuditDistribution` reviewed installation, build, archives, metadata, and tests. Parent reproduced the ZIP secret and output-integrity findings. The inferred checkout-wheel leak was not reproduced; a real wheel omitted the synthetic secret. Explicit wheel/sdist regression now checks operation without VCS ignores.
- `AuditGuidesAssets` reviewed all assigned guides, schema, specimen assets, prompts, and documentation. Routing-role contradictions and historical commit-provenance ambiguity were corrected.
- `AuditBrowserExtension` initially reported no issue while referring to patch anchors. That was insufficient for a whole-source audit. A fresh `AuditUiWholeSource` review read unchanged source and identified selected-run, restored-polling, and return-focus defects. The parent reproduced all three, including simulated persisted page events in actual Chromium.

## Remediation review

`ReviewWorkflowFixes` found the shared full-release validator to be the correct boundary. It recommended an explicit repository argument plus instruction normalization for non-Git MCP projects. Its warning that an untracked regression file would be omitted was rejected because the ownership-aware commit draft explicitly selected and committed `tests/test_feature_freeze.py` in `5fef92d097`.

`ReviewSecurityBatch` found a remaining artwork-ID swap despite content-hash validation. The parent reproduced an approve-option ID resolving to `b.html` while the signed request still named `a.html`, added a failing metadata-ID regression, and bound IDs to the existing derivation. That regression passed after correction in `1e137f6658`.

`ReviewEvidenceTrail`, model `openai-codex/gpt-6-luna`, found stale interim statuses, already-completed pytest evidence, imprecise initial timestamps, and historical chronology. Historical corrections and an appended timestamp correction preserve the original accounts. `ReviewFinalTrail`, using the same reviewer model in fresh context, confirmed protected user changes and truthful hypothesis rejection. Its remaining flags were stale final reports; those records are reconciled in this batch.

`ReviewFinalRuntime` reported no remaining concrete issue. `ReviewBrowserFixes` accepted controller identity, polling cancellation and focus restoration while retaining the native-BFCache verification limit. `ReviewExtensionFixes` withdrew its proposed removal of new-run auto-follow because the existing behavioral test requires it. The parent preserved that contract and repaired retry tracking after failed opens.

`ReviewFinalPackage`, model `openai-codex/gpt-6.1-sol`, accepted the final five-file packaging batch with no remaining finding. Earlier review caught the private-ancestor template exception and publication ordering; both received reproduced regressions and corrections.

Independent reviewers did not implement the batches they approved. Review outcomes are not substituted for execution evidence. A requested alternate-family model override was rejected because host per-call model selection is disabled; no settings were changed. Reviews used available models and fresh contexts. Final central execution results are in [TEST-MATRIX.md](TEST-MATRIX.md).
