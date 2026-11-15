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
| FF-021 | Low | Testing coverage | `tests/test_dashboard_browser.py` | Fixed, six Chromium tests passed | `e0af2429d1` |
| FF-022 | Low | Audit completeness | `docs/feature-freeze/inspection.tsv` | Corrected, 140 unique existing paths reconciled | `82268c984c` |
| FF-023 | Medium | Repository provenance | MCP status, artwork, requests, approval and cleanup | Fixed, real stdio, HTTP and browser regressions passed | `e0af2429d1` |
| FF-024 | Medium | Concurrent liveness | Landing `session_data` probe lock | Fixed, concurrent authenticated HTTP regression passed | `e0af2429d1` |
| FF-025 | Low | API contract | MCP empty artifact selection | Fixed, real-stdio regression passed | `e0af2429d1` |
| FF-026 | Low | Test diagnostics | MCP protocol failure helper | Fixed, full protocol suite passed | `e0af2429d1` |
| FF-027 | Medium | Package privacy | Source ZIP `.env.example` directory exception | Fixed, 14 builder tests and 15 subtests passed | `6f5c08bb1c` |
| FF-028 | Medium | Security evidence | Historical scanner batch without retained output | Corrected, final scan and 77 current source hashes retained and verified | `82268c984c` |
| FF-029 | Low | Review evidence | Historical summaries without original review records | Corrected, 14 original review records retained with dispositions | `82268c984c` |
| FF-030 | Medium | Verification supply chain | Unnecessary Pillow dependency on Python 3.10 | Removed, dashboard tests and clean audits without Pillow | `e0af2429d1` |
| FF-031 | Low | Concurrent liveness | Landing selected-owner handle replacement | Fixed, deterministic authenticated owner race regression passed | `e0af2429d1` |
| FF-032 | Medium | Acceptance boundary | `studio.py` cross-project registration | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-033 | Medium | Approval integrity | `studio.py` assessment report binding | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-034 | Medium | Offline asset boundary | `studio.py` quoted CSS image sources | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-035 | Medium | Resume correctness | `studio.py` leaf and shared consumer dependencies | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-036 | Medium | Reviewer independence | Engine and dashboard identity comparison | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-037 | Medium | CSS lexical boundary | `studio.py` comment removal | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-038 | Medium | CSS lexical boundary | `studio.py` malformed string recovery | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-039 | Medium | CSS URL interpretation | `studio.py` leading resource whitespace | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-040 | Medium | Resume input inventory | `studio.py` recorded context/routing paths | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-041 | Medium | CSS lexical boundary | `studio.py` unquoted URL comment markers | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-042 | Medium | CSS source substitution | `studio.py` environment fallback | Fixed, affected and full Python gates passed | `35001cedc3` |
| FF-043 | Medium | CSS error recovery | `studio.py` EOF resource extraction | Fixed, affected and full Python gates passed | `35001cedc3` |

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


## FF-021

The existing browser suite tested polling and focus but approved requests only through the backend.
It would not catch broken form submission controls or a browser payload that failed to persist the user's selected option and rationale.
The smallest correction adds one real-browser test through the existing guided controls.
It verifies the exact durable user decision, reviewed input digest, trimmed rationale, and read-only state after reload.
No production behavior changes.
All five Chromium tests passed in the current Python 3.12 environment.
Both full Python gates passed with the additional browser test.

## FF-022

The inherited inspection ledger listed all 116 release-baseline paths but omitted 20 files added during remediation.
Those files had associated review narratives but lacked the requested file-level accounting.
The ledger now lists all 136 current tracked paths, including audit documents and the three new regression modules.
No source component is excluded.
The final inventory check compares immutable tracked membership with ledger membership and rejects duplicates, omissions, or unexpected paths.
This is an audit-record correction with no runtime regression risk.

## FF-023

With runs under `work/docs/design/runs` and themes under `branding/themes`, MCP status rediscovered a nearer default-layout ancestor.
It changed `.design-theme-sources.json` from the fixed repository to its `work` subdirectory.
Artwork publication and review also discarded the known repository.
The new real-stdio regression failed before correction.
The correction preserves the existing authoritative repository through snapshots, artwork, requests, browser approval, and finalized-run cleanup.
Regression risk is disagreement between existing run-relative and repository-relative publication callers.
Verification includes current provenance, imported artwork, a digest-bound review, and actual authenticated HTTP approval.

## FF-024

