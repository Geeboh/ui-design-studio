# UI Theme Module v1

## Contents

1. Scope and layout
2. Tokens and generated CSS
3. Manifest and validation
4. Runtime adapter and settings
5. Theme lifecycle
6. Release and portability
7. Native desktop and mobile adapters

## 1. Scope and layout

UI Theme Module v1 is the supplied web CSS/SVG adapter's versioned packaging convention. It standardizes web output across projects; it is not a universal plugin installer or a W3C standard. The designer's assessment, concept, mockup and review workflow also applies to desktop/mobile projects, but their native theme delivery needs an explicit native adapter as described in section 7. The DTCG 2025.10 token format is a stable Community Group specification; the module manifest and adapter contract below are project-defined. Source: https://www.designtokens.org/TR/2025.10/format/ .

The module is declarative. Keep application behaviour in reviewed host code and design tokens/styles/icons in the module. Implement one adapter to the host's existing component/theming mechanism. React, Vue, Svelte, server-rendered HTML and other browser stacks can consume the same CSS variables; each still needs a real host integration. Native mobile/desktop toolkits require a separate adapter and verification, not a claim of automatic compatibility.

```text
themes/<id>/
  theme.json          # manifest, compatibility, required contrast pairs, budgets
  tokens.json         # editable source of truth
  tokens.css          # generated deterministic scoped variables
  theme.css           # scoped component presentation, no application logic
  icons.svg           # small original/licensed symbol subset
  preview.html        # local visual specimen, never runtime application code
  README.md           # usage, supported states/modes, integration and rollback
  LICENSE.txt         # actual applicable license
  CHANGELOG.md        # version and changes
themes/registry.json   # registered themes and chosen default
```

The example theme is `Fieldstone`. It demonstrates this web format; it does not choose the target project's appearance or cover its actual screens.

## 2. Tokens and generated CSS

Use primitive → semantic → component tokens. Business UI consumes semantic names such as `--ui-color-text`; colour names such as `--green-600` should stay behind that contract. Required semantic paths are:

| Group | Paths |
| --- | --- |
| Colour | `color.background`, `surface`, `text`, `muted`, `primary`, `on-primary`, `border`, `focus`, `danger`, `on-danger`, `success`, `on-success` |
| Spacing | `space.1`, `.2`, `.3`, `.4`, `.6`, `.8` |
| Shape | `radius.sm`, `.md`, `.lg` |
| Motion | `motion.fast` |
| Typography | `font.family` |

Additional tokens may use the supported subset. Names use lowercase letters/digits/hyphens. Leaf `$type` or inherited group `$type` is explicit. Supported types: `color` with `colorSpace: "srgb"`, three numeric components in `[0,1]` and alpha; `dimension` with a nonnegative number and `px` or `rem`; `duration` with a nonnegative number and `ms`; `number`; `fontFamily` as an array of plain family names. Whole-value aliases such as `{color.primary}` must resolve without cycles and match type. Unsupported token features must be adapted explicitly, not silently coerced. This is a constrained DTCG-compatible subset, not a complete DTCG parser.

```json
{
  "color": {
    "primary": {
      "$type": "color",
      "$value": {"colorSpace": "srgb", "components": [0.09, 0.42, 0.35], "alpha": 1}
    }
  },
  "space": {
    "4": {"$type": "dimension", "$value": {"value": 1, "unit": "rem"}}
  },
  "font": {
    "family": {"$type": "fontFamily", "$value": ["system-ui", "Segoe UI", "sans-serif"]}
  }
}
```

The fragment above illustrates syntax; a complete theme must include all required tokens. `build-theme` maps paths deterministically to `--ui-<path-with-hyphens>` beneath `[data-ui-theme="<id>"]`. Generated output is checked for staleness. Edit source tokens and rebuild; do not hand-maintain divergent generated CSS.

Scope every `theme.css` selector with the same attribute. Avoid global resets, `:root`, body/html selectors, remote imports, embedded data URLs, executable SVG, unsafe references, and selectors that depend on incidental route markup. The conservative validator supports simple CSS plus media/supports/layer blocks; it deliberately rejects some legal CSS features. Extend the contract with tests when a real need justifies it, rather than weakening checks to pass an artifact.

Colour mode, density and motion are independent preferences. v1's supplied starter has one light palette. When implementing dark or alternate modes, either create separately validated modules or extend the declared token/mode compiler and its validation; do not promise the starter has dark-mode coverage. Density variants may use scoped host attributes; preserve required target sizes. Respect reduced motion and forced colours in the actual application.

## 3. Manifest and validation

The schema is `schemas/theme.schema.json`. Required manifest fields are `schemaVersion`, `id`, `name`, semantic `version`, `description`, `author`, `license`, `tokens`, `styles`, `icons`, `preview`, `compatibility`, `budgets`, and `contrastPairs`. Current `schemaVersion` is `1.0`, `themeApi` is `1`, and the example framework value is `any` (the CSS contract, not automatic installation).

`tokens` is `tokens.json`; `styles` includes `tokens.css` and `theme.css`. Paths are relative, portable and confined to the module; symlinks are rejected. Document provenance and asset licensing. The supplied original template uses MIT; imported reference graphics retain their actual license and must not be relabelled MIT.

