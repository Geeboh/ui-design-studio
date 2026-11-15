# Security review

## Threat model

The dashboard uses bearer-capability URLs for a small trusted local team. URL holders can inspect artwork and submit guided approvals. Plain HTTP does not protect credentials or content against network observers. This freeze does not authorize public exposure or change that transport assumption.

Review covered authentication, origin/host checks, filesystem confinement, symlinks and special files, subprocess ownership, serialization, approval identity/freshness, private package inputs, installation rollback, and dependency integration.

## Confirmed protections corrected

- Bounded work cannot receive full-theme release acceptance.
- JSON and hash readers reject FIFOs and other nonregular descriptors without blocking.
- Retained manifest content and derived IDs remain bound to the displayed version and approval inputs.
- MCP worker paths use the connection's fixed repository and preserve explicit empty action lists.
- Status tools no longer advertise read-only behavior while retaining artwork.
- Package privacy does not depend on the checkout's Gitignore. Public environment examples cannot reopen private ancestors.
- Release output preflight and staged checksum publication protect existing artifact pairs on reported failures.

The first inferred checkout-wheel leak was disproved by an actual build. Independent review then established a different nested-example leak introduced by a broad exception. Its failing regression led to explicit safe example inclusion in the build hook.

## Scanners and limits

The installed-environment `pip-audit` run reported no known vulnerabilities. Trivy secret, misconfiguration, and license scans returned no findings for the worktree. These are point-in-time tool results, not proof of completeness or license certification. Dependency resolution differs between Python 3.10 and 3.13; no new runtime dependency was introduced.

Native Windows/macOS behavior, physical-device access, human acceptance, and public-internet security remain unverified. Capability URLs and private runtime records are not committed as audit evidence.

