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

## Current independent revalidation

Original outputs, exact target provenance, dispositions and limitations are embedded in [REVIEW-EVIDENCE.json](REVIEW-EVIDENCE.json). Earlier sections are inherited narratives, not substitutes for current review.

| Reviewer | Current scope | Disposition |
| --- | --- | --- |
| AdapterAudit | Complete inherited MCP, dashboard and lifecycle source | FF-023–025 reproduced and fixed |
| DistributionAudit | Complete inherited installation and distribution slice | FF-027 reproduced and fixed |
| WorkflowAudit | Guides, assets, contracts and audit evidence | FF-028–029 corrected with original retained outputs |
| EngineAuditCorrected | Correct inherited engine/server checkout | No confirmed additional defect; initial wrong-target output excluded |
| ReauditEngine | Whole current engine/run server and tests | FF-032–036 reproduced and fixed; scaffold hypothesis disproved |
| ReviewRepoBoundary | Explicit repository propagation and empty artifacts | Accepted |
| ReviewPollAndPrivacy | Concurrent probes and template exception | FF-031 reproduced and fixed |
| ReviewNewRegressions | Current regression assertions and browser coverage | Three specific test gaps closed |
| ReviewFinalRaceVerifier | Final listener race, QR buffer and nested browser form | Accepted |
| ReviewAuditTrail | Interim report, gate and preservation evidence | Final reconciliation required; recovery uncertainty retained |
| ReviewEngineAcceptance | Registration, report binding and reviewer identity | Accepted |
| ReviewEngineIntegrity | CSS resources and resume consumers | FF-037–040 reproduced and fixed |
| ReviewFinalResumePaths | Recorded input inventory and dependent categories | Accepted |
| ReviewFinalCssBoundary | Final lexical/resource correction | FF-041–043 reproduced in validator and Chromium, then corrected and regression-verified by parent |

ReviewEngineIntegrity exposed model identity `openai-codex/gpt-6.1-sol`; other current reviewer model identities are not inferred. Per-call alternate-family overrides were unavailable. No cross-family certification is claimed. Parent execution, not static agreement, establishes the reported test outcomes.

The last CSS reviewer reported three concrete survivors rather than approval. The parent reproduced each, applied shared lexical/source-boundary corrections and ran the affected and full gates. Their dispositions and original rejection remain in the evidence; a later zero-finding independent CSS verdict is not claimed.