Starting runtime budgets are 128 KiB raw and 40 KiB gzip across declared CSS/SVG runtime assets. They are adjustable project policies, not web standards or promises about the complete application. The helper reports the sum of per-file gzip sizes; this is an estimate of compressed payload, not measured wire transfer. It excludes previews/docs and token source from runtime counts. Measure application shell, additional JS, fonts, request overhead and map/data payload separately. The default goal is zero additional theme dependencies and zero remote runtime requests.

Required opaque-token contrast pairs cover text/background, text/surface, muted/background, button/status foregrounds, focus/background and border/surface. Full UI contrast includes actual focus contexts, hover/disabled/selected states, overlays, transparency, charts and icons; the token check cannot replace rendered review. SVG and CSS lint are conservative packaging checks, not a security sandbox for arbitrary untrusted themes.

## 4. Runtime adapter and settings

For the supplied web adapter, implement this sequence in the actual host stack:

1. Read the shipped registry and validate supported `themeApi`, known IDs and local asset paths during build or server startup. Treat files as trusted only after reviewed installation. Do not offer arbitrary archive upload unless the product already has a reviewed import mechanism.
2. Load the chosen module's styles and symbols from local static paths. Prefer build-time known modules and a small existing-host adapter; add no new framework. If modules are loaded on demand, fetch candidate local assets before activation and preserve the current theme on failure.
3. Place `data-ui-theme="<id>"` on a stable application root; ensure dialogs/portals inherit the same variables. Avoid a flash of unthemed content without hiding a broken application behind an endless loader.
4. Expose a Theme settings section: installed theme/name/version, preview, select/apply, reset to default, and supported density/colour-mode preferences. Do not expose unsupported controls. Make controls keyboard operable and labelled.
5. Validate a requested ID against the registry. Resolve user preference → device/project default → known-good bundled fallback. Persist a user preference using the existing settings store, with a documented local fallback if needed.
6. Swap theme without page reload where the stack supports it; preserve route, focus, forms, scroll and business data. Test missing CSS, invalid saved ID, a removed theme and incompatible version. Recover to the previous known-good theme and show an actionable status.
7. Verify with real navigation and every dialog, not just a standalone preview. Confirm the runtime consumes the registry written by the helper; registry creation alone does not implement theming.

## 5. Theme lifecycle

Use `decisions.md` to resolve first/new/modify. Preserve the old styling as a legacy fallback before migration. The first successfully finalized Studio module becomes the default. An application with an established external theme registry needs a documented import/mapping so the helper does not overwrite its meaning.

`register` validates the module and final run dossier, verifies the run's theme digest against current bytes, and writes `themes/registry.json` atomically with a prior-registry backup. Subsequent new IDs preserve the default unless `--make-default` was explicitly selected. Modifying the current default keeps its ID; increment its version and preserve its prior release archive. A current hash only establishes byte identity; substantive evidence still requires the documented human/agent review.

## 6. Release and portability

For the supplied web adapter, run `build-theme`, `check-theme`, `check-run`, `register`, and `package` using the project venv wrapper. `package` validates a web theme archive and produces checksums; it can also package a valid draft. Therefore a successful package operation alone is not a completed redesign. Label drafts and release only after final run acceptance and real application integration. Native resources and behaviour are outside this compiler/validator's coverage.

Keep the release module and design dossier separate. Release only needed tokens/styles/icons/preview/docs with licenses and hashes. Exclude source screenshots containing secrets, application databases, credentials, private reference pictures, build caches and test fixtures. Document where to install the module, host adapter requirements, how to rebuild it, how to add a new theme and how to restore the old version/default. Reproduce a build and test theme switching/rollback before handover.

## 7. Native desktop and mobile adapters

Use the existing project's toolkit and native theming mechanism. Do not add a browser runtime merely to use the web sample. A local HTML board can communicate colours, layout and storyboards, but it is a concept presentation until the actual platform behaviour is exercised.

Before production acceptance of a native theme:

1. Declare the host adapter and supported platform/toolkit versions in the design contract. Identify native build, preview/simulator/device and accessibility tools, and record unavailable required verification as blocked.
2. Define a versioned native module contract covering stable theme identity, semantic tokens, generated resources, supported modes, compatibility, licensing, checksums, installation and rollback. Reuse the host's existing format where available. Preserve the first-finalized/default and later-new/modify lifecycle without creating a competing settings system.
3. Specify and test deterministic conversion from source tokens into native colours, units, type styles, shapes, motion and vector resources. A `rem`, a CSS font-family list or an SVG feature may not map directly to a native toolkit; document each supported conversion and reject unsupported values explicitly.
4. Integrate native components, overlays/sheets and system-owned UI where the host permits theming. Preserve semantics, navigation, focus, form state and user preferences. Inspect complete screen/window/dialog cases across the required device sizes, orientations, scaling and input conditions.
5. Run native builds and actual platform checks for interaction, accessibility, resource/bundle cost, startup and representative runtime performance, offline requirements, persistence, invalid-theme fallback and rollback. Label simulator observations and physical-device observations accurately. A successful web preview or CSS-token contrast check cannot establish these results.
6. Package using the native contract and its validated tooling. If Studio's supplied helper cannot represent that contract, implement and test the required adapter/tooling extension before claiming full Studio theme acceptance. Do not disguise native assets as CSS or weaken the web validator to manufacture a pass. Keep native acceptance evidence explicit in the run dossier.

The shared run records can describe native surfaces and evidence, but their structural checks do not establish native correctness. State which host adapter and checks support the delivered result. A reusable design system may have both web and native adapters; version and validate each adapter's generated output separately.
