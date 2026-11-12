# Release validation

**UI Design Studio 1.1.0 · Checked 12 November 2026**

This record covers the distributed designer package, its installation/routing utilities and its supplied web-theme specimen. It does not claim that any recipient's application has been redesigned, tested or deployed.

## Checks completed

| Check | Result | Scope |
| --- | --- | --- |
| Python regression suite | **PASS — 67 tests** | 15 installer tests and 52 Studio/theme/evidence/model-routing tests |
| Skill metadata | **PASS — 9 skills** | Required name/description fields, names and description bounds |
| Documentation structure | **PASS** | Markdown links, fenced blocks and JSON examples across the distribution |
| JSON source files | **PASS** | Release metadata, token source, theme manifest and theme schema |
| Shell syntax | **PASS** | `install.sh` and `tools/ui-design` |
| Fresh installation | **PASS** | Creates a profile-free policy with `modelPolicy: auto-models`, installs docs/license and creates a new pending run |
| Actual 1.0 → 1.1 upgrade | **PASS** | Old package installed first; new dry run/update performed; existing configuration and unrelated application bytes preserved |
| Upgrade restoration | **PASS** | Original agent bytes and retired profile files restored; independent generated theme/run artifacts retained |
| Context/model acceptance | **BLOCKED as expected** | A new run with unknown project context and pending routing cannot finalize |
| Draft theme/default behaviour | **PASS** | Scaffold validates/packages without creating a registry or changing the default |
| Independent source review | **PASS after correction** | Fixed managed-file overwrite protection; documented the legacy-run continuation boundary |
| Cross-project assessment exercise | **PASS within source-only scope** | Fresh-context worker followed the fixture's requirements instead of its stale TADA profile; all five original files stayed unchanged |
| Distribution builder | **PASS** | ZIP CRCs and every archive member checked against source; manifest verified |
| Actual Fieldstone token/asset checks | **PASS** | Supported tokens, scoped CSS/SVG, declared byte budgets and eight opaque contrast pairs |

The tests use explicitly synthetic fixtures. Native OMP configuration responses in routing tests are simulated; they are not evidence of live provider execution. The release builder regenerates checksums after the final documentation is written.

## Installation and routing safeguards exercised

Installer tests cover no-write dry runs; paths containing spaces; complete preflight; repeated installation; unowned conflicts; preservation of existing configuration and unrelated instruction bytes; safe managed-file upgrades; obsolete-file retirement; backup/restore; permission preservation; refusal to overwrite later edits; symlink rejection; active-routing conflicts; and rollback after an injected write failure.

An independent reviewer reproduced a defect in the earlier update logic: an owned file could be replaced even after a local edit. The release now requires the current bytes and mode to match the saved installation record before replacement, unless they already match the desired release. The reviewer reran the same reproduction and confirmed rejection with no partial mutations.

The nine dedicated routing tests cover exact apply/restore behaviour; idempotency; current-model equality; provider-default handling; changed mappings; concurrent-run conflicts; later user edits; write-failure rollback; native override/query failures; invalid aliases/effort; symlinks; interrupted prepared-journal recovery; and advisory-lock behaviour. A successful apply establishes local configuration only. The director must inspect actual worker metadata before claiming effective routing.

The unchanged complete synthetic dossier produced by the original 1.0 helper remained readable and passed its legacy checks under 1.1. New model/context helpers require a 1.1 dossier. The documented continuation procedure preserves old records and carries forward valid work without importing final acceptance.

## Cross-project assessment exercise

A fresh-context worker used the assessment skill on a small fictional scheduling application, Lumen Workshop. Its configuration deliberately retained a stale `profile: tada` value and selected `current-model`. The worker derived the actual project context from its instructions and requirements, correctly recorded that offline edits were not required, and preserved the chosen model policy. It left routing pending because no live OMP session identity was available.

The resulting source-based report inventoried two page-like sections and one dialog, identified missing save/confirmation and recovery behaviour, ambiguous date/time presentation, unnamed controls and insufficient muted-text contrast, and provided recommendations with verification limits. All five original fixture files were compared by SHA-256 and remained unchanged; new artifacts were confined to `docs/design`. This exercise demonstrates context discovery and assessment discipline on a fixture. It does not establish browser behaviour, actual user research or a completed redesign.

## Evidence and theme checks

The Studio tests exercise unresolved context/routing, stale context/report hashes, changed policy/assignments, current-model mismatch, required-role coverage, requirement-grounded offline applicability, legacy offline protection, actual evidence hashes, incomplete page/state coverage, invalidated approvals, independent reviewer records, first/new/modify default lifecycle, concurrent registration, version increases and stale replay.

Theme tests cover supported token types and aliases, alias cycles/type mismatch, CSS variable collisions, generated-file freshness, contrast failures, unsupported alpha claims, CSS/SVG restrictions, asset/path confinement, byte budgets, deterministic theme archives and preservation of unrelated files.

### Fieldstone measurements

| Measure | Observed value |
| --- | ---: |
| Declared runtime raw bytes | 12,442 bytes |
| Sum of individual runtime-file gzip sizes | 3,151 bytes |
| Supported source tokens | 23 |
| Original SVG symbols | 8 |
| Text/background contrast | 13.5832:1 |
| Text/surface contrast | 14.8366:1 |
| Muted/background contrast | 5.8106:1 |
| Primary foreground/background | 6.4016:1 |
| Danger foreground/background | 7.1236:1 |
| Success foreground/background | 6.6180:1 |
| Focus/background contrast | 5.2537:1 |
| Border/surface contrast | 3.9470:1 |

The helper's runtime total includes the manifest and declared styles/icons. It excludes preview/docs and editable token JSON. Gzip sums are reproducible estimates, not measured browser transfer totals. Token contrast checks do not establish the accessibility of complete rendered interfaces.

## Practical limits

No live recipient OMP session, provider-account routing, actual production application, physical device or native desktop/mobile adapter was available for this release check. The included standalone HTML and theme resources were inspected structurally and through deterministic checks. No successful browser screenshot/interaction or assistive-technology audit is claimed for the specimen. Validate the actual application in the first design run.

The project-independent workflow can guide other UI stacks, but the included executable theme compiler, validator, registry and packager implement the CSS/SVG web adapter. A native toolkit requires the documented native adapter and real platform checks. Package test success must not be presented as native compatibility or WCAG conformance.

## Reproduce the package checks

From the extracted package directory:

```bash
python3 -m venv .venv-test
.venv-test/bin/python -m unittest discover -s tests -v
bash -n install.sh tools/ui-design
.venv-test/bin/python scripts/package_release.py --check
```

These package tests use Python's standard library and require no Python dependency downloads. Use the project's own build, browser/native, accessibility and performance checks for its actual interface. See [Distribution](DISTRIBUTION.md) for release reproduction and [Installation](INSTALLATION.md) for installation/upgrade troubleshooting.
