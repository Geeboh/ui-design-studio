# Source register

Reviewed for the PRISM handoff on 2026-11-25/26. IDs below are the stable references used by [rules.json](rules.json). This register accounts for **all 12 supplied files and all 21 URLs in the two lists**. Additional primary references resolve consequential conflicts; they are not extra mandatory reading.

## Coverage and limitations

The ten supplied PDFs contain 2,385 file pages. Every page was extracted, every document's chapter/section structure was mapped, relevant sections were read deeply, and representative consequential diagrams/pages were visually checked. This is not a claim of exhaustive word-by-word reading, execution of every code example, or validation of every historical assertion. All ten PDFs were readable.

Twenty listed web bodies or index/catalog bodies were publicly retrievable and reviewed. U13 was available only as a preview; unseen claims are not endorsed. Several direct fetches initially failed or extracted menus/related links; later public web retrieval recovered the actual body. Reading an index/catalog does not mean reviewing every linked article. Embedded videos were not reviewed.

**The original PDFs and website extracts are not included in this pack.** Filenames are attachment identifiers, not pack-relative paths. This pack supplies original synthesis and precise locators; implementation normally needs only selected rules and contracts. Do not redistribute books or load their entire text into every task.

## Attached files

| ID | Supplied filename | Verified identity / edition | Coverage and disposition |
|---|---|---|---|
| B01 | `01-You-don-t-know-JS.pdf` | Kyle Simpson, *You Don't Know JS Yet: Get Started*, second edition, January 2020; first release 2020-01-28 (PDF p4). 109 pages. | All four chapters and two appendices mapped. Language/host distinction, identity, modules, closure and references are useful. This is one introductory volume, not the whole series. |
| B02 | `02-Website-Performance-Optimizing-The-Front-End-And-The-Back-End.pdf` | Peter Smith, *Professional Website Performance: Optimizing the Front End and the Back End*, Wiley/Wrox, copyright 2013 (pp5–6). 484 pages. | All 12 chapters and three appendices mapped. Keep measurement, avoiding repeated work and cautious caching. Treat old PHP/MySQL/browser/SSL recipes as historical; see retired guidance. |
| B03 | `03-The-Reactive-Principles-And-Patterns.pdf` | Jonas Bonér with contributors, *The Reactive Principles: Design Principles for Distributed Applications*, version 1.0 (p1). 19 pages. Metadata date 2022-03-02 is not asserted as publication date. | Whole paper read; eight principles and six patterns. Apply responsiveness, bounded work and local consistency without requiring a distributed framework. |
| B04 | `04-System-Design-Interview-An-Insider-s-Guide-by-Alex-Xu-z-lib.org-.pdf` | Alex Xu, *System Design Interview: An Insider's Guide*, second edition; editor Paul Solomon. 269 pages. Cover confirms edition; original publication year not established from supplied opening matter. | All 16 chapters mapped; deep reading of admission, queues, dependencies, versions and recovery. Interview examples and historical scale/price estimates are illustrative. |
| B05 | `05-High-Performance-Browser-Networking.pdf` | Ilya Grigorik, *High-Performance Browser Networking*, O'Reilly; first release 2013-09-09, copyright 2013 (p529). 536 pages. | All 18 chapters mapped. Main narrative ends p416; long index follows. Strong performance reasoning; modern standards override draft HTTP/2, TLS and mobile-era details. |
| B06 | `06-Event-driven-system-Kafka-.pdf` | Ben Stopford, *Designing Event-Driven Systems: Concepts and Patterns for Streaming Services with Apache Kafka*, first edition April 2018; first release 2018-03-28 (p3). 166 pages. | All five parts covered; consistency, projections, idempotency, schemas and external effects examined. Does not justify Kafka for this local tool. |
| B07 | `07-Build-APIs-You-Won-t-Hate.pdf` | Phil Sturgeon, *Build APIs You Won't Hate*, supplied version 2015-08-12; copyright 2013–2015 (p2). 181 pages. | All 13 chapters plus conclusion mapped. Useful contracts/errors/examples. PHP5.4/Laravel4 and password-grant recipes are historical. |
| B08 | `08-DDD.pdf` | Vaughn Vernon, *Domain-Driven Design Distilled*, copyright 2016, first printing May 2016 (p4). 137 pages. | All seven chapters covered. Vocabulary, small consistency boundaries, adapters and atomic state/event persistence are central. This is not Eric Evans's original book. |
| B09 | `09-Designing-Web-APIs_-Building-APIs-That-Developers-Love-PDFDrive-.pdf` | Brenda Jin, Saurabh Sahni and Amir Shevat, *Designing Web APIs: Building APIs That Developers Love*, first edition September 2018; first release 2018-08-28 (p4). 232 pages. | All 11 chapters and worksheets mapped. Consumer tasks, schemas, compatibility and errors are useful; enterprise ecosystem/scale material is conditional. |
| B10 | `10-Refactoring-UI.pdf` | Adam Wathan and Steve Schoger, *Refactoring UI*. 252 pages. Edition/date not stated in the supplied PDF metadata/opening text. | All sections mapped: starting, hierarchy, spacing, text, colour, depth, images, finishing and practice. Primary visual craft reference; qualify labels, semantics, density and unit advice by accessibility and context. |
| F11 | `11-UX-design.txt` | Fourteen supplied UX URLs, U01–U14 below. | Thirteen full bodies/indexes; U13 preview only. The list is an index, not an additional evidence source. |
| F12 | `12-Cognitive-Psychology-in-UX-Design.txt` | Seven supplied cognition URLs, C01–C07 below. | Seven full bodies/indexes/catalogs; linked libraries and videos not exhaustively reviewed. |

