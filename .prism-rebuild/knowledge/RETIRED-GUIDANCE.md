# Retired or qualified guidance

This file prevents historical examples and oversimplified summaries from becoming implementation defaults. Source IDs and full URLs are in [SOURCES](SOURCES.md). “Retired” applies to the specified claim or recipe, not necessarily the whole work.

| Source / locator | Guidance to retire or qualify | Replacement for this project |
|---|---|---|
| B02 pp410–411 | RC4-SHA presented as adequately secure for ordinary commercial use. | **Do not implement.** P08 prohibits RC4; use current TLS policy/P26 if TLS termination is in scope. |
| B07 pp120–121 | Resource-owner password-grant/proxy recipes. | **Do not implement as current OAuth advice.** P06 prohibits the grant. Studio does not need OAuth merely because an API book discusses it. |
| B02 p294 | MySQL query-cache tuning. | Removed in MySQL 8.0 (P17); this Python local-state design does not require MySQL. |
| B02 pp158,161–165 | Every consecutive style write creates a separate reflow; cycles inherently leak; blanket manual JS micro-optimization. | Measure current engines. Avoid forced read/write layout sequences (P13); track retained reachability (P18). Preserve readable source. |
| B02 p150; B05 pp216–268 | Universal spriting, sharding and draft-HTTP/2-era optimization recipes. | Evaluate actual protocol, cache granularity and workload. Use P10/P11; Chrome removed HTTP/2 server push (P12). SSE is a separate mechanism. |
| B05 p67, pp119–180 | Old TLS round-trip model, radio states and battery/bandwidth figures treated as current. | Retain latency/idle-chatter reasoning; use P09 and measured contemporary environments for numbers. |
| B06 pp38–40,142 | ZooKeeper-based current Kafka operation or a universal two-week default retention. | Kafka 4.0 removed ZooKeeper mode (P19); 4.2 docs specify 168 hours (P20). Neither is a reason to install Kafka here. |
| B06 pp126–135,162 | Broker transactions or a count of received events prove all external work happened once. | Use durable operation identity, distinct required checks and reconciliation. An arbitrary model call is outside a local/broker transaction. |
| B04 pp95–99 | `R + W > N` alone guarantees strong consistency; any smaller vector component proves concurrency. | P23 requires appropriate protocol/quorum assumptions and vector incomparability. Prefer a local transactional authority here. |
| B04 p260 | Keep only the latest N versions without reference constraints. | Never collect a version needed by an approval, pending revision, checkpoint or retained evidence policy. |
| B09 p114 | An opaque cursor inherently returns every changing item exactly once. | Define stable ordering, snapshot/mutation semantics and identity; opaque encoding alone provides neither consistency nor security. |
| B07/B09 error examples | Treat legacy RFC 7807 or human error prose as the only current machine contract. | Use stable domain error codes and channel-specific mapping; P07 supersedes RFC 7807 for HTTP Problem Details. |
| B10 pp48–62 | Short slogans about labels or semantics imply removing accessible names, form labels or document structure. | Separate visual emphasis from semantic correctness. Read the surrounding examples and satisfy P01. |
| B10 pp66–106; U02/U07 | Whitespace, fixed grids, a typography unit or a font count is mandatory for every interface. | Dense expert work has legitimate needs (B10 p69). Use tested tokens, readable hierarchy and zoom/reflow behaviour. |
| U02; C03/C04/C06 | Five users always find a fixed percentage of problems; 7±2 sets a universal menu limit; a single timing value proves engagement. | Treat these as simplified heuristics, not release guarantees. Externalize task memory and test applicable behaviour. P16 qualifies memory-capacity claims. |
| U10; C07 | Recall effects prove first/last gaze order; loosely defined retention/chameleon theories dictate layout; Hick's work dates to the 19th century. | Do not derive mandatory design rules from these accounts. P15 is a 1952 choice-reaction study. Seek a directly applicable primary study for causal claims. |
| U06 | A GUI must be installed and cannot be a web interface; passing contrast proves overall WCAG conformance. | Studio's browser surface is graphical. Evaluate applicable accessibility criteria beyond contrast. |
| U07 dragging checklist | Keyboard-only success establishes SC 2.5.7. | Also verify a single-pointer non-drag alternative; P02 explicitly distinguishes the requirements. |
| U12 accessibility paragraph | Every image needs descriptive alt text. | Appropriate decorative images need empty alt; informative/function images need contextual alternatives (P03). |
| U11/U12 | Product anecdotes, agency outcome percentages or ROI multiples predict this project's results. | Use examples as hypotheses; require methodology and relevant measurement before making quantitative promises. P24 also corrects the acquisition framing in U11. |
| U13 | Treat the unseen article body as reviewed evidence. | Preview-only source; no rule or factual conclusion relies on unseen content. |
| C04 persuasion examples; U10 dwell-time advice | Hide cost, induce scarcity, simulate effort or increase choices merely to hold attention. | Show truthful progress, consequences, alternatives and budget. Optimise informed task completion rather than pressure or dwell time. |
| Broad distributed-systems examples | Resources imply Kafka, microservices, CRDTs, sharding or a new frontend framework are required. | PROJECT chooses a small shared engine, local transactions and rebuildable views. Add complexity only for a demonstrated need. |

Operational prices, model IDs, browser support and host flags are especially time-sensitive. Verify current primary documentation/capabilities before using them. A review date on a web page does not establish that every paragraph was corrected. Keep the exact scope and reason for each override in the source record.
