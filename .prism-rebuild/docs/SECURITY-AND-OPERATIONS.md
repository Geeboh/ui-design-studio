# Security and operations

## Supported operating model

PRISM Studio retains a local Python engine, local MCP/CLI adapters and an authenticated browser dashboard. The proposed state store is a transactional SQLite database on a documented local single-host path, with immutable artifact blobs, durable operation receipts and portable exports. These are proposed implementation requirements, not claims that this handoff has migrated or secured an existing installation.

Preserve the baseline's useful protections: authenticated access, capability-token handling, host/origin checks, escaping/CSP, path containment, owned-resource cleanup, transactional installer restore and actual model reporting. Refactoring a boundary must retain its positive and adversarial acceptance cases. [REQ-SECURITY](../contracts/requirements.json), [M7/G7](../contracts/gates.json) and the migration/dispatch cases define the minimum release evidence.

| Asset or boundary | Required protection | Recovery/diagnostic evidence |
|---|---|---|
| Project instructions and source | Explicit root, scoped path ownership, applicable instruction snapshots | Planned writes, conflict-aware receipts, no unrelated mutation |
| Run decisions and criteria | Expected revisions, dependency-scoped approval, real actor identity | Decision history, stale reasons, coherent terminal state |
| Design money and provider work | Exact ledger, atomic reservations, idempotency and uncertain-outcome reconciliation | Operation/provider receipts, pending liability, verified settlement/refund |
| Artifacts and annotations | Content identity, validated geometry, bounded input, safe rendering | Digests, pinned bases, immutable lineage, integrity failures |
| Credentials and capability links | Scoped authority, expiry/revocation, private storage and redaction | Redacted access failures, rotation/revocation receipts |
| State and backups | Supported local storage, qualified SQLite runtime, consistent backup and rollback | Runtime/journal policy, integrity checks, restored fixture evidence |
| Distribution and evidence | Complete manifests, private-data exclusion, source/plan/artifact binding | Archive scans, installed-artifact tests, exact hashes |

## Authentication, capabilities and request boundaries

Authenticate protected dashboard HTML, APIs, previews, blobs, exports and thumbnails. Check every route, including alternate encodings and error/redirect paths. A public bootstrap shell may exist only if it exposes no protected project data or authority. Credentials for one project/session cannot retrieve another's content.

Represent read, annotate, decide and execute authority separately where needed, with explicit project/run/component scope and expiry/revocation. Intersect host, session, project and task grants in the shared domain handler. A role name, ability to read files, YOLO mode or retrieved document does not grant write/publication authority. Recheck current authorization before replaying a command; previously recorded outcomes may be retrievable only under the documented result-access policy. A revoked token must not create new effects.

For browser mutations, preserve the explicit host/origin and CSRF boundary in addition to authentication. Test same-origin success, cross-site rejection, missing/forged Origin, unexpected Host, malformed content and redirect behavior. The implementation must document its accepted browser and nonbrowser request shapes rather than adding blanket CORS permissions. A rejected request leaves no decision, reservation or command effect.

Do not introduce remote OAuth merely because an API book describes it. If a future integration requires OAuth, use current standards and the provider's current flow. The password-grant examples in the 2015 source are obsolete: [RFC 9700 §2.4](https://www.rfc-editor.org/rfc/rfc9700.html#name-resource-owner-password-crede) prohibits that grant. This is a source correction, not a requirement to add a new authentication subsystem to the local product.

## Untrusted rendering and resource input

Treat feedback, titles, filenames, annotations, source catalogs, imported documents and generated artwork as untrusted data. Prefer safe text insertion. Where markup is deliberately supported, use an explicit allowed format/sanitization policy and appropriate content type. Preserve CSP and other relevant response protections; test errors and alternate preview routes as well as the main view.

SVG and other active formats require a deliberate isolation or sanitization design. Do not insert arbitrary SVG into the authenticated document's live DOM merely to make previewing convenient. Test script elements, event handlers, external references, unsafe URL schemes and hostile markup in every user-controlled surface. Verify behavior in the required real browser engines. Legitimate content should either render safely or produce a useful format error.

Validate bounded payload sizes, finite coordinates, image-relative geometry and resource counts before expensive processing. The annotation client and server share the same stored contract. Raw input sampling may be denser than the stored representation, but reduction must preserve intended endpoints and never silently change the referenced artifact.

