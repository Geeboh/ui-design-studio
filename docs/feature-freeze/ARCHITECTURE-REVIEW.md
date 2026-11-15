# Architecture review

## Entry points and data flow

| Entry point | Boundary | State and lifetime |
| --- | --- | --- |
| `tools/ui-design` and installed `ui-design` | Explicit CLI arguments and confined project paths | Engine dossiers, theme registry, packaging and cleanup |
| `ui-design-mcp` | One fixed repository and typed stdio requests | Owns a connection dashboard; closes only owned listeners |
| OMP progress extension | Main-session events, verified child identity and generation | Owns one dashboard child; preserves Pi Tasks ownership |
| Connection HTTP dashboard | Bearer capability, origin/host checks and private discovery | Lists runs; explicit open selects a separate run listener |
| Run HTTP dashboard | Bearer capability, digest-bound approvals and sandboxed previews | File-backed evidence, retained artwork and owned cleanup |
| Project/global installers | Managed-file ownership, conflict checks and bounded destinations | Installation records, reversible backups and isolated runtime |

The authored `.omp` tree is the single engine/asset source. Hatchling maps it into the wheel payload. `runtime.py` loads either that payload or the checkout source. No second maintained engine copy exists.

Runs use JSON/Markdown dossiers. Content hashes bind approvals and evidence. Atomic record writes and advisory/exclusive locks protect selected operations. The registry is metadata, not application deployment. No database, application migration service, container deployment, or tracked CI system exists.

## Corrections and compatibility

The shared `check_run` validator now enforces the full-release scope boundary for CLI, MCP, dashboard finalization, and registration. Scoped completion remains a separate successful outcome. Source dependency edges now invalidate dependent work, including older manifests without those edges.

Worker instruction paths resolve against an explicit repository when MCP already knows it. The engine compares confined physical paths rather than inconsistent relative strings. The Python helper adds only an optional keyword-only `repo`; existing CLI/direct callers retain discovery.

Retained content versions and derived artwork IDs are validated without changing their format. Browser state uses one poll timer, current controller identity, and an explicit stopped state. Extension discovery distinguishes existing peers from new runs and retains failed-open retry eligibility.

Large modules were not split solely by line count. Their existing boundaries and tests supported targeted fixes. No rewrite, compatibility alias, second registry, or speculative framework was introduced.

