# Workflows

## Guided lifecycle

1. Assess the existing product and requirements.
2. Plan concepts, scope, risks, and coverage.
3. Design screens, states, tokens, and approval artifacts.
4. Produce implementation only after approval.
5. Review accessibility, responsive behavior, performance, and offline requirements.
6. Finalize evidence, documentation, registration, and rollback information.

The director skill loads only phase material needed for the current request. Each phase has required inputs, outputs, ownership, and gates. A run can resume from recorded state.

## Autonomous, goal, and design-only runs

/ui-yolo selects the autonomous contract. It still follows project instructions, records evidence, preserves run state, and must not fabricate verification. Prompt and run-type documents also define goal-scoped, assessment-only, design-only, and resume flows. A design-only run does not imply application implementation or live user validation.

## Dashboard lifecycle

The extension starts or borrows a dashboard connection, verifies identity, selects one run, renders progress, and stops or recovers the child process. /ui-design-dashboard start starts or reuses a connection; stop stops the owned child; a 48-hex session ID selects a discovered connection. /ui-design-progress RUN pins a run inside configured storage; auto returns to discovery.

## Theme lifecycle

Theme work is bounded: inspect the system, define semantic tokens and assets, validate contrast and budgets, obtain review evidence, then register or package the module. The checked-in example is illustrative and not a completed redesign or live audit.

Sources: .omp/skills/ui-design-studio/SKILL.md, references/workflow.md, run-records.md, multi-agent.md, prompts/, .omp/extensions/ui-design-progress.ts:1114-1228, assets/example-theme/README.md.
