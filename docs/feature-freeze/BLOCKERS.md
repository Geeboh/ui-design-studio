# Blockers and remaining acceptance

No confirmed code finding remains unresolved in the audited remediation branch. Automated engineering gates pass. The following limits prevent an unconditional, all-platform release claim.

| Limit | Impact | Required action |
| --- | --- | --- |
| Native Windows/macOS unavailable | POSIX and simulated platform tests do not certify native installation, filesystem or lifecycle behavior | Run the documented install, update, restore and full applicable suite on each supported native platform |
| Human and physical-device acceptance absent | Automated browser checks cannot approve target-application usability or device integration | Complete project-specific UAT and device checks before claiming them |
| Native BFCache and other engines unverified | Chromium persisted-event simulation exercises handlers but not browser cache admission | Exercise real back/forward restoration and supported non-Chromium browsers |
| Original user edits not integrated | Their combined behavior is outside this branch's evidence | Review and test the combination without overwriting the original checkout |
| Alternate-family review override unavailable | Host rejected per-call model selection | Available-model fresh-context reviews were used; do not advertise cross-family certification |

## Operational recovery

Archive and checksum publication cannot be crash-atomic across two filesystem replacements. Normal checksum replacement failures restore the prior archive; tests cover that path. If rollback itself fails, the builder retains its backup for recovery. After a crash, do not distribute either file until the checksum matches. Rebuild from the reviewed source into a safe destination, or restore the retained archive backup with its matching prior checksum. Preserve recovery files until verification succeeds.

Dashboard capabilities grant access to their run. Use only trusted hosts/networks; plain LAN HTTP does not provide transport confidentiality. Do not publish capability URLs, private runtime records or credentials.

No credentials, deployment access or irreversible action is needed to review this local delivery. Merge, publication and deployment remain deliberately unperformed, not passing acceptance checks.
