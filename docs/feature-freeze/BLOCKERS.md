# Blockers and remaining work

## External limitations

- Native Windows and macOS are unavailable on this Linux workstation. Platform simulation does not certify native behavior.
- Human acceptance, physical-device testing, and deployment approval are not performed by automation.
- The original checkout contains independent user edits. This branch deliberately does not incorporate them; combining both requires integration review.

## Active engineering gaps

- Independent inspection coverage is not yet reconciled.
- Confirmed workflow defects require regression-first fixes.
- Pytest-only contracts and final release checks remain outstanding.
- The source manifest must be regenerated after final authored changes. Historical release archives remain unchanged.
- Pi Tasks rejected broad multi-step plans repeatedly. T1 tracks original acceptance criteria; its single accepted baseline step does not imply overall completion.

No credential or external approval currently blocks safe local remediation.
