# Contributing

## Preserve source boundaries

Read project instructions, requirements, current architecture, and the relevant phase/reference contract before changing workflow behavior. Keep phase ownership and independent review boundaries intact.

## Preserve runtime safety

Changes to installers, run paths, dashboard connections, model routing, theme packaging, or release output must retain validation, error handling, rollback, and redaction behavior. Reuse existing configuration fields and helpers.

## Preserve evidence

Do not convert inferred behavior, synthetic benchmarks, screenshots, or historical reports into live verification claims. Record source paths, hashes, commands, environment, and unresolved limits. Runtime evidence and run records are part of the workflow contract.

## Documentation changes

Use docs/documenter/ for generated Documenter pages. Publish through the Documenter state helper so ownership and stale-page protection remain active. Preserve existing human-authored pages under docs/.

Before delivery, rescan, record current reviews and claims, run normal and strict checks, and report binary gaps, exclusions, unresolved unknowns, and skipped runtime verification.

Sources: Documenter references, AGENTS.md, .omp/skills/ui-design-studio/references/multi-agent.md, quality-gates.md, docs/.
