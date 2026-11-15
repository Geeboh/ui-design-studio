# Security review

## Threat model

The dashboard uses bearer-capability URLs on trusted local networks. URL holders may inspect retained artwork and submit guided approvals. Plain HTTP does not protect against network observers. This freeze does not introduce public exposure or change transport assumptions.

Review includes filesystem confinement, symlinks, subprocess ownership, authentication, serialization, approval freshness, dependency vulnerabilities, and privilege boundaries. Independent server/security review is running.

Dependency baseline audit reported no known vulnerabilities for the installed environment. This is a point-in-time advisory check, not proof that dependencies are defect-free.

FF-001 bypasses release authorization semantics. FF-003 expands an emitted worker action contract. Both have concrete reproductions and remain open until regression verification.
