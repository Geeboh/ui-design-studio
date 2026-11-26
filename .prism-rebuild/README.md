# PRISM Studio — Complete Rebuild Pack

**UI Design Studio 2.0 · Pack 1.0.0 · Prepared 26 November 2026**

PRISM turns a design proposal into clear, independently reviewable parts, then carries those decisions through reliable implementation. This pack is the complete implementation handoff for rebuilding UI Design Studio as PRISM Studio.

**Start with [START-HERE.md](START-HERE.md).** It explains preparation, the first OMP prompt, continuation, verification, and recovery. The application has not been rebuilt by downloading this pack. Its contracts, prompts and acceptance cases specify the work; its helper scripts prepare and check that work.

## What the rebuilt product must deliver

- A shared Python domain engine behind CLI, MCP and dashboard adapters.
- Scoped, version-bound approvals and incremental design/implementation slices.
- Focused revisions with annotations pinned to the exact original artifact.
- Decompose-and-re-request batches with stable components, partial approval and dependency-aware invalidation.
- A monetary **design budget**, separate from implementation spend, with reservations, actual-cost reconciliation and honest enforcement status.
- Persistent model defaults, explicit overrides and verified runtime assignments.
- Responsive, accessible review flows; clear errors, recovery and preserved context.
- Efficient snapshots, artifact previews and worker context.
- Safe migration, installation, upgrade/restore, package parity, CI and evidence-backed release readiness.

## Read by purpose

| Need | Read |
| --- | --- |
| Get moving | [Start here](START-HERE.md) |
| Give OMP the full objective | [Master rebuild prompt](prompts/MASTER-REBUILD.md) |
| Understand the product | [Product and UX](docs/PRODUCT-AND-UX.md) |
| Apply the working identity | [PRISM name and voice](docs/BRAND-AND-NAMING.md) |
| Implement the core | [Architecture](docs/ARCHITECTURE.md), [domain contracts](docs/DOMAIN-CONTRACTS.md) |
| Implement approvals, revisions and spending | [Design governance](docs/DESIGN-GOVERNANCE.md) |
| Preserve existing projects | [Migration and compatibility](docs/MIGRATION-AND-COMPATIBILITY.md) |
| Work through milestones | [Build roadmap](docs/BUILD-ROADMAP.md), [implementation playbook](docs/IMPLEMENTATION-PLAYBOOK.md) |
| Configure models and optional extensions | [Models, tools and cost](docs/MODELS-TOOLS-AND-COST.md) |
| Verify and release | [Quality and release](docs/QUALITY-AND-RELEASE.md), [security and operations](docs/SECURITY-AND-OPERATIONS.md) |
| Inspect this handoff's actual checks | [Pack validation record](validation/PACK-VALIDATION.md) |
| Apply the distilled knowledge | [Principles](knowledge/PRINCIPLES.md), [rule catalogue](knowledge/rules.json), [sources](knowledge/SOURCES.md) |
| Resolve a known defect | [Baseline findings](docs/BASELINE-FINDINGS.md) |
| Restore rebuild instructions | [Preparation and rollback](docs/INSTALLATION-AND-ROLLBACK.md) |

## What is executable today

The `tools/` scripts verify this pack, create an isolated worktree, install/restore its rebuild context, inventory prerequisites, fingerprint candidates, execute a configured test plan, summarize evidence, and produce a deterministic handoff archive. Their interfaces are documented in [tool reference](docs/TOOLS.md).

The runtime schemas, command catalogue, requirements, scenarios, and product skill blueprints are **proposed product contracts**. They must be implemented and verified before being advertised as PRISM capabilities. Only the `prism-rebuild` orchestration template is activated by the preparation tool. Existing `ui-*` skill aliases remain the compatibility surface until the corresponding rebuilt behavior exists.

## Completion claims

| Claim | What it proves |
| --- | --- |
| Pack verification PASS | This handoff's hashes, references, traceability and schema examples are consistent. |
| Selected gate pass | The selected implementation checks ran against the recorded candidate. |
| Automated release candidate ready | All required release gates, package/host checks and review evidence match the exact candidate. |
| Human validation deferred | No claim is made about participant usability studies or manually established accessibility conformance. |
| Published release | A separate, explicitly authorized publication step completed and its receipt was checked. |

The default completion target is a **verified release candidate**, with human participant testing deferred. Optional native-platform and offline profiles apply only when the target requires them. A missing required browser or host integration check remains visible and cannot be replaced by a plan or fabricated receipt.

## Provenance and scope

The reviewed baseline is `60307ef31fd6e2bad1d39620fc507b0b822e281a` (1.4.3), also returned by the public repository's remote HEAD check during pack preparation. M0 must inspect any later differences before treating old findings as current. Sources were distilled into original conditional guidance; the uploaded books and website extracts are not redistributed. See [source register](knowledge/SOURCES.md) and [retired guidance](knowledge/RETIRED-GUIDANCE.md).

The pack provides a disciplined path to completion, not a guarantee that an unknown host, model or provider will behave correctly. Unknowns have explicit discovery steps, bounded recovery and acceptance evidence.
