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

Current point-in-time scanner and dependency responses are retained in [SECURITY-EVIDENCE.json](SECURITY-EVIDENCE.json), alongside 77 authored source hashes. Trivy batch `9c9ef4d6-5ff9-4040-bb22-e9599a20b502` returned an empty findings list for vulnerability, secret, misconfiguration and license scans. The tool did not return scanner version or scanned-file count. No completeness or license certification is inferred.

Python 3.10 and 3.12 environments contained 51 and 72 installed distributions respectively. Their final audits reported no known vulnerabilities. The Python 3.10 environment was inspected using the Python 3.12 auditor's `--path`; installing an auditor inside the minimum-version environment unnecessarily selected vulnerable verification-only `filelock` 4.1.0. Its 17 advisory IDs and the earlier 42 Pillow advisory IDs remain retained. Both avoidable dependencies were removed, not ignored. The unpublished local package can be skipped by the advisory database and is covered by source review rather than a fabricated advisory result.

Fresh source review and regressions also cover explicit repository provenance, cross-project registration, required report freshness, whitespace self-review, quoted CSS image resources and resume consumers. The actual Chromium variable-resource probe was intercepted locally. No request was sent to the external example host. The theme validator remains a conservative packaging check, not a sandbox for arbitrary hostile CSS.

Native Windows/macOS behavior, physical-device access, human acceptance and public-internet security remain unverified. Capability URLs and private runtime records are not committed as audit evidence. The original checkout's independent input-resolution changes are excluded from this branch and its security verdict.
