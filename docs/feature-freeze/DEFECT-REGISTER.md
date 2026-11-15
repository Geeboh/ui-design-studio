# Defect register

`studio.py` and `design_server.py` below refer to `.omp/skills/ui-design-studio/scripts/`.
Verification status describes observed checks, not proof that no other defects exist.

| ID | Severity | Category | Component | Status | Related commit |
| --- | --- | --- | --- | --- | --- |
| FF-001 | High | Release correctness | `studio.py` scope acceptance | Fixed, focused checks passed | `5fef92d097` |
| FF-002 | Medium | Coverage correctness | `studio.py` critical applicability | Fixed, focused checks passed | `5fef92d097` |
| FF-003 | Medium | Worker boundary | `studio.py` allowlist | Fixed, focused checks passed | `5fef92d097` |
| FF-004 | Medium | Resume correctness | `studio.py` source dependency graph | Fixed, legacy/current regression passed | `5fef92d097` |
| FF-005 | High | Resource exhaustion | `studio.py` JSON and hash reads | Fixed, FIFO regression passed | `5fef92d097` |
| FF-006 | Medium | Approval integrity | `design_server.py` artwork library | Fixed, 76 server tests passed | `1e137f6658` |
| FF-007 | Medium | API correctness | `src/ui_design_studio/server.py` instructions | Fixed, 19 MCP tests passed | `5fef92d097` |
| FF-008 | Medium | Liveness correctness | `src/ui_design_studio/dashboard.py` probes | Fixed, 43 dashboard tests passed | `7ebd26664d` |
| FF-009 | Medium | Resource cleanup | `design_server.py` nested run cleanup | Fixed, 76 server tests passed | `1e137f6658` |
| FF-010 | Low | API permissions metadata | `src/ui_design_studio/server.py` status tools | Fixed, 19 MCP tests passed | `5fef92d097` |
| FF-011 | Low | Documentation | `references/run-records.md` selected roles | Corrected from source contract | `d1f6923ee4` |
| FF-012 | Low | Evidence provenance | Historical remediation handoff and ledger | Retrospective correction added | `d1f6923ee4` |
| FF-013 | Low | Measurement documentation | Historical benchmark method | Timing comparisons explicitly inconclusive | `d1f6923ee4` |
| FF-014 | High | Secret disclosure | ZIP, wheel and sdist inputs | Fixed, 13 builder and 5 package tests passed | `3d47815bc3` |
| FF-015 | Medium | Distribution integrity | `scripts/package_release.py` output location | Fixed, 13 builder tests passed | `3d47815bc3` |
| FF-016 | Medium | Failed-write integrity | `scripts/package_release.py` sidecar | Fixed, 13 builder tests passed | `3d47815bc3` |
| FF-017 | High | Approval identity | `design_server.py` retained artwork IDs | Fixed, failing/passing ID regression | `1e137f6658` |
| FF-018 | Medium | Run-selection correctness | `.omp/extensions/ui-design-progress.ts` | Fixed, 52 Node tests passed | `700cc01362` |
| FF-019 | Medium | Browser lifecycle | Dashboard `landing.js` | Fixed, real-browser regressions passed | `700cc01362` |
| FF-020 | Medium | Keyboard accessibility | Dashboard `dashboard.js` | Fixed, real-browser regressions passed | `700cc01362` |

## FF-001

An otherwise complete component dossier with a fresh finalization digest passed full validation and registered a default theme. Root cause: scope enum validation did not enforce the full-release boundary. The shared validator now blocks bounded scopes, preserving separate scoped completion. Consumer impact: defective full-release PASS becomes BLOCKED. `tests/test_feature_freeze.py` checks all six bounded scopes through engine, real CLI, registry rejection, and successful scoped completion. Baseline failed; corrected tests passed.

## FF-002

A ready/error/recovery surface could exclude every recovery viewport because any remaining error state satisfied a shared existential check. Every declared critical state now needs an applicable viewport. The change closes a coverage omission, while justified sparse viewport exclusions remain supported. Regression risk is rejection of previously accepted incomplete records. The dedicated recovery-state test failed before correction and passed afterward; existing sparse coverage tests passed.

## FF-003

`worker_packet(..., allowed_actions=[])` granted read, write, and evidence actions. A truthiness default conflated absence with an explicit empty list. Defaulting only for None preserves the caller's contract without changing omitted arguments. Tests cover default, empty, and read-only lists, including real MCP calls. The original checkout has an independent uncommitted correction and remains untouched.

## FF-004

Changing the recorded remediation contract produced only `staleNodes=["remediation-contract"]`, leaving dependent context, routing, evidence, and approvals unmarked. Missing graph edges caused the defect. New manifests include source edges; old manifests receive the same invalidation during checking without rewriting history. Regression risk is additional, justified re-review after a real requirement change. A dedicated regression checks both current and legacy graph variants.

## FF-005

A FIFO at `.design-server.json` blocked `read_record` indefinitely and held startup/session locks. Direct `sha_file` had the same blocking-open hazard. Subprocess reproductions timed out without a writer. Shared JSON/hash readers now open nonblocking, reject nonregular descriptors, and refuse final-component symlinks. Missing-file and parse-error handling remain intact. Regression risk is deliberate rejection of special files previously accepted by low-level readers. The POSIX FIFO regression passed for both readers.

## FF-006

Replacing retained HTML and editing its mutable manifest hash let previews display bytes outside the original content-addressed version. The library now verifies the version digest against path, file hashes, title, and context when retaining, listing, or serving. Tampered records disappear from discovery and previews fail closed. Existing legitimate versions remain readable. Tests reproduce simultaneous byte/hash tampering, metadata tampering, HTTP rejection, and preserved original artwork.

