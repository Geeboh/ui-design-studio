# Release validation

## Version 2.0.9 candidate · 26 November 2026 UTC

This release record covers the PRISM Studio rebuild, the standalone MCP adapter, the project-local installer, the authenticated dashboard, and release packaging. Human participant research remains deferred by project policy.

| Check | Observed result | Scope |
| --- | --- | --- |
| Core and web receipts | PASS | M0-M8 focused gates on the clean candidate |
| Dashboard browser matrix | PASS; 14 tests each | Chromium, Firefox, and WebKit |
| Standalone OMP host regression | PASS; 52 tests | Live no-tools RPC readiness and UI Design Studio discovery |
| Acceptance mapping | PASS; 96 cases | Current-candidate mapping with declared sequential review fallback |
| Python distributions | PASS | Wheel, sdist, and source ZIP built from the current source |
| Manifest and archive verification | PASS; 185 source hashes | `scripts/package_release.py --check`, ZIP CRC, sidecar, and private-path exclusion |
| Installer regression | PASS; 32 tests | Project-local install, update, restore, conflict, and portability behavior |

The release review records `PASS_WITH_DECLARED_REVIEW_FALLBACK`. This is not human participant research or recipient-application acceptance evidence. Native Windows/macOS, physical devices, and target-application usability remain outside this package validation.

## Version 1.4.3 candidate · 16 November 2026 UTC

This patch release publishes the initial source-grounded documentation library and aligns package metadata. It adds no runtime dependency or run-schema migration.

| Check | Observed result | Scope |
| --- | --- | --- |
| Focused package tests | 41 passed and 47 subtests passed | `tests/test_release_builder.py`, `tests/test_mcp.py`, and `tests/test_mcp_package.py` |
| Source ZIP build | PASS; 155 packaged files, 1,648,023 bytes | `dist/UI-Design-Studio-OMP-v1.4.3.zip` |
| ZIP checksum | PASS | SHA-256 `d091ae4936a8247014255cb42ee1d082a7ffbe3ceab6328859ffc6a1bd9d1085` |
| Manifest check | PASS; 154 source hashes verified | `scripts/package_release.py --check` |
| Documenter coverage | 141/141 eligible source files and 16/16 generated pages reviewed | Source snapshot `40f3ff4151dfb62aa2f79001641057c0d7e4305bcdd7a66646a1f62af8280213` |

The three screenshots retained in this source release are redacted synthetic v1.4.2 dashboard captures. They are not new v1.4.3 recipient-application acceptance evidence. Hosted release assets are outside this local source verification scope.

## Version 1.4.2 candidate · 15 November 2026 UTC

This local candidate builds merged main `8ca4c9e9795839181005c9df82563e4a42e8fc83` with a patch-version update, release documentation, and fresh screenshots. No tag, hosted release, or deployment was created. Uncommitted changes in the original checkout are excluded.

| Check | Observed result | Scope |
| --- | --- | --- |
| Python distributions | Wheel and sdist built successfully | Existing builder; wheel built from the sdist |
| Full Python suite | 299 tests and 212 subtests passed | Linux, Python 3.12.3, actual candidate wheel, Chromium 159 |
| Minimum-Python installed package suite | Five tests and four subtests passed | Python 3.10.22; installed CLI, MCP identity, and payload behavior |
| Fresh screenshots | Three inspected captures | Actual 1.4.2 connection dashboard, durable guided approval, and retained sandboxed specimen |
| Approval capture | Exact review digest matched; decision survived reload | Synthetic browser form submission, not recipient-application acceptance |
| Screenshot privacy | Bearer URLs, connection identity, and private absolute paths masked or cropped out | No fabricated UI state |

The source ZIP builder regenerates `MANIFEST.sha256`, checks archived bytes against current sources, and verifies ZIP integrity before producing a checksum sidecar. The local `dist/RELEASE-VERIFICATION-v1.4.2.json` records final artifact identities and content comparisons; `dist/SHA256SUMS-v1.4.2.txt` covers the handoff files. Checksums are not signatures.

The retained [feature-freeze records](feature-freeze/) describe the earlier merged engine audit. They are not a new audit of this version-only candidate. No new repository-wide security scan or Node suite was run for the release metadata update. Native Windows/macOS, other browser engines, a second physical LAN device, and human recipient-application testing remain unverified.

Screenshot timestamps use the browser's local timezone. The candidate date above uses UTC. See [release notes and screenshots](RELEASE-v1.4.2.md).

## Final remediation revalidation · 16 November 2026 UTC

