# Repository inspection inventory

Baseline contains 116 tracked files. Four independent review slices and a parent-owned workflow slice cover the repository. Individual paths and review dispositions will be reconciled when reviewers return.

| Slice | Assigned paths | Status |
| --- | --- | --- |
| Workflow | `studio.py`, `tests/test_studio.py` | Parent source inspection complete, remediations pending |
| HTTP and MCP | `design_server.py`, all `src/ui_design_studio` code, server and MCP tests | Independent review running |
| Browser and OMP | Dashboard HTML/CSS/JS, progress extension, extension tests | Independent review running |
| Distribution | Installer, build hooks, scripts, metadata, manifest and package tests | Independent review running |
| Guides and assets | All remaining Markdown, JSON, specimen assets, examples, prompts, screenshots | Independent review running |

Historical ZIPs and screenshots are generated release evidence. Audit their integration and integrity without rewriting historical release content. Runtime caches, Git internals, third-party installed packages, and private active-dashboard state are excluded from source review. Dependency integration remains in scope.
