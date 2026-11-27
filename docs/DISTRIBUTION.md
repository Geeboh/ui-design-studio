# Distribution and release maintenance

UI Design Studio 2.0.6 is the complete project-local OMP skills distribution and optional standalone local MCP adapter. It may be copied, modified and redistributed under the included MIT license. Keep copyright and license copies. Imported reference images and assets used in future design runs retain their own licenses; the package's license does not change them.

## What recipients receive

The ZIP contains one top-level `ui-design-studio-v2.0.6/` directory. Start at `README.md`; follow `docs/INSTALLATION.md` and `docs/RUN-TYPES.md`. `release.json` identifies version, default policies and compatibility scope. `docs/VALIDATION.md` states what was actually checked.

Included: nine skills, seven native OMP specialist definitions, two convenience commands, a native status extension, the Design Server and dashboard, focused reference documents, installation/update/restore utilities, project/run/model-routing helpers, theme schema/compiler/validator, an original CSS/SVG specimen, copy-and-paste run prompts, regression tests and a reproducible release builder.

Not supplied: OMP itself, model accounts, API credentials, a preselected paid provider, the recipient's application source, or a completed design of that application. The reusable workflow derives requirements from each project. The bundled executable theme implementation targets the web; native desktop/mobile projects require their real host adapter and native acceptance checks.

## Verify a download

Compare the ZIP's SHA-256 with the accompanying `.zip.sha256` file or release announcement. After extracting, verify individual source files from the package directory:

```bash
sha256sum -c MANIFEST.sha256
```

On a platform without `sha256sum`, use the Python check below through a virtual environment. Checksums detect changed bytes; they are not a signature or proof of publisher identity. Distribute the ZIP and its checksum through a trusted channel.

## Reproduce the checks

From the extracted package directory:

```bash
python3 -m venv .venv-release
.venv-release/bin/python -m pip install . build hatchling zxing-cpp pytest playwright
.venv-release/bin/python -m playwright install chromium
.venv-release/bin/python -m pytest -q
node --test tests/test_progress_extension.mjs
bash -n install.sh tools/ui-design
.venv-release/bin/python scripts/package_release.py --check
```

The only use of system Python is creating the virtual environment. The OMP helpers and release builder use the standard library. The full verification environment also needs the package, build backend, QR decoder, pytest, and Playwright shown above. Playwright and its browser are verification-only dependencies, not runtime dependencies. Without Playwright, browser regressions are skipped and the full browser gate has not passed. Set `UI_DESIGN_TEST_BROWSER` to an existing Chromium executable instead of downloading one when appropriate. OMP/provider execution and the target application's native checks remain separate from these package tests.

## Build a distribution

After reviewing and testing the complete source tree:

```bash
.venv-release/bin/python scripts/package_release.py --output dist/PRISM-Studio-2.0.6.zip
```

The builder regenerates `MANIFEST.sha256`, writes the ZIP and a SHA-256 sidecar, reopens the ZIP, checks every entry against its source bytes and checks CRCs. Entries have deterministic ordering, release-date timestamps and portable file modes. `install.sh` and the project wrapper retain executable permissions.

Only the declared source directories and root release files are packaged. Virtual environments, bytecode caches, Git metadata, installation backups and generated project runs are excluded. Review the source tree for private material before distribution; an allowlist is not a general secret scanner. Do not distribute a used project directory as if it were the clean package.

The source ZIP also includes `src`, `pyproject.toml`, the build hook, and the [MCP adapter guide](MCP.md). Build the standalone wheel with `python -m build --wheel`. Hatchling maps the same authored `.omp/skills` and `.omp/agents` files into `ui_design_studio/payload`; no second source copy is maintained. Wheel builds reject symlinks and exclude bytecode, caches, private runtime records, and credentials. The wheel carries no OMP installation step or client configuration mutation.


For another release, update the release version and date, code version constants, release notes and user-facing commands consistently; run meaningful checks again and rebuild. Theme versions are independent designer package versions. Fieldstone's theme version remains 1.0.0 because its runtime styling is unchanged; distribution guidance around it may change.

## Compatibility and support record

Record the recipient's OMP version, operating system, model policy, current run path and the exact failing command when diagnosing a problem. Share a redacted error and relevant output; exclude credentials and private captures. Use `tools/ui-design doctor --repo .` after installation, then the targeted helper/test relevant to the issue. A doctor pass is discovery, not an application quality verdict.

Model-routing helpers temporarily edit only the seven package agents and keep a restoration journal. Finish or park workers and restore those assignments before package maintenance. The installer preserves user configuration and refuses conflicting unmanaged or later-edited files rather than silently replacing them.

The skill's guidance adapts to the installed runtime. Do not advertise every OMP release or every native UI toolkit as tested; use the validation record for the actual release checks and the first design run for project-specific verification.