This release revalidation covers the approval API, attachments, browser annotations, SVG rendering, approval ordering, release packaging, and captured screenshots. It uses synthetic fixtures and Chromium on Linux.

| Check | Observed result | Scope |
| --- | --- | --- |
| Full Python suite | 310 tests passed | Repository suite |
| Approval/server focused suite | 85 tests passed | Approval persistence, rollback, attachments, annotations, SVG, and ordering |
| Browser approval suite | 9 tests passed | Chromium approval flow, image upload, annotation editing, undo/redo, and reload state |
| Static checks | PASS | Python compilation, dashboard Node syntax, and `git diff --check` |
| Source ZIP | PASS; 138 archive entries | Includes changelog and release notes |
| Manifest and archive verification | PASS; 137 source hashes verified | `sha256sum -c MANIFEST.sha256`, ZIP CRC, and ZIP sidecar |
| Python distributions | PASS | Wheel and sdist built |

The retained screenshots are synthetic browser captures, not recipient-application acceptance evidence. Firefox, WebKit, native Windows/macOS, physical devices, and human recipient-application testing remain unverified.

## Current main revalidation · 16 November 2026 UTC

This revalidation covers checkout `main` at `5a3c603e4f95c884d5b0535eb4aa52c2a7ff62c4` plus the current remediation changes. It uses disposable local artifacts and synthetic fixtures. No hosted release, deployment, or human UAT was performed.

| Check | Observed result | Scope |
| --- | --- | --- |
| Full Python suite | 312 tests and 212 subtests passed | `.venv`, Linux, Chromium executable configured for browser tests |
| Affected browser suite | 8 tests passed | Direct Python Playwright Chromium coverage |
| Node extension suite | 52 tests passed | Node `--experimental-strip-types` |
| Static checks | PASS | `compileall`, Node syntax, shell syntax, Ruff correctness subset |
| Benchmark contract | PASS | Offline synthetic benchmark compared stable committed contract |
| Dependency audit | PASS | `pip-audit` reported no known vulnerabilities |
| Filesystem scan | PASS | Trivy 0.76.2 returned no findings; no language/config files detected |
| Source ZIP | PASS | 137 archive entries; final checksum sidecar generated and verified |
| Manifest and archive verification | PASS | 136 source hashes verified; `sha256sum -c MANIFEST.sha256` passed |
| Wheel and sdist | PASS | `ui_design_studio_mcp-1.4.2-py3-none-any.whl` and `.tar.gz` built |
| Playwright Fast application QA | NOT RUN | `PLAN_NOT_READY`; no application config, CLI, or project was available |

Direct Chromium tests are not a Playwright Fast pass. Firefox, WebKit, native Windows/macOS, physical devices, and recipient-application acceptance remain unverified.

## Version 1.4.1 Cortex remediation · 14 November 2026

The release checks cover the remediation changes on Linux with Python 3.12.3 and Node 24.22.2. They use synthetic fixtures and do not establish recipient-application design evidence.

| Check | Observed result | Scope |
| --- | --- | --- |
| Remediation, design, and Studio focused suite | 143 passed, 50 subtests | Focused remediation, design, and Studio regression checks |
| Dashboard suite | 43 passed, 37 subtests | Dashboard regression checks |
| Wheel package suite | 4 passed, 3 subtests | Built 1.4.1 wheel |
| Wheel build | PASS | Standalone MCP runtime package |
| Release package validation | PASS, 103 files verified | Manifest and package metadata |
| Screenshots | Three redacted synthetic dashboard captures included | Visual reference only |

## Version 1.4.0 global installation and automatic OMP dashboard · 13 November 2026

Checked on Linux with Python 3.12.3, Node 24.22.2, and actual OMP 18.20.0. These checks used temporary HOME directories and synthetic projects, not a production application's design evidence.

