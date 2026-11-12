# Fieldstone specimen

An original, lightweight light theme demonstrating UI Theme Module v1. Warm neutral surfaces, restrained green accents, clear borders, a system font stack and small original SVG icons support a practical interface.

This is a design sample with illustrative content, not an assessment or implementation of TADA. It has one light palette. Dark mode, real application integration and complete application accessibility/performance verification are pending until implemented and tested in a host project.

## Preview

Open `preview.html` beside its CSS/SVG files, or serve the directory through an existing local development server. External SVG symbols may require HTTP in some browser configurations; the self-contained package showcase avoids that dependency.

## Integrate

Load `tokens.css` then `theme.css`. Set `data-ui-theme="fieldstone"` on a stable root. Use semantic `--ui-*` variables in real host components. Adapt the demonstration `.ui-*` classes to the host's reviewed primitives; retain its business logic and accessibility behaviour. Refer to `references/theme-module.md` in the designer skill for the registry/selector contract.

## Customize

Edit `tokens.json`, run `tools/ui-design build-theme themes/<id>`, and run `check-theme`. Edit scoped component styles as needed. Check every real text/background pair and interactive state; the token validator checks only declared pairs. Name/version/author/license in `theme.json` must describe the actual resulting module.

## Restore

Retain the previous theme directory/version and registry backup. Restore the previous default through the host adapter, then verify reload, persisted user selection and state preservation. The designer's installer rollback removes the workflow package only; application design changes use the project's Git/release rollback procedure.

## Asset provenance

CSS and eight SVG symbols were authored for this package and are provided under the included MIT license. No remote font, image, JavaScript library or telemetry is used. Functional data images, maps and imagery in an application have their own data and license requirements.