Four authenticated landing requests against a stalled foreign owner serialized their probe passes under the session lock.
Later viewers exceeded the existing five-second browser deadline while a healthy owned run remained live.
The new real-HTTP regression failed with `TimeoutError: timed out`.
The correction snapshots protected ownership, probes outside the mutation lock, and revalidates ownership before responding.
The existing per-observation deadline and selected/owned priority remain unchanged.
Regression risk is stale ownership after concurrent close or selection changes.
Verification requires all four viewers to receive HTTP 200 with the healthy selected run.

## FF-025

The MCP adapter converted an explicit `artifact=[]` to `None`.
The engine defaults only an omitted list and rejects an empty list, so the adapter silently expanded invalid input to all owned artifacts.
The new real-stdio regression failed before correction.
Testing `artifact is not None` preserves the existing engine contract without changing omitted arguments.
Verification checks the consumer-visible rejected tool result.

## FF-026

`MCPProtocolTests.fail` shadowed `unittest.TestCase.fail`.
When a new regression found an unequal value, assertions raised an unrelated missing-argument TypeError instead of displaying the mismatch.
The failure helper is now named `call_failure`, and every caller was migrated.
A direct assertion check now raises `AssertionError` with both differing values.
No production behavior changes.
The full protocol suite verifies the renamed error-call helper.

## FF-027

The source ZIP collector exempted every path component named `.env.example`.
A directory with that name therefore exposed descendants in the ZIP and manifest.
The new disposable-source regression failed by finding private descendants in the archive.
Only a leaf template file remains exempt; all `.env.*` ancestor directories are excluded.
The 14 builder tests and 15 subtests passed after correction, including retained plain templates and symlink rejection.
No new dependency or archive format is introduced.

## FF-028

The inherited security report cited a Trivy batch whose result was no longer available through the findings API.
A batch ID alone could not substantiate the readiness claim.
The historical claim is narrowed rather than silently treated as fresh evidence.
The current scan and findings responses, target metadata, and 77 authored source hashes are retained in `SECURITY-EVIDENCE.json`.
The tool returned neither scanner version nor scanned-file count, so neither is invented.

## FF-029

The inherited independent-review summary did not preserve original outputs or per-review target provenance.
Current reports distinguish historical narrative from freshly inspected evidence.
Original current review outputs and reviewed source identity are retained with explicit scope and dispositions.
The wrong-target engine report is excluded from acceptance and replaced by a correct-target review.
No production behavior changes.

## FF-030

Unversioned verification instructions installed Pillow 12.3.0 on Python 3.10.
The actual dependency audit reported 42 advisories with fixed version 13.0.0.
Pillow was not a runtime dependency and only provided an avoidable grayscale allocation in QR verification.
The decoder now receives a shaped standard-library byte buffer through ZXing's documented buffer interface.
Pillow was removed from both validation environments and current reproduction instructions.
The complete 44-case dashboard suite with 37 subtests passed on Python 3.10 without Pillow.
Both Python 3.10 and 3.12 dependency audits then reported no known vulnerabilities.
No malicious image was executed and no advisory was suppressed.
An additional final audit prerequisite selected verification-only `filelock` 4.1.0 with 17 advisories on Python 3.10. The unnecessary auditor packages were removed, and that environment was audited through Python 3.12 using its documented `--path` option. Both final resolved environments reported no known vulnerabilities. This was verification setup, not a product dependency or an ignored finding.

## FF-031

The first outside-lock probe correction discarded a valid observation when a concurrent borrow replaced its handle object with the same authenticated listener identity. Object identity did not establish listener replacement. The response now preserves observations only when the current authenticated instance still matches and the owned listener is not stopping. A deterministic delay after a real probe reproduced the false offline state and passed after correction. No cache or longer deadline was added.

## FF-032

Two projects with identical theme bytes had different current project-context sources and separately valid runs. Registration in project B accepted project A's run and created B's registry. The direct engine and CLI lacked the repository confinement already enforced by MCP. Registration now confines the run to the explicitly selected repository before consuming approvals or writing metadata. Valid in-repository run paths remain supported. The new regression failed before correction and passed afterward.

## FF-033

Changing or deleting `report.md` after final approval left `check_run` and registration at PASS when the report was not separately listed as evidence. Final review inputs omitted the required assessment report. Its current confined regular-file SHA now contributes to `reviewDigest`; absence fails closed. Existing final approvals require actual re-review against the new digest. Mutation and deletion regressions failed before correction and passed afterward.