| Check | Observed result | Scope |
| --- | --- | --- |
| MCP, dashboard, and installed package | 61 Python tests passed | Existing protocol/authorization/ownership contracts, foreground readiness, human QR output, parent EOF, signals, occupied ports, and installed console operation |
| Global installer | 11 Python tests passed | Owned upgrades, unrelated executables, symlinks, failure cleanup, flag routing, and actual pip parsing with hostile external target configuration |
| Existing project installer and installed extension | 19 Python tests passed | 15 installation/update/restore cases and four extension payload installation cases |
| OMP extension | 49 Node tests passed | Awaited startup, single-flight child ownership, bounded recovery, explicit stop, selected-run recovery, cancelled switches, authenticated discovery, and preserved Pi Tasks ownership |
| User-global installation | Real installation and repeated upgrade passed | The same installed executables served two projects with spaces in their paths, without project-local `.omp` installation |
| Installed CLI and SDK | Actual consumers passed in both projects | Authenticated landing, guide access, pending create/resume, CLI discovery, independent QR decoding, EOF cleanup, and dossier preservation |
| Native OMP | Actual PTY lifecycle passed | Automatic dashboard before any run, local/LAN URL display, unexpected child recovery, explicit stop inhibition, explicit restart, and owned shutdown |
| Rendered terminal QR | Two complete actual OMP cards decoded independently | The decoded value exactly matched each displayed LAN capability URL. A historical card cropped by scrolling was not a complete QR |
| Source identity | Installed bytes matched current source | Tested global CLI/backend files and the installed OMP extension |

Independent review found an inherited pip-configuration destination hazard, an unverified discovery-display path, lost run selection during recovery, and premature teardown on a cancelled session switch. The fixes have focused behavioral regressions. A real reinstall with hostile external pip configuration preserved an unrelated user executable.

OMP's child remains available during work and approval pauses. Recovery stops after three rapid failures and reports an actionable restart command. This is not an OS daemon or a promise to survive machine shutdown. Explicit stop and completed-run cleanup remain effective. Foreground output names Ctrl-C; OMP output names its own stop command.

No native Windows/macOS, second physical LAN device, or other native MCP-client verification was performed for this change. Existing trusted-LAN HTTP and private-capability limits still apply.

After the 1.4.0 version update, the final built wheel passed four package tests outside the checkout. The protocol suite passed 14 tests, the project installer passed 15 tests, and the global installer passed 11 tests. These 44 rerun cases overlap the 140 completed-feature cases above; they are not 44 additional unique cases.

The final version-sensitive checks used the built release wheel:

```bash
export UI_DESIGN_TEST_WHEEL="$PWD/dist/ui_design_studio_mcp-1.4.0-py3-none-any.whl"
python -m unittest discover -s tests -p 'test_mcp_package.py' -v
python -m unittest discover -s tests -p 'test_mcp.py' -v
python -m unittest discover -s tests -p 'test_install.py' -v
python -m unittest discover -s tests -p 'test_global_mcp_install.py' -v
```

Reproduce the focused automated checks in a dependency-equipped virtual environment.

```bash
python -m unittest discover -s tests -p 'test_mcp*.py' -v
python -m unittest discover -s tests -p 'test_global_mcp_install.py' -v
python -m unittest discover -s tests -p 'test_install.py' -v
python -m unittest discover -s tests -p 'test_progress_extension.py' -v
node --experimental-strip-types --test tests/test_progress_extension.mjs
```

## Version 1.3.0 portable MCP adapter checks

Checked on Linux with Python 3.12.3, Node 24.22.2, OMP 18.19.0, and headless Chromium. The adapter uses the pinned official MCP Python SDK 1.30.0. These checks use isolated temporary projects and ephemeral listeners.

| Check | Observed result | Scope |
| --- | --- | --- |
| MCP protocol | 14 tests passed | Real SDK stdio initialization, typed tools, resources, prompts, guide access, pending create/resume, path boundaries, two-client reuse, EOF and Linux SIGTERM |
| Connection dashboard | 38 tests passed | Authenticated empty state, private discovery, address inventories, ownership races, bounded probes, partial-refresh recovery, slow-header teardown, CLI errors, and independently decoded Unicode QR output |
| Wheel packaging | 3 tests passed | Bundled engine/assets/guides outside checkout, create/resume and CLI smoke, no private state, and rejected payload/readme/license symlinks |
| Run server | 69 tests passed | Existing evidence and approval gates, actual loopback/LAN listeners, nested preview resources, default ports, encoded proxy prefixes, alias rollback, and owned cleanup |
| Existing Studio engine | 52 tests passed | Theme, dossier, evidence, registration, and OMP-only model-routing compatibility |
| OMP installation | 19 tests passed | Existing installer/update/restore contracts and the exact private MCP ignore subtree |
| OMP progress extension | 33 tests passed | Waiting connections, explicit selection, run-director precedence, verified async command output, expiry, session switching, and unchanged Pi Tasks widget content |
| Clean installed wheel | Actual second-environment smoke passed | Installed console entry points, real stdio, guides/assets, pending create/resume, authenticated listing, dashboard-info, and EOF cleanup outside checkout without project-local `.omp` files |
| Browser | Actual waiting and run pages exercised | Loopback and real LAN alias, keyboard focus and reload, credential replacement recovery, copy, 320px reflow, retained CSS/image preview, digest-bound guided approval, stopped-run display, and explicit browser resume |
| Native OMP | Actual PTY output observed | Installed extension pinned the connection ID and complete loopback/LAN URLs before a run existed; `/ui-design-dashboard` printed verified labels and QR blocks |

