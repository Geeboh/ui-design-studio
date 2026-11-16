# Repository inspection inventory

All 116 baseline tracked paths have inspection dispositions in [inspection.tsv](inspection.tsv). Four independent source-review slices and the parent-owned workflow slice covered the repository. A fresh whole-source UI review replaced an initial patch-oriented review.

| Slice | Assigned paths | Status |
| --- | --- | --- |
| Workflow | `studio.py`, `tests/test_studio.py` | Reviewed; shared acceptance and filesystem fixes verified |
| HTTP and MCP | `design_server.py`, all `src/ui_design_studio` code, server and MCP tests | Reviewed; integrity, cleanup, path and probe fixes verified |
| Browser and OMP | Dashboard HTML/CSS/JS, progress extension, extension tests | Reviewed; 52 Node tests, four Chromium regressions and native OMP smoke passed |
| Distribution | Installer, build hooks, scripts, metadata, manifest and package tests | Reviewed; 13 builder and five wheel/sdist/package tests passed |
| Guides and assets | Remaining Markdown, JSON, specimen assets, examples, prompts, screenshots | Reviewed; routing/provenance/method corrections recorded |

Historical ZIPs and screenshots are generated release evidence. Audit their integration and integrity without rewriting historical release content. Runtime caches, Git internals, third-party installed packages, and private active-dashboard state are excluded from source review. Dependency integration remains in scope.

New regression files and freeze records are reviewed with their associated remediation batches. `REVIEWS.md` records independent review scope and rejected hypotheses. No source component is excluded because it was unchanged.

There is no database, application migration framework, container deployment, or tracked CI configuration. State uses confined JSON/Markdown dossiers, registry files, retained artwork, private runtime locators, and installation/routing journals. Installed third-party dependencies are audited as integration inputs rather than rewritten.

## Current tracked membership

The current source set has 149 tracked or authored paths, excluding user-provided `AGENTS.md`.
The original 116-path ledger omitted 17 audit records, three remediation regression modules, and four v1.4.2 release entries.
Those 24 paths and the five current feature-freeze reports now have explicit entries in [inspection.tsv](inspection.tsv).
This corrects FF-022 without changing the earlier baseline count.
Current review partitions are engine/run server, adapter/landing server, distribution/installers, and workflow/documentation.
The parent additionally read the complete dashboard and extension code and every new regression module.
Fresh reviewer coverage and gaps are recorded in [REVIEWS.md](REVIEWS.md).
