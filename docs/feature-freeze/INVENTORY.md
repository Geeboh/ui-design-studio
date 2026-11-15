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
