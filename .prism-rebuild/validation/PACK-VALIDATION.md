# PRISM Studio rebuild pack — validation record

**Pack:** 1.0.0 · **Target product:** UI Design Studio 2.0.0  
**Prepared:** 26 November 2026, Australia/Hobart  
**Result:** the implementation handoff passed its contract, integrity and helper-tool checks. The production application has not been rebuilt by this pack.

## What was checked

| Check | Observed result | Scope |
| --- | --- | --- |
| Strict JSON parsing | Passed | Duplicate keys, non-finite literals and overflowing floating values rejected |
| Draft 2020-12 domain schema | Passed | 139 definitions, including 34 typed records; all local references resolve |
| Contract fixtures | 31 of 31 expected outcomes | Valid examples accepted and intentionally invalid examples rejected |
| Command catalogue | Passed | 62 unique operations; enum, payload, idempotency, input/output, error/event and requirement references consistent |
| Requirements and cases | Passed | 86 requirements, 96 acceptance cases, nine milestones, nine gates; reciprocal mappings and milestone graph checked |
| Knowledge references | Passed | 40 original rules cite known source IDs with conditional application guidance |
| External OMP templates | Passed | Ten inactive `.md.in` blueprints; frontmatter, names and context ceiling checked |
| Local document links | Passed | Relative Markdown targets exist inside the pack |
| Python syntax | Passed | Nine helper/library/test files parsed |
| Helper regression suite | **19 test methods passed** | All adversarial subtests passed; zero failures, errors or skips |
| Deterministic archive behavior | Passed | Identical bytes after input relocation to `.prism-rebuild` and changed file timestamps |
| Independent content/tool review | Completed | All confirmed material findings resolved and rechecked; no remaining material finding in the reviewed scope |
| Source repository preservation | Confirmed | The original checkout remained clean at the reviewed commit; tests used disposable fixtures |

The final archive carries an exact SHA-256 file manifest. Finalization runs the full checker again, builds the archive twice, compares bytes, extracts it into a fresh directory, checks ZIP CRC and runs the full checker on that extraction. The separately supplied ZIP checksum identifies the delivered bytes; it is outside the ZIP to avoid a self-referential hash.

## Helper tests

The final helper-suite run exited **0** and completed in **5.899 seconds** of unittest time. It ran against a stable manifest before this report and the retained validation evidence were finalized. The recorded input digests in [TOOL-TEST-RESULT.json](TOOL-TEST-RESULT.json) identify the tested helper and contract files; those executable inputs were not changed after that successful run. Complete unittest output is retained in [tool-tests.log](tool-tests.log).

The cases exercise:

- Strict JSON decoding, path traversal and private-state root/child symlinks.
- A child process attempting to redirect its parent's later receipt/log writes.
- Git exclude leaf and parent redirection, with outside bytes preserved.
- Manifest tampering, missing files and unexpected files.
- Worktree preparation preserving dirty source files and existing instructions.
- Activation of only the rebuild skill, idempotent installation, exact restore and conflicting later edits.
- Missing/damaged local packs and intentionally incomplete verification plans.
- Successful selected-gate receipts that remain explicitly partial.
- Nonzero command exits, timeouts, missing/stale evidence and source changes during execution.
- Retention of captured evidence even if a later command removes the original report.
- Currentness invalidation after changed plans, logs, source snapshots or captured artifacts.
- Missing, stale and misattributed release reviews.
- Complete retained output exceeding 2 MiB, including its final sentinel.
- Identical ZIP bytes across renamed input roots and modified timestamps; rejection of in-place archive output.

The first test run found a diagnostic-text assertion mismatch: the test expected “symlink” while the correct guard reported a redirected Git exclude path. Both unsafe actions were already blocked. The assertion was corrected without weakening the blocked-action or no-write checks. A final packaging check also exposed input-directory-dependent ZIP roots; the builder and regression test were corrected before the final successful run.

All synthetic plans, reviews and selected-G0 receipts are explicitly marked `TOOL_HARNESS_ONLY`. They establish helper behavior and are not implementation, browser, host, provider or release acceptance evidence.

## Independent review

A separate reviewer inspected the helpers and contracts without implementing the pack. It reproduced path redirection and evidence-currentness failures, then checked the corrected behavior in isolated fixtures. It also identified missing canonical operations for model preferences, review batches, evidence recording, cost adjustments and lifecycle/read flows; those gaps were resolved with explicit typed contracts.

The reviewer independently checked the expanded schema/catalog and 31 fixtures, then scanned the matching architecture prose. See [INDEPENDENT-REVIEW.md](INDEPENDENT-REVIEW.md) for the reviewed scope and resolved findings. “No remaining material finding” reports the outcome of this review; it is not a guarantee that every future implementation decision is correct.

## Validation environment

| Component | Observed version |
| --- | --- |
| Python | 3.12.14 |
| Operating system | Linux 6.18.57, x86_64, glibc 2.41 |
| Git | 2.56.1 |
| jsonschema | 4.26.0 |
| zlib | 1.3.2 |
| Helper interpreter SQLite | 3.53.1 |

The helpers declare Python 3.10+ syntax compatibility. This execution run used Python 3.12 on Linux; Windows, macOS and every supported Python version were not exercised. Cross-host ZIP byte reproducibility may depend on compression-runtime identity. The preflight SQLite observation is for its interpreter; the installed product must report and qualify its own runtime before choosing its journal mode.

## Source coverage and reuse

All twelve supplied resources are inventoried: ten PDFs totalling **2,385 physical PDF pages** and two lists containing **21 URLs**. Full-document extraction and topic indexing supported task-focused section review. Twenty linked bodies or index/catalog pages were retrievable; the UXPlanet item U13 was preview-only and is explicitly limited in the register. Index review does not imply reading every outbound article or viewing embedded videos.

The pack contains original principles, conditional rules, citations and obsolete-guidance overrides. It contains **no supplied PDFs or bulk article extracts**. See [source inventory](../knowledge/source-inventory.json), [source register](../knowledge/SOURCES.md), [principles](../knowledge/PRINCIPLES.md) and [retired guidance](../knowledge/RETIRED-GUIDANCE.md).

## Claims deliberately left for implementation

This handoff does not establish that UI Design Studio 2.0 has been coded, installed, integrated with a live OMP/MCP host, exercised in browsers, benchmarked as a production application, or used with paid design providers. Its schema does not alone prove transaction isolation, foreign-key ownership, currency validity, ledger sums, authorization, filesystem crash durability or dependency applicability. Those are mapped implementation acceptance obligations.

Human participant research remains **DEFERRED** by project policy. Real automated browser interaction, accessibility checks, required host integration and isolated package verification remain required for the corresponding release claims. No release, default-branch merge, remote push or paid external design request was performed while producing this pack.

## Reproduce the pack checks

From the extracted pack, in an environment with `jsonschema` available:

```bash
python3 tools/verify-pack.py --root .
python3 tools/test_tools.py -v
```

The integrity-only bootstrap requires no optional library:

```bash
python3 tools/verify-pack.py --root . --integrity-only
```

Follow [START-HERE.md](../START-HERE.md) to prepare an isolated implementation worktree. The deliberately empty example gate plan must be filled with real product tests; it cannot qualify the application in its supplied form.
