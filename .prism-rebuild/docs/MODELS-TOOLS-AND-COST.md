# Models, optional tools and cost

## Three separate concerns

1. **Rebuild implementation spend:** the coding session and workers used to build PRISM.
2. **Product design budget:** the user's explicitly configured allowance for concepts, mockups, artwork, design revisions and configured design review.
3. **Infrastructure/runtime cost:** storage, hosting or provider charges outside those categories.

Do not combine these into one misleading balance. A subscription does not prove a provider call costs zero. Unknown prices remain unknown. The rebuilt product must label advisory versus enforced design budgets accurately.

## Minimum sensible model arrangement

Choose from the models actually available in the user's OMP configuration. Names, prices, capabilities and provider prefixes are discovered in M0; this pack does not hardcode a possibly unavailable model ID.

| Role | Minimum capability | Cost policy |
| --- | --- | --- |
| Architecture/invariant owner | Strong reasoning about transactions, concurrency, migrations and security | Use for M1/M2 decisions and difficult reviews; avoid repeated whole-repo analysis. |
| Bounded implementer | Reliable repository editing, tests and tool use | Use the least costly model that passes a representative task; medium effort is a starting trial, not a guarantee. |
| Independent reviewer | Can understand the changed subsystem and detect meaningful failures | Reserve stronger review for approval, budget, migration, security and release boundaries. |
| Visual reviewer | Can inspect actual screenshots and reason about interaction/accessibility | Required when claiming visual checks; text-only analysis cannot substitute for viewed output. |
| Mechanical support | File inventory, formatting, deterministic transforms | Prefer scripts; use a small model only when judgment is needed. |

A capable current model can perform all roles sequentially if that is the available environment. Label sequential review accurately. To reduce expense, keep architectural decisions stable, use bounded work packets and escalate only a concrete unresolved problem. Do not repeatedly run the most expensive model over the whole repository.

### A small qualification trial

Before assigning bulk work to a cheaper model, give it one real bounded defect with its acceptance case. Observe whether it understands the contract, preserves unrelated behavior, produces a coherent diff and passes the meaningful check. Escalate if the result fails; record the reason. This is evidence-based routing rather than a guarantee based on a model's product name.

## Runtime discovery

Run `omp --help` and `omp models --help` before choosing exact installed syntax. Inspect available models through the host's supported listing/configuration. Record provider/model IDs, reasoning setting, visual/tool support and applicable price source. Read only relevant configuration; never print credential values. The director's active model remains explicit. The rebuilt product's preference precedence is invocation override, resumed run settings, project defaults, personal defaults, then automatic selection.

`current-model` means the actually observed session selection and relevant reasoning setting, reconciled with worker overrides. A routing plan alone is not proof of an assignment. Preserve original settings and restore temporary changes before handover or deliberate pause.

## Goal, vibe and prewalk

Use one goal as the sustained objective owner. Native task workers provide parallel execution without requiring a second director. `/vibe` is optional and must not create competing orchestration. Current upstream `--goal` starts an interactive goal session and conflicts with several other startup inputs; use the exact examples in [START-HERE](../START-HERE.md).

`--prewalk` is a one-shot model handoff at the first eligible edit/write turn; it does not perform repository discovery by itself. Keep it off unless you intentionally want that handoff and have verified the target model. M0 remains the explicit focused discovery step.

## Compression and rigor extensions

| Optional extension | Integration policy |
| --- | --- |
| Caveman | Concise machine coordination may use it. Human docs, user errors, consent, accessibility text and explanations remain clear normal language. |
| RTK-style compression | Compress repeated tool output for context; retain complete relevant evidence privately and exact commands, IDs, paths, hashes, amounts and failures. |
| Ponytail | Discover the installed package and its actual behavior first. Apply it only if it adds a useful capability without changing routing/authority unexpectedly. This pack assumes no undocumented command or flag. |
| Tersio pstack | Optional rigor/checkpoint layer when already installed. Avoid duplicating PRISM's task ledger, reviewer loops and acceptance orchestration. |
| Playwright Fast | Follow the repository's installed browser-QA workflow for affected checks and release matrices. A plan/dry run is not evidence of execution. |
| Context7, Semgrep, Trivy, FAR | Use available relevant capabilities after checking their versions and scope. Their absence is not itself a new mandatory gate; required security/quality behavior still needs suitable verification. |

Do not auto-install plugins or system packages as a side effect of this pack. Use supported existing tools first; record concrete missing prerequisites. These optional tools are not necessary to understand or execute the handoff.

## Context and concurrency defaults

The example build policy starts at three concurrent workers as an adjustable scheduling choice, with one writer for shared contracts. The engine must honor configured limits and observed resource capacity. Parallelism should reduce elapsed time without multiplying duplicate discovery, conflicting edits or unbounded spend.

A worker packet should fit the task: objective, owned paths, dependency versions, requirements, acceptance cases and only the relevant knowledge rules. Use IDs and paths to reusable references. Write compact checkpoints before compaction; reread changed dependencies on resume. Character-based token estimates must be labelled approximate.

## Sources and freshness

- [OMP CLI reference](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md), checked during preparation; installed help remains authoritative for that host.
- [OMP task tool](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md) and [task discovery](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md), verify against the installed version.
- [Tersio](https://github.com/KurutoDenzeru/tersio), optional extension reference; no installation/version is assumed.

The supplied `config/build-policy.example.json` is a **PRISM rebuild policy example**, not an OMP configuration file. Resolve it into `.prism-state/build-policy.json`; do not paste it blindly over global OMP settings.