The emitted terminal QR was reconstructed and independently decoded with verification-only `zxing-cpp`. No URL was sent to an external QR service. The browser approval remained a synthetic user decision; the complete run stayed pending because its other evidence gates were unmet.

The [release screenshots](RELEASE-v1.3.0.md#screenshots) retain actual Chromium captures from synthetic runs. Connection capabilities, private project paths, and connection identity are visibly redacted. The tests reproduce the automated checks without private development captures.

Independent source reviews identified publication rollback, default-port normalization, encoded proxy paths, pending-read shutdown, partial multi-run refresh, cumulative probe delays, metadata symlinks, unsupported Windows signal registration, and keyboard-token handling. Targeted regressions or actual browser checks verified the corrections. Alternate-family review was unavailable because per-call model overrides were disabled; no permissions were changed.

Native Windows/macOS, a second physical device, and other native MCP clients were not exercised. A simulated no-Unix-signal stdio/EOF branch is not native Windows verification. No public-internet or remote HTTP MCP support is claimed. Trusted-LAN HTTP exposes bearer credentials and content to network observers. Pi Tasks task creation failed in this development session's semantic assessor; a fallback progress widget tracked the work without changing Pi Tasks integration or claiming passing task evidence.

### Reproduce adapter checks

```bash
python3 -m venv .venv-mcp-test
.venv-mcp-test/bin/python -m pip install . build zxing-cpp
.venv-mcp-test/bin/python -m unittest discover -s tests -p 'test_mcp*.py' -v
.venv-mcp-test/bin/python -m unittest discover -s tests -p 'test_design_server.py' -v
.venv-mcp-test/bin/python -m unittest discover -s tests -p 'test_studio.py' -v
.venv-mcp-test/bin/python -m unittest discover -s tests -p 'test_install.py' -v
.venv-mcp-test/bin/python -m unittest discover -s tests -p 'test_progress_extension.py' -v
node --test tests/test_progress_extension.mjs
.venv-mcp-test/bin/python -m build --wheel
```

## Version 1.2.0 progress feature checks

The progress feature was checked on Linux with Python 3.12.3, Node 24.22.2, OMP 18.19.0 and a local Chromium browser.

| Check | Observed result | Scope |
| --- | --- | --- |
| Python and native-adapter regressions | 142 tests passed | 51 server, 52 existing Studio, 15 installer, 4 native-payload and 20 native-adapter cases |
| Native console | Pinned widget observed in actual OMP | Separate below-editor rows, real counts and percentages, blockers and complete URL |
| Console fallback | Periodic non-TTY output observed | Real counts, bar, percentages, full address and no ANSI injection |
| Browser progress and artwork | Actual authenticated LAN page exercised | Workers, task, gate/history data, image and sandboxed HTML thumbnails, full-size images and local dependencies |
| Library and narrow layouts | Actual pagination and 320px reflow exercised | Retained versions, search, two thumbnail pages and four dashboard sections without page-level horizontal overflow |
| Guided decisions and recovery | Real browser submission persisted in a synthetic run | Named option and digest, retained drafts, offline recovery, changed-dependency rejection and reviewer clock differences |
| Independent source review | Findings corrected with targeted regressions | Upstream approval invalidation, session ownership, inert SVG, watcher shutdown, stale-owner recovery, URL selection and keyboard focus |

These checks use isolated, explicitly labelled integration fixtures. They do not approve a production theme, prove public-internet deployment, certify WCAG conformance or establish Windows/macOS compatibility. HTML previews intentionally disable scripts. PDF preview support depends on the browser. The live server is for a small private design team; untrusted networks require an existing protected transport.

## Version 1.1.0 baseline

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
.venv-test/bin/python scripts/remediation_benchmark.py > docs/remediation/v1.4.0/benchmarks.json
```

The original OMP-only helpers and their tests use Python's standard library. Adapter tests require the dependencies in `pyproject.toml` and the verification-only packages shown above. Use the project's own build, browser/native, accessibility and performance checks for its actual interface. See [Distribution](DISTRIBUTION.md) for release reproduction and [Installation](INSTALLATION.md) for installation/upgrade troubleshooting.
