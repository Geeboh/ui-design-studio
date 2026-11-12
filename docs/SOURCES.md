# Primary sources and compatibility notes

**UI Design Studio 1.1.0 · Reviewed 12 November 2026**

OMP sources refer to upstream `main`. Runtime capabilities and command syntax may differ in an installed release, so the director inspects the live version/tool surface before using optional features. The external sources below explain their respective standards or tools. Studio's workflow, decision weights, worker limit, theme-module packaging and default byte budgets are package design choices.

## Oh My Pi

| Topic | Primary source |
| --- | --- |
| Skill discovery and invocation | [Skills](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md) |
| Named specialist definitions and model precedence | [Task agent discovery](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md) |
| Project instructions and worker context inheritance | [Context files](https://github.com/can1357/oh-my-pi/blob/main/docs/context-files.md) |
| Task batching, model choices and concurrency | [Task tool](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md) |
| Slash commands, file commands and discovery refresh | [Slash-command internals](https://github.com/can1357/oh-my-pi/blob/main/docs/slash-command-internals.md) |
| Configuration resolution | [Configuration usage](https://github.com/can1357/oh-my-pi/blob/main/docs/config-usage.md) |
| Thinking/model roles and other settings | [Settings](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md) |
| Launch flags including `--goal` | [CLI reference](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md) |
| Goal lifecycle and continuation semantics | [RPC goal payload](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md#goal-payload) |
| Verified goal completion instructions | [Goal-mode prompt source](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/prompts/goals/goal-mode-active.md) |
| Vibe director and bundled worker tiers | [Vibe mode](https://github.com/can1357/oh-my-pi/blob/main/docs/vibe-mode.md) |
| Browser capabilities | [Browser tool](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/browser.md) |

The package uses native project-local skill/agent/command paths. It does not promise one universal minimum OMP version because capabilities are discovered. It does not require `/vibe`, a particular model alias, or a third-party MCP integration. A routing plan must be checked against actual worker execution; installing a skill is not evidence that a model assignment has taken effect.

## Optional Tersio pstack

- [Tersio package documentation](https://www.npmjs.com/package/@krtclcdy/tersio)
- [Tersio source repository](https://github.com/KurutoDenzeru/tersio)

The pstack guidance concerns the Tersio extension when it is already part of the project. It is an optional rigor layer, not a built-in Studio dependency or a universal OMP command. Follow the installed extension's actual version and documentation. Studio owns the design workflow; avoid duplicate orchestration when combining them.

## Accessibility and interaction

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [Non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- [AA target-size rule and exceptions](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [Reflow and two-dimensional exceptions](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
- [Modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [Keyboard interaction](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/)
- [Evaluation tool selection and limits](https://www.w3.org/WAI/test-evaluate/tools/)

WCAG 2.2 AA is the starting target for web interfaces. The package's preferred 44 CSS pixel touch target is a project policy; it must not be confused with the AA minimum target-size criterion and its exceptions. Automated checks alone do not establish conformance. A native application also needs relevant platform accessibility checks.

## Design tokens and theme format

- [DTCG Format Module 2025.10](https://www.designtokens.org/TR/2025.10/format/)
- [DTCG Colour Module 2025.10](https://www.designtokens.org/TR/2025.10/color/)

DTCG 2025.10 is a Final Community Group Report, not a W3C Standard. The included helper implements a documented subset and rejects unsupported features. UI Theme Module v1 and its registry/adapter contract are Studio's separate packaging convention; DTCG token compatibility does not make every application load the same theme archive automatically.

## Web performance

- [Web Vitals](https://web.dev/articles/vitals)
- [Core Web Vitals thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds)
- [Lab and field data differences](https://web.dev/articles/lab-and-field-data-differences)

The quality reference distinguishes lab observations, field measurements and declared byte budgets. A small theme archive does not prove fast interaction or Core Web Vitals compliance. Record device, network, server, cache and test conditions; keep application data costs separate from the theme's runtime assets.

## Verification limits

The release's [Validation record](VALIDATION.md) describes checks actually run on the package. Upstream documentation is not test evidence for your application. The director must establish each project's inventory, renderer, integration, access, accessibility and performance results during its own run and state any remaining unknowns.
