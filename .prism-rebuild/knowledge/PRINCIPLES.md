# Original principles for PRISM Studio

Use this page as a small routing aid. [rules.json](rules.json) contains 40 original conditional rules; [SOURCES](SOURCES.md) records their provenance and coverage. These rules synthesize the supplied resources for this project. They are not copied chapters or a universal design doctrine.

## Select the rules needed for the task

| Task | Start with |
|---|---|
| Assess a workflow or screen | PR-001, PR-005 through PR-010, PR-039 |
| Check accessibility | PR-007, PR-008, PR-010 through PR-016 |
| Review or revise an artifact | PR-017 through PR-024, PR-039 |
| Schedule paid design work | PR-024 through PR-030 |
| Implement the shared engine/API | PR-018, PR-019, PR-023, PR-026, PR-027, PR-031, PR-032, PR-040 |
| Improve dashboard performance | PR-030, PR-033 through PR-037 |
| Manage context and provenance | PR-002 through PR-005, PR-039 |
| Install or change a theme | PR-009, PR-038, PR-040 |

## The governing ideas

Begin with the user's task and actual constraints. A useful design lets the person understand the current state, act deliberately, see what happened and recover. Minimalism, density, progressive disclosure, defaults and automation serve that task; none should conceal important consequences.

Preserve exact identities where trust depends on them: artifacts, captures, annotations, component versions, approvals, requests and cost attempts. Small authoritative transactions protect approvals and money; derived read views keep presentation responsive. A newer run timestamp does not necessarily invalidate a design decision, while a changed dependency can.

Treat a design budget as a financial boundary with known currency and explicit uncertainty. Reserve before controlled paid work, settle from evidence, and reconcile ambiguous outcomes. Token efficiency helps but does not establish monetary enforcement. Keep implementation spend separate from design spend by default.

Make local changes local. Focused revisions pin their base; decomposition uses stable components and a dependency graph; partial acceptance preserves independent progress. Recheck the assembled result because valid parts can still compose badly.

Use actual artifacts and observable checks. A polished placeholder, schema validation or agent statement cannot replace the claimed evidence. Human research is deferred, so document the remaining uncertainty. Automated interactions and accessibility checks remain necessary for the applicable web gates.

Keep context small enough to be useful. Route the active skill, exact task packet and selected references. Do not inject every book, every cognitive bias, or an entire run transcript into each worker. Missing source detail is a gap to resolve, not permission to invent a finding.

## Authority and conflicts

The `authority` field means:

- `project-policy`: a chosen product or operating constraint; change it explicitly.
- `standard`: a scoped normative requirement or primary platform contract; use the applicable version and exceptions.
- `engineering-proposal`: an implementable design derived from project risks; validate it against the actual system.
- `source-informed-heuristic`: useful judgment guidance, requiring context and outcome checks.

`sourceIds` and `sourceLocators` explain provenance, not automatic equivalence. A rule may add project-specific enforcement that a source only motivates. Where a primary standard corrects a secondary summary, retain the correction. Where preferences conflict, state the tradeoff and choose based on the goal; do not invent a scientific certainty.

Read [RETIRED-GUIDANCE](RETIRED-GUIDANCE.md) only when handling the affected legacy recipe or resolving a conflict. A source's age alone is not grounds to discard it; a known unsafe or obsolete prescription is grounds to prevent literal reuse.
