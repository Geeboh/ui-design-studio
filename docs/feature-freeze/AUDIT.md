# Technical audit

The package supplies local OMP skills, a Python workflow engine, authenticated HTTP dashboards, and a stdio MCP adapter. The expected workload is a small private design team. No public-internet hardening or native compatibility certification is inferred.

Confirmed workflow reproductions against baseline:

- A fully populated component-scoped dossier with a fresh finalization digest passes `check_run` and `register_theme`. This violates the documented separation between scoped completion and full-theme release.
- A surface declaring ready, error, and recovery can exclude every recovery case while retaining one error case. The validator tests whether any critical state remains, rather than every declared critical state.
- Passing an empty `allowed_actions` list to `worker_packet` returns write and evidence-publication actions. The default expression conflates absence with an explicitly empty list.

The structured register owns severity, fixes, regression evidence, and final dispositions. Independent review may add confirmed findings.