Imported knowledge remains reference data. Instructions embedded in a source cannot override user, system or project authority. Retrieval status and source version are recorded honestly; unavailable content is not reported as read. Distribution includes original distilled rules with provenance, not the uploaded source books or copied chapters.

## Filesystem and process boundaries

Resolve a target project explicitly. Support intended non-Git roots and paths with spaces. Validate read/write/import/export paths against their allowed roots and operations; defend against traversal, absolute-path escape, symlink escape and unsafe archive members. Recheck at the point of use where a path race could matter. A worker's allowed new file path need not exist yet, but its creation still needs explicit ownership within the project boundary.

Execute argument arrays without shell evaluation. Treat filenames and artifact content as data even when they contain spaces, quotes or shell metacharacters. Do not put bearer tokens into command-line arguments or echoed tool logs. A test harness for an expected application error should assert that error and itself return success; a failing process must not be treated as a successful release gate.

Installer and theme restore operations compare affected current content/modes against their receipts before replacing anything. Later user changes cause a conflict that preserves both versions. Do not reset, stash, clean or recursively delete the original checkout as part of preparation or recovery. Keep package installation restore, theme activation rollback and application source rollback as different procedures.

Owned-server cleanup verifies instance identity and authority before stopping a process. A reused port or PID is not proof of ownership. If identity cannot be established, report the situation rather than killing an unrelated process. Test stale discovery files, exited/restarted child processes, port reuse and duplicate launch attempts.

## Loopback, LAN and discovery

The reviewed 1.4.3 documentation describes trusted-LAN binding by default with an explicit loopback-only option. Do not rewrite that history. The proposed v2 policy changes **new installations** to loopback unless LAN exposure is deliberately configured. Migration preserves and surfaces explicit existing LAN configuration; any changed default or effective exposure needs a visible compatibility decision.

Loopback-only startup must not call or require network-interface enumeration. Its operation must survive environments where `psutil.net_if_addrs` is unavailable or forbidden. A failure to discover LAN interfaces should not disable a valid loopback endpoint.

For deliberate LAN use, advertise only actual configured/discovered addresses and the bound port after verifying the owned server's identity. Missing/unreachable interfaces yield an unavailable status, not a fabricated address, example QR or silent wider bind. Generate QR codes locally and keep capability-bearing addresses private. Authentication does not encrypt HTTP traffic; untrusted-network use requires an explicitly supported protected transport/tunnel policy, not a reassuring badge.

Record the effective bind policy and why it was selected. Test loopback-only, zero/one/multiple-interface LAN, dynamic port, child restart, discovery failure and owned stop behavior. A physical second-device LAN check is reported only if actually performed. It is not a universal native-platform blocker for a loopback-supported web release; the exact advertised LAN support claim must match its evidence.

## Durable state and the SQLite runtime

Use a documented local single-host state directory. SQLite's [WAL documentation](https://www.sqlite.org/wal.html) states that ordinary WAL operation relies on same-host shared memory and does not work over a network filesystem. A known network-mounted path is not silently accepted for the proposed policy. Unknown storage characteristics produce a specific configuration question or a documented supported selection, not a guess.

