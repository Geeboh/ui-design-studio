# Security

## Trust boundaries

The repository crosses boundaries between an OMP host, project files, Python runtime, local HTTP, browser dashboard, MCP clients, and optional model providers. Project paths, run records, dashboard connections, and model-routing state are untrusted inputs until validated.

## Controls established by source

- Installers reject unsafe relative paths, symlinked managed paths, unmanaged conflicts, and modified owned files.
- Project installation uses atomic writes, backups, pre-write rechecks, and rollback.
- Global MCP installation uses an ownership marker and refuses unrelated executables or symlinked environment paths.
- Release packaging excludes runtime/private state and rejects symlinks and unsafe destinations.
- The progress extension uses bearer authentication, identity probing, local connection checks, bounded response sizes, timeouts, diagnostic redaction, and session/project/run matching.
- Dashboard pages declare strict CSP and no-referrer behavior; the landing page uses a token fragment and removes private connection data on page lifecycle transitions.
- Theme guidance forbids remote assets and validates paths, sizes, contrast, reduced motion, and forced colors.

A trusted-LAN dashboard is not an Internet-facing security boundary. A repository review cannot establish the security of a particular host, browser, provider, project, or deployment. Do not copy tokens, credentials, or runtime private data into documentation.

Sources: scripts/install.py, scripts/install_mcp.py, scripts/package_release.py, .omp/extensions/ui-design-progress.ts:521-622, .omp/skills/ui-design-studio/dashboard/, references/theme-module.md, docs/MCP.md, docs/feature-freeze/SECURITY-REVIEW.md.
