# Operations

## Run maintenance

Keep run directories inside configured paths.runs. The extension and runtime reject unsafe relative paths, symlinked directories, mismatched run IDs, stale locators, and selected runs outside the configured boundary. Resume is explicit when discovery is ambiguous or a selected run stops.

## Installation recovery

Project installation creates a backup manifest before applying changes. If application fails, the installer reverses applied changes and removes a newly created venv. Restore checks backup identity, project root, installed hashes, modes, and current file state; edited files block restore.

## Release checks

scripts/package_release.py --check compares MANIFEST.sha256 with hashes of reviewed source files. A release build excludes runtime/private files, rejects symlinks, enforces skill/agent counts from release.json, writes deterministic ZIP metadata, tests CRC/content, and publishes archive and sidecar atomically.

The release script does not upload or publish externally. Existing ZIPs and checksum files under dist/ are repository artifacts; this review did not rebuild them.

## Evidence discipline

Existing validation and remediation pages distinguish source claims, synthetic checks, and deferred user acceptance. Preserve that distinction when adding operational records. Do not expose the dashboard beyond the documented trusted-LAN boundary or treat a synthetic benchmark as field performance.

Sources: scripts/install.py:387-529, scripts/package_release.py:34-193, scripts/remediation_benchmark.py:204-212, docs/DISTRIBUTION.md, docs/MCP.md, docs/VALIDATION.md.