Inspect the linked SQLite library actually used by the Python runtime: record `sqlite3.sqlite_version` and `sqlite_source_id()`, plus attributable vendor patch information where relevant. The [3.51.3 release record](https://www.sqlite.org/releaselog/3_51_3.html) confirms the WAL-reset fix and its source identity; the [WAL-reset section](https://www.sqlite.org/wal.html#walreset) also identifies fixed backports 3.44.6 and 3.50.7. A supported Python version alone does not establish that fix. Recheck this policy against current upstream/vendor information when implementing and releasing.

Enable multi-connection WAL only when the fix is established. If unavailable, either block that mode with a precise reason or explicitly select a qualified alternate policy, such as `journal_mode=DELETE`, `synchronous=FULL` and serialized writes. The alternate requires the same invariant, concurrency, reopen/crash and backup tests and measured performance appropriate to its target. It is not a silent fallback and does not require installing system packages without authorization.

Keep transactions small and bounded, use integrity constraints, enforce expected revisions within writes and handle busy/permission/disk-full errors without partial side effects. WAL's reader/writer advantages do not mean arbitrary concurrent writers or automatic application correctness. Journal/synchronous/checkpoint policy and durability assumptions are explicit configuration facts, not undocumented performance tweaks.

Use the supported [online backup API](https://www.sqlite.org/backup.html) or a verified quiesced/export procedure to obtain a consistent backup. WAL is part of persistent state; copying the live main database alone can omit committed transactions. Restore into a separate location, verify database and blob integrity, then activate through a receipt. Never delete journal/lock files as a generic response to a busy error.

## Paid work, cancellation and recovery

Use durable operation identity, canonical request hash, expected revisions and atomic reservation before controlled paid dispatch. A repeated identical request returns its recorded outcome; reusing the key for different semantics is rejected. This application mechanism complements the distinction between idempotent and non-idempotent HTTP requests in [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods). Retry/backoff alone is insufficient to prevent duplicate charges.

When a provider outcome is unknown, retain pending liability and reconcile the original operation. Do not release its reservation merely because a browser disconnected, a worker lease expired, a timeout fired or the user clicked Cancel. Cancellation before dispatch can release an unspent reservation; cancellation after dispatch needs provider/charge evidence. Refunds are separate verified ledger entries linked to the original charge.

On restart, recover committed outbox intent and leases from durable state. Deduplicate delivery and receipts, but do not claim universal exactly-once execution for an uncontrolled external provider. If a charge exceeds its promised bound, retain the real amount, flag the discrepancy and stop misleading hard-cap claims. Never truncate accounting to make the UI total fit.

The budget applies to design work. Build/implementation expenditure is tracked separately and excluded by default. Current-model routing, host permissions and scoped revision policy still apply under recovery or fallback. A cheaper model is not a valid substitute if it lacks required visual/technical capability or violates explicit current-model mode.

## Logs, support bundles and retention

Use synthetic canaries to test redaction of capability URLs, bearer tokens, headers, provider errors, filenames and private paths. Redaction applies to exceptions, process output, browser traces, screenshots, exports and release evidence—not only normal request logs. Store credentials and state with appropriate local access restrictions and document platform limitations honestly.

Operational logs need enough information to correlate a stable operation, error code, scope and revision without exposing secret values or unnecessary project content. Keep human-readable detail separate from machine codes; current HTTP Problem Details guidance is [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html). A common domain error can have different HTTP/MCP/CLI representations while retaining the same meaning.

Support export is explicit and redacted. No external analytics, session recording, cloud QR service or automatic resource upload is introduced merely because a reference suggests it. Retention policy names what is kept, for how long, and why: pending financial reconciliation, active migration/restore evidence and retained approvals must not be deleted by generic cache cleanup. Cache eviction cannot remove authoritative state or accepted artifact bytes.

## Operational runbooks to implement and verify

| Event | Required first response | Recovery proof |
|---|---|---|
| Database busy or permission failure | Return bounded actionable failure; preserve transaction and original state | Successful reopen/integrity check and no partial command effect |
| Corrupt/missing artifact | Reject reliance on its identity; isolate affected scope | Verified replacement/import under a new identity and explicit re-review where needed |
| Unknown provider outcome | Keep original operation and reservation pending | Attributable receipt/reconciliation, one settlement, no duplicate dispatch |
| Interrupted migration/activation | Inspect migration receipt and exact original/candidate state | Resume or conflict-safe rollback with byte/count/digest checks |
| Failed install/theme upgrade | Follow recorded changed-file set and backups | Restore only expected bytes/modes; stop on later-edit conflicts |
| Expired/revoked capability | Deny new effects; preserve safe local draft/context | New authorized session or documented result-access policy; no automatic hidden replay |
| Stale discovery/reused port | Verify owned instance before action | Correct observed endpoint or truthful unavailable state; unrelated process untouched |
| Gate source change/missing evidence | Mark stale/blocked, retain diagnostic receipt | Re-establish candidate/plan and rerun relevant real checks |

Each runbook is exercised in a disposable fixture before release. Operator documentation states exact supported commands after implementation; this handoff does not invent unimplemented recovery CLI flags. For a genuine environment blocker, preserve a resumable record with the failed operation, affected acceptance IDs, actual error and safe alternatives tried. Complete independent authorized work before requesting any missing external action.
