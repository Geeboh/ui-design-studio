# Implementation playbook

## Working method

Use an incremental replacement with explicit compatibility adapters. Preserve the baseline branch and archived legacy records. Introduce the shared domain core first; move each adapter to it; retire old duplicated behavior only after parity and migration checks pass. A full directory deletion followed by speculative recreation would discard useful controls and make regression evidence harder to interpret.

Each work item needs an objective, requirement IDs, owned paths, input revisions, dependencies, allowed operations, acceptance cases and a review owner. Use [the work-order template](../templates/WORK-ORDER.md). Small changes do not require a new architecture ceremony. Changes to invariants, schema or money require explicit scenario review.

## Parallel ownership

| Stream | Owns | Must coordinate with |
| --- | --- | --- |
| Domain/state | Commands, invariants, transaction boundaries, schema | Migration, API adapters, budget |
| Migration/installation | Legacy import, backup, restore, path ownership | Domain and packaging |
| Dashboard | Interaction state, rendering, accessible controls | Published API contract and design tokens |
| Governance | Approvals, components, revisions, budget/provider operations | Domain owner |
| Verification/docs | Test fixtures, scenarios, executable guides, review | Every stream's public behavior |

One integration owner controls shared contracts and release metadata. Workers may propose a contract change but must not independently invent incompatible versions. Review contracts before distributing implementation tasks. A bounded work item can be completed sequentially if the host has no subagent capability.

## Discovery is a concrete task

M0 happens in the prepared worktree, before implementation. Inspect instructions, source entry points, `.omp` discovery surfaces, schemas, tests, build configuration, install scripts, theme behavior, package manifests and current docs. Record commands and facts in `.prism-state/discovery.md`. Reproduce baseline findings where they still apply. Identify new changes and resolved issues at the selected commit.

Do not call this discovery `--prewalk`: current upstream OMP uses that name for a one-shot model handoff. A handoff does not establish codebase understanding. Use focused searches and a persistent discovery map instead.

## Per-task loop

1. Read the assigned requirements and the smallest applicable references.
2. Confirm dependency versions and exclusive ownership.
3. Write or select the meaningful failing regression/acceptance check.
4. Implement the smallest coherent behavior behind the shared interfaces.
5. Run affected checks and inspect the actual result.
6. Obtain a review of the diff, contract and evidence; fix concrete findings.
7. Integrate, rerun affected cross-boundary checks and commit owned paths.
8. Record status, evidence locations and the next dependency.

Keep UI behavior and the corresponding contract test in the same work item where possible. Do not spend tokens reproducing complete tool logs in worker messages: send a short result plus the private full evidence path. Never compress away an error, path, identity, version, amount or failed assertion.

## Candidate discipline

Development tests may run on a dirty candidate if the plan explicitly allows it; the fingerprint records its bytes. Release verification requires a clean committed candidate. Keep generated evidence under ignored `.prism-state/`. Build outputs should use declared ignored locations; a test that changes tracked source causes the runner to invalidate its result.

A packaging step must identify the exact source commit and archive digests. Changing release metadata afterward creates a new candidate that needs the affected checks again. Test installation from the produced ZIP, sdist and wheel in clean locations; all documented fixtures and resources must be present or the instructions must explicitly require a source checkout.

## Existing strengths to preserve

Retain explicit project selection, authenticated dashboard access, capability-token handling, CSP and escaping protections, path containment, owned-resource cleanup, transactional installation/restore, actual model reporting, application state across theme changes and the portable MCP engine. Refactoring should improve these boundaries rather than accidentally remove them.

## Completion and blocked work

The director owns a requirement-level completion ledger, not an impressionistic percentage. A task can be pending, active, blocked, implemented-unverified, verified, or inapplicable with a recorded scope reason. An unavailable required host/browser check is blocked, not inapplicable. A native integration check for a web-only target may be inapplicable. Human research is deferred by policy.

For a genuine blocker, record the failed operation, observed error, affected acceptance IDs, attempted safe alternatives, exact user/environment action needed and the independent work already finished. Avoid retry loops with unchanged inputs. Preserve an immediately resumable next action.