## FF-007

Valid explicit repository-relative MCP instruction paths failed the engine's required-instruction check. Forwarding unnormalized strings and guessing a non-Git repository root caused the mismatch. The adapter now resolves instructions within its fixed repository and passes that boundary to the engine. The engine compares actual confined required paths. Regression risk is rejection of undocumented, incorrect path forms. Real stdio tests cover explicit run/project instructions, empty allowlists, and missing required instructions.

## FF-008

Four stalled foreign runs occupied all probe workers until a shared deadline expired. A queued healthy owned run was falsely reported stopped and the selected run disappeared. Scheduling selected and owned runs first preserves the deadline and display ordering. Regression risk is lower priority for foreign probes, not longer total refresh. The real stalled-HTTP regression now includes four foreign owners, a healthy owned run, and a separately owned selected run.

## FF-009

Cleanup-all returned PASS with zero runs while a valid nested listener remained live. Its single-depth locator glob disagreed with supported nested discovery. Recursive enumeration retains confinement and run validation. Regression risk is intentionally discovering additional nested owned runs. Real-server tests verify nested shutdown and preserve unrelated servers, directory symlinks, and symlinked locator targets.

## FF-010

Compact and paged status tools advertised read-only behavior even though snapshots retain artwork on disk. Their annotations now match the existing full-status tool. Client permission decisions can therefore reflect actual effects. No runtime data shape changes. Updated protocol-contract tests check metadata and actual retained artwork identity.

## FF-011

The run-record guide required all seven specialists despite schema 1.2 allowing selected roles. The guide now distinguishes schema 1.2 selected roles from legacy 1.1 all-seven assignments. Source validators and existing role tests establish the contract. No behavior change or regression risk.

## FF-012

The historical handoff and ledger said remediation remained uncommitted despite commit `c7660d911347d00abe7ab6ca0741f3e4586e1815`. Original R15 PASS also lacked its commit evidence at that session's handoff. Retrospective sections preserve the original account while recording the later commit and release chronology. Verification used the actual historical commit contents. No code behavior changes.

## FF-013

Historical benchmark prose implied five samples for all timings. Hash timings use three, and compact/full timing paths do different work. Documentation now states those limits and treats timing comparisons as inconclusive. No optimization or speedup is claimed. Structural byte and call counts remain narrower observations. Rewriting a benchmark solely to manufacture a favorable number is not justified.

## FF-014

A synthetic `.omp/skills/ui-design-studio/.env.production` entered the release ZIP source list despite Git ignoring it. Exact-name filtering missed environment variants. ZIP collection now excludes `.env.*` except plain `.env.example`. Wheel/sdist configuration independently excludes environment variants without relying on VCS ignores. Review caught a negative template exception reopening private ancestors. Two insufficient configuration attempts were discarded. The existing build hook now includes templates only when Hatch's own path exclusion admits every ancestor. Actual wheel/sdist tests verify retained plain templates and excluded secrets, including templates below private parents. Regression risk is deliberate exclusion of previously packaged private inputs.

## FF-015

The first build to `docs/custom.zip` succeeded, then the output and checksum became future source inputs. Output checks ran after the source list was captured and after the manifest write. Reject packaged-tree destinations before mutation. Regression risk is rejection of formerly accepted unsafe custom destinations; dedicated `dist` and external paths remain supported. A disposable build reproduced PASS for the defective path.

## FF-016

A symlinked ZIP sidecar was rejected only after replacing the existing ZIP, leaving old checksum metadata. Output safety is now checked before mutation. Both outputs are staged; an existing archive is backed up by a same-directory hardlink and restored if checksum replacement fails. Injected write/publication failures verify preserved prior bytes and temporary-file cleanup. A rollback failure retains the backup rather than deleting recovery evidence. Two filesystem replacements cannot be crash-atomic. Consumers must verify checksums; maintainers must rebuild or recover the retained backup after an interrupted publication. This limit is not reported as an atomic transaction.

## FF-017

Swapping only the IDs of two otherwise valid retained manifests made an approval option display `b.html` while its digest still bound `a.html`. Parent execution confirmed the mapping mismatch. The content-version check alone did not validate the derived artwork ID. IDs now match the existing path/version derivation. No format migration is required. The metadata-ID regression failed before correction and passed afterward. Legitimate retained records keep their IDs.

## FF-018

With two existing unfinished runs, selecting B in the browser caused the next ordinary tool result to open A. The extension confused unopened peers with newly discovered runs. Per-session discovery tracking preserves existing peers while allowing genuinely new runs. Failed opens are removed from discovery tracking so recovery remains retryable. The first correction broke an existing interrupted-open test; the parent fixed that regression rather than weakening it. All 52 Node tests passed afterward. Session reset, explicit selection, and completed-run behavior remain covered.

## FF-019

Landing `pagehide` canceled polling permanently because no persisted `pageshow` handler restarted it. In actual Chromium, simulated persisted events left a newly created real run invisible after 4.5 seconds while the page still reported Connected. A stopped flag, current controller identity, and one timer now cancel hidden work, ignore stale completions, and restart single-flight polling. Four browser regressions include idle and in-flight restoration. Native browser BFCache restoration itself remains unverified.

## FF-020

A concurrent reviewer could hide and disable an approval form while its artwork dialog stayed open. Closing the dialog tried to focus the still-connected hidden opener. Actual Chromium left the invisible `viewer-close` button focused. Restoration now selects an enabled visible original, replacement, heading, or navigation control. The real-browser regression checks normal original focus and visible replacement focus after concurrent approval. No visual design or workflow change is introduced.