## FF-034

CSS `image-set()` and `-webkit-image-set()` accepted remote quoted resources without `url()`, including custom-property values. Local quoted resources also bypassed required existence and manifest membership checks. A shared token scan now validates direct image-source strings and existing `url()` values through the established confined local-file policy. It preserves declared local assets, nested MIME strings, gradients and nonfetching content strings. Source-bearing `image()` is checked conservatively; no current-browser fetch through that unsupported feature is claimed. The external, missing and undeclared resource regressions failed before correction and passed afterward.

## FF-035

Resume graph leaf edges pointed toward their consumers, while invalidation traversed dependencies toward dependents. Approvals lacked an evidence dependency. Path deduplication also dropped later coverage and approval consumers of a shared physical file. New snapshots retain one hash with every direct consumer, and consumer nodes depend on their file leaves. Legacy records with incomplete consumer membership now block conservatively and request reviewed refresh; known kind-based stale categories remain reported without replacing stored hashes. Direct, transitive, shared-file, unrelated-file and legacy preservation regressions verify the correction.

## FF-036

An implementer named `alice` could record a passed review as `alice ` and receive final acceptance. Both engine and dashboard compared untrimmed identity strings, although validation only required nonblank trimmed values. Both comparisons now trim surrounding whitespace while preserving case and original record bytes. Fresh-final-approval regressions isolate self-review rejection from unrelated stale digest failures. An authenticated HTTP regression additionally verifies that Produce and Finalize remain pending while Design stays passed.

## Rejected scaffold hypothesis

The fresh audit suspected that `theme_new` failed when the configured themes parent did not exist. A real empty-project invocation created the theme and passed `check_theme`. `shutil.copytree` already creates the needed parent path. No product change was justified.

## FF-037

Quoted `/*` and `*/` markers caused quote-unaware comment removal to erase an active remote `url()` declaration from validation. Actual Chromium fetched that resource while the validator passed. Comment recognition now runs alongside complete string recognition and preserves markers inside strings. The resource regression failed before correction and passed afterward. All browser requests were intercepted locally.

## FF-038

The resource tokenizer treated raw newline characters inside quotes as valid string contents. Browser bad-string recovery instead resumed parsing and fetched a subsequent remote background declaration. The conservative lexer now rejects bad or unterminated strings and comments before resource scanning. Newline, carriage-return and form-feed regressions failed before correction and passed afterward. This deliberately rejects malformed CSS rather than attempting browser error recovery.

## FF-039

A quoted resource beginning with a space and `//` passed local classification when the theme supplied a declared local lookalike under a space-named directory. Chromium removed URL-leading whitespace and fetched the remote host. The shared resource helper now rejects surrounding whitespace before fragment, scheme and path checks. Both `url()` and quoted image-set regressions failed before correction and passed afterward. Ordinary explicit local resource candidates remain supported.

## FF-040

The resume writer hashed default context and routing filenames even when a valid run recorded different confined paths. Changing those actual inputs then returned resume PASS without stale nodes. The writer now snapshots the same recorded paths that acceptance validates. Context and routing mutation regressions fail against the old writer and pass with the corrected inventory. Their exact dependent categories are checked, and stored manifest bytes remain unchanged during inspection.

## FF-041

Unquoted fragment URL tokens `url(#/*)` and `url(#*/)` still made comment removal erase an intervening remote resource. CSS tokenization treats those markers as URL contents. The lexer now recognizes complete quoted and unquoted URL tokens before recognizing comments, reusing the same URL shape for resource extraction. The failing regression and actual intercepted Chromium request establish the defect. Original valid fragment references remain supported.

## FF-042

An unknown `env()` inside image-set substituted its quoted remote fallback after static checking. The earlier direct-`var()` guard was too narrow. Direct source positions now admit only the documented static image-producing functions and MIME descriptors, rejecting dynamic substitutions without banning normal gradient/color variables. Standard and prefixed image-set regressions and an actual intercepted browser fetch reproduced the defect.

## FF-043

An unquoted URL ending at CSS EOF bypassed extraction because the scanner required a closing parenthesis. Chromium recovered the unfinished construct and fetched its resource. The conservative checker now rejects residual unfinished functions instead of treating unextracted inputs as safe. The new regression and actual intercepted browser request reproduced the defect. Static local candidates and gradients remain covered by positive tests.