PDF locators throughout this pack are **1-based file pages**, not printed page labels. Conversion dates in PDF metadata do not establish newer editions.

## F11: all fourteen UX URLs

| ID | Source | Access / use / qualification |
|---|---|---|
| U01 | [Top 20 key points from Refactoring UI](https://medium.com/design-bootcamp/top-20-key-points-from-refactoring-ui-by-adam-wathan-steve-schoger-d81042ac9802) | Body recovered through public retrieval. Secondary summary; prefer B10 for context and avoid literal interpretation of short slogans. |
| U02 | [UXPlaybook: UI fundamentals](https://uxplaybook.org/articles/ui-fundamentals-best-practices-for-ux-designers) | Full 11-section body reviewed. Talia Hartwell; published 2024-10-10, labelled updated 2026. Useful overview; qualify fixed counts, trend claims and five-user percentages. |
| U03 | [Boagworld: User interface design](https://boagworld.com/design/user-interface-design/) | Full body reviewed. Experience-based principles; use for practical critique, not a universal quantitative guarantee. |
| U04 | [NN/g: Visual Design in UX Study Guide](https://www.nngroup.com/articles/visual-design-in-ux-study-guide/) | Full index reviewed. Useful navigation across hierarchy, colour, typography and visual perception; individual linked studies require separate retrieval. |
| U05 | [Adham Dannaway: UI design tips](https://www.adhamdannaway.com/blog/ui-design/ui-design-tips) | Body recovered through public retrieval. Useful concrete visual craft; evaluate density, semantics and accessibility in the actual product. |
| U06 | [LogRocket: Essential GUI design principles](https://blog.logrocket.com/ux-design/essential-gui-design-principles/) | Full body reviewed. Eric Chung, updated 2026-07-21. Keep consistency and feedback; reject GUI-versus-web taxonomy error and contrast-only conformance inference. |
| U07 | [Netguru: UI design checklist with tests](https://www.netguru.com/blog/best-practices-ui-web-design) | Full body reviewed. Kacper Rafalski, updated 2026-11-03. Strong testable checklist; correct the keyboard-only check for dragging and qualify prescriptive grids/libraries. |
| U08 | [MockFlow: UI design principles](https://mockflow.com/blog/ui-design-principles) | Full body reviewed. Introductory checklist; deduplicate recurring hierarchy, feedback, consistency and accessibility advice. |
| U09 | [User-friendly interface best practices](https://medium.com/@uidesign0005/best-practices-for-designing-user-friendly-interfaces-for-ui-ux-designers-0b761c85ce48) | Body recovered through public retrieval. Generic secondary guidance; low incremental authority beyond stronger sources. |
| U10 | [UX Magazine: Five cognitive psychology theories](https://uxmag.com/articles/5-cognitive-psychology-theories-that-contribute-to-the-quality-of-ux-design) | Full five-section body recovered. Dorian Martin, 2021-01-15. Low authority: historical error about Hick, recall/gaze conflation and weak theoretical translations. |
| U11 | [Eleken: 40 good UX examples](https://www.eleken.co/blog-posts/good-ux-examples) | Full catalogue body reviewed. Sophia Andrus, updated 2026-03-10. Pattern inspiration; agency outcomes and product anecdotes are not causal proof or live-product certification. |
| U12 | [Gluestack: Interface design for websites](https://market.gluestack.io/blog/interface-design-for-websites) | Full body reviewed. Suraj Ahmed, 2025-12-26. Useful template screening; vendor claims, ROI figures, mobile absolutes and all-images-alt guidance require qualification. |
| U13 | [UXPlanet: Why modern UI sucks and how to fix it](https://uxplanet.org/ui-design-why-modern-ui-sucks-and-how-to-fix-it-303a578a31e7) | **Preview only.** Treat as an unverified viewpoint pointer; no rule depends on unseen body content. |
| U14 | [Invisible Design](https://medium.com/the-year-of-the-looking-glass/invisible-design-a0195494a19e) | Body recovered through public retrieval. Useful reflective essay; unobtrusive interaction does not justify hiding cost, state, consent or recovery. |

## F12: all seven cognition URLs

| ID | Source | Access / use / qualification |
|---|---|---|
| C01 | [NN/g: Psychology for UX Study Guide](https://www.nngroup.com/articles/psychology-study-guide/) | Full index read. Tanner Kohler, 2024-01-10; reviewed 2026-08-27. Organize targeted questions; an index is not itself an experiment. |
| C02 | [Cognizant: Cognitive psychology in UX design](https://www.cognizant.com/nl/en/insights/blog/articles/cognitive-psychology-in-ux-design) | Full body read. Ricardo Faria, 2023-04-20. Basic load/memory/attention overview; fewer steps and animation are conditional choices. |
| C03 | [15 cognitive psychology principles](https://medium.com/@miysalk/15-cognitive-psychology-principles-every-ux-designer-should-know-5f207b832515) | Full 15-section body recovered. Misal K, 2025-02-03. Introductory checklist; fixed memory/400ms claims lack sufficient support as universal gates. |
| C04 | [Growth.Design psychology catalogue](https://growth.design/psychology) | Public catalogue body read; 106 labelled biases/principles at review. Mixture of findings, heuristics and incomplete cards. Use as hypotheses; avoid manipulative pressure. |
| C05 | [Boldare: Psychology and UX design](https://www.boldare.com/blog/psychology-and-ux-design/) | Full body read. Sylwia Rapacz and Kateryna Kaida; date unconfirmed. Deliberate decisions and focus are useful; dual-system shorthand and visual-count rules are not laws. |
| C06 | [IxDF: Cognition in UX/UI design](https://ixdf.org/literature/topics/cognition) | Main article and FAQ read; living page labelled updated 2026; videos not watched. Useful cognitive walkthrough. Qualify universal memory counts and untraced effect percentages. |
| C07 | [Ryte: Six ways to use cognitive psychology](https://en.ryte.com/magazine/how-to-apply-cognitive-psychology-to-improve-ux/) | Full body read. Rithesh Raghavan, 2021-10-27. Low authority: weak retention definition, conditioning/attention/priming conflation and fixed layout prescriptions. |

## Primary standards and verification references

These references were used to resolve specific issues. Verify their applicable version when implementing a time-sensitive recommendation. A primary standard governs its stated scope; it does not settle aesthetic preference or every product tradeoff.

| ID | Reference | Scope |
|---|---|---|
| P01 | [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Normative accessibility criteria and levels; exceptions matter. |
| P02 | [W3C: Dragging movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html) | Single-pointer alternative is separate from keyboard access. |
| P03 | [W3C: Decorative images](https://www.w3.org/WAI/tutorials/images/decorative/) | Empty alt for appropriate decorative images. |
| P04 | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) | HTTP semantics, preconditions and retry/idempotence boundaries. |
| P05 | [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) | HTTP cache semantics, private/authenticated responses. |
| P06 | [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) | OAuth security BCP; password grant prohibited. |
| P07 | [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) | HTTP Problem Details; supersedes RFC 7807. |
| P08 | [RFC 7465](https://www.rfc-editor.org/rfc/rfc7465.html) | RC4 prohibited in TLS. |
| P09 | [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html) | TLS 1.3 and early-data replay caveats. |
| P10 | [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html) | Finalized HTTP/2 semantics. |
| P11 | [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html) | HTTP/3 over QUIC. |
| P12 | [Chrome: Removing HTTP/2 server push](https://developer.chrome.com/blog/removing-push) | Default disabled in Chrome 106; distinct from SSE. |
| P13 | [Chrome: Forced reflow](https://developer.chrome.com/docs/performance/insights/forced-reflow) | Avoid forced layouts from interleaved reads and writes. |
| P14 | [Web Vitals thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds) | Field percentile targets; not equivalent to local synthetic results. |
| P15 | [Hick, 1952: On the Rate of Gain of Information](https://journals.sagepub.com/doi/10.1080/17470215208416600) | Original choice-reaction-time research; not a 19th-century discovery. Publisher abstract/search record retrieved; direct page later timed out. |
| P16 | [Cowan, 2001: Short-term memory capacity](https://pubmed.ncbi.nlm.nih.gov/11515286/) | Research qualifications around memory capacity; no fixed universal menu limit. |
| P17 | [MySQL 8.0 changes](https://dev.mysql.com/doc/refman/8.0/en/mysql-nutshell.html) | Query cache removed. |
| P18 | [V8: Trash talk](https://v8.dev/blog/trash-talk) | Modern reachability/tracing garbage collection. |
| P19 | [Kafka 4.0 upgrade guide](https://kafka.apache.org/40/getting-started/upgrade/) | ZooKeeper mode removal and upgrade limitations. |
| P20 | [Kafka 4.2 broker configuration](https://kafka.apache.org/42/configuration/broker-configs/) | Version-specific defaults, including 168-hour retention. |
| P21 | [SQLite isolation](https://www.sqlite.org/isolation.html) | Transaction/writer visibility semantics. |
| P22 | [SQLite WAL](https://www.sqlite.org/wal.html) | Same-host requirement; no network-filesystem WAL design. |
| P23 | [Dynamo, SOSP 2007](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) | Causal versioning/sloppy quorum qualifications, sections 4.4–4.6. |
| P24 | [Adobe/Figma termination announcement](https://news.adobe.com/news/news-details/2023/adobe-and-figma-mutually-agree-to-terminate-merger-agreement) | Merger terminated 2023-12-18; qualifies U11's acquisition framing. |
| P25 | [HTML: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html) | EventSource constructor, reconnection and credentials behaviour. |
| P26 | [RFC 9325](https://www.rfc-editor.org/rfc/rfc9325.html) | Modern TLS deployment BCP; historical cipher snippets are not current policy. |
| PROJECT | [Pack conventions](../PACK-CONVENTIONS.md) and [product specification](../docs/PRODUCT-AND-UX.md) | User/project decisions: design-only budget, modes, model precedence, local architecture, evidence and deferred human research. These are policy, not research findings. |

## Updating the register

Keep the supplied URL and attachment identity stable. Add retrieval date, changed title/version and disposition when revisiting a source. Mark unavailable content honestly. Retiring an operational recipe does not erase its provenance. A new source should improve a concrete decision; more duplicated advice is not automatically better context.
