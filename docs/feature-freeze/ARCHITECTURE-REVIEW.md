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

## Current revalidation

The current audit preserves the architecture and existing CLI interfaces.
Inherited runtime fixes were fast-forwarded into the isolated branch rather than reimplemented.
The current browser review read all dashboard HTML, CSS, JavaScript, and the complete TypeScript extension.
The additional form-submission test drives existing controls and checks the durable digest-bound user decision after reload.
FF-023 propagates the already-known repository through optional backend parameters rather than rediscovering it from ancestors.
FF-024 snapshots selected-run and handle state under the mutation lock, probes outside it, and revalidates ownership before responding.
Single-flight caching was rejected because cache expiry, invalidation, and shutdown state were unnecessary for this correctness fix.
No second state store, compatibility layer, new dependency, or runtime abstraction is introduced.

The acceptance batch binds the required assessment report into the existing review digest and confines registration to its explicit repository. Identity comparison trims whitespace without rewriting evidence. The dashboard uses the same independence rule.

CSS validation now emits normalized resource references once, and the caller checks their declared runtime membership. It preserves local static image-set candidates without adding a CSS-parser dependency. Direct resource-variable substitution is deliberately outside the existing conservative subset.

Resume dependencies keep one stored hash and all direct consumers per physical path. Graph edges point from consumers to their inputs. Old records missing complete membership remain readable but cannot claim current acceptance; checking returns conservative BLOCKED without changing recorded hashes. No migration side effect occurs during inspection.

The final lexical correction rejects malformed strings before skipping nonfetching text, and recognizes comments without interpreting delimiters inside strings. Resource classification rejects surrounding URL whitespace to avoid disagreement with browser URL parsing. Resume inventory uses the same recorded path fields as acceptance; a graph cannot invalidate an input the snapshot omitted.
