"use strict";

(() => {
  const POLL_INTERVAL = 2000;
  const STALE_AFTER = 10000;
  const PAGE_SIZE = 12;
  const DOCUMENT_WIDTH = 1440;
  const DOCUMENT_HEIGHT = 900;
  const baseUrl = new URL(".", window.location.href);
  const byId = (id) => document.getElementById(id);
  const numberFormat = new Intl.NumberFormat();
  const state = {
    token: new URLSearchParams(window.location.hash.slice(1)).get("token") || "",
    snapshot: null,
    artworks: [],
    artworkById: new Map(),
    view: "progress",
    libraryPage: 1,
    feedPage: 1,
    decisionPage: 1,
    lastSuccess: 0,
    failure: null,
    inFlight: false,
    refreshQueued: false,
    pollTimer: null,
    requestController: null,
    stopped: false,
    approvalViews: new Map(),
    viewer: null,
    historyKey: null,
    decisionKey: null,
  };
  const previewJobs = new Map();
  const gridKeys = new WeakMap();
  let approvalSequence = 0;
  const previewObserver = typeof IntersectionObserver === "function"
    ? new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          previewObserver.unobserve(entry.target);
          loadPreview(entry.target);
        }
      }
    }, { rootMargin: "150px" })
    : null;
  const previewResize = typeof ResizeObserver === "function"
    ? new ResizeObserver((entries) => {
      for (const entry of entries) scaleThumbnail(entry.target);
    })
    : null;
  const viewerResize = typeof ResizeObserver === "function"
    ? new ResizeObserver(() => {
      if (state.viewer?.mode === "fit") applyViewerScale();
    })
    : null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function badge(status, label = status) {
    const node = element("span", "status-badge", label);
    node.dataset.state = status;
    return node;
  }

  function showTime(node, value) {
    node.dateTime = value;
    node.textContent = formatTime(value);
    node.title = value;
  }

  function formatTime(value) {
    return new Date(value).toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  }

  function formatElapsed(seconds) {
    const whole = Math.floor(seconds);
    const hours = Math.floor(whole / 3600);
    const minutes = Math.floor((whole % 3600) / 60);
    const remainder = whole % 60;
    if (hours) return `${numberFormat.format(hours)}h ${minutes}m ${remainder}s`;
    if (minutes) return `${minutes}m ${remainder}s`;
    return `${remainder}s`;
  }

  function requireValue(condition, message) {
    if (!condition) throw new Error(`Invalid snapshot. ${message}`);
  }

  function validateSnapshot(data) {
    const record = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
    const text = (value) => typeof value === "string";
    const count = (value) => Number.isSafeInteger(value) && value >= 0;
    const date = (value) => text(value) && Number.isFinite(Date.parse(value));
    const strings = (value) => Array.isArray(value) && value.every(text);
    requireValue(record(data) && data.schemaVersion === "1.0", "Expected schema version 1.0.");
    requireValue(text(data.revision) && date(data.observedAt), "Revision or observation time is missing.");
    requireValue(record(data.run) && ["id", "themeId", "mode", "phase", "status"].every((key) => text(data.run[key])), "Run fields are missing.");
    requireValue(record(data.server) && text(data.server.url) && date(data.server.startedAt), "Server fields are missing.");
    requireValue(Array.isArray(data.gates) && data.gates.every((gate) => record(gate) && text(gate.id) && text(gate.label) && text(gate.detail) && ["passed", "pending", "failed"].includes(gate.status)), "Gate records are invalid.");
    requireValue(record(data.coverage) && ["required", "mockups", "verified"].every((key) => count(data.coverage[key])) && typeof data.coverage.inventoryComplete === "boolean", "Coverage counts are invalid.");
    requireValue(text(data.nextAction) && strings(data.blockers) && strings(data.warnings), "Progress messages are invalid.");
    requireValue(Array.isArray(data.workers) && data.workers.every((worker) => record(worker) && ["id", "task", "status", "message"].every((key) => text(worker[key])) && date(worker.updatedAt) && (worker.model === undefined || text(worker.model))), "Worker records are invalid.");
    requireValue(Array.isArray(data.tasks) && data.tasks.every((task) => record(task) && ["id", "title", "status"].every((key) => text(task[key])) && (task.progress === undefined || (typeof task.progress === "number" && Number.isFinite(task.progress) && task.progress >= 0 && task.progress <= 100)) && (task.nextAction === undefined || text(task.nextAction))), "Task records are invalid.");
    requireValue(record(data.statistics) && ["artworks", "workers", "tasks", "evidence", "passedEvidence"].every((key) => count(data.statistics[key])) && typeof data.statistics.elapsedSeconds === "number" && Number.isFinite(data.statistics.elapsedSeconds) && data.statistics.elapsedSeconds >= 0, "Statistics are invalid.");
    requireValue(Array.isArray(data.history) && data.history.every((point) => record(point) && date(point.at) && ["verified", "required", "passedGates"].every((key) => count(point[key]))), "History records are invalid.");
    requireValue(Array.isArray(data.artworks) && data.artworks.every((artwork) => record(artwork) && ["id", "path", "title", "context", "version", "url"].every((key) => text(artwork[key])) && ["image", "html", "pdf"].includes(artwork.kind) && date(artwork.createdAt)), "Artwork records are invalid.");
    requireValue(new Set(data.artworks.map((artwork) => artwork.id)).size === data.artworks.length, "Artwork IDs must identify unique retained versions.");
    requireValue(Array.isArray(data.approvals) && data.approvals.every((request) => record(request) && ["id", "title", "context", "inputsDigest"].every((key) => text(request[key])) && ["plan", "design"].includes(request.stage) && strings(request.inputs) && ["pending", "approved", "rejected", "stale"].includes(request.status) && Array.isArray(request.options) && request.options.every((option) => record(option) && text(option.id) && text(option.label) && strings(option.artworkIds)) && new Set(request.options.map((option) => option.id)).size === request.options.length), "Approval requests are invalid.");
    requireValue(new Set(data.approvals.map((request) => request.id)).size === data.approvals.length, "Approval request IDs are duplicated.");
    requireValue(data.decisions === undefined || (Array.isArray(data.decisions) && data.decisions.every((decision) => record(decision) && ["stage", "actor", "outcome", "rationale"].every((key) => text(decision[key])) && ["recordedAt", "optionId", "inputsDigest"].every((key) => decision[key] === undefined || text(decision[key])))), "Recorded decisions are invalid.");
    return data;
  }

  function artifactUrl(artwork) {
    const url = new URL(artwork.url, baseUrl);
    if (url.origin !== window.location.origin || !["http:", "https:"].includes(url.protocol) || url.username || url.password) {
      throw new Error("The artifact URL is not a local preview capability.");
    }
    const previewRoot = new URL("preview/", baseUrl).pathname;
    if (!url.pathname.startsWith(previewRoot)) {
      throw new Error("The artifact URL is outside the preview library.");
    }
    return artwork.url;
  }

  function snapshotFresh() {
    return Boolean(state.snapshot && state.token && !state.failure && navigator.onLine !== false && performance.now() - state.lastSuccess < STALE_AFTER);
  }

  function updateConnection() {
    const status = byId("connection-status");
    const notice = byId("connection-notice");
    let kind = "connected";
    let label = "Connected";
    let message = "";
    if (!state.token) {
      kind = "unauthorized";
      label = "Token missing";
      message = "Open the complete private server address, including #token= in the fragment. Authenticated updates and approval submissions are paused. Existing drafts are retained.";
    } else if (navigator.onLine === false) {
      kind = "offline";
      label = "Offline";
      message = state.snapshot
        ? "The browser reports that it is offline. Displayed records are the last received snapshot. Approval drafts are retained."
        : "The browser reports that it is offline. No run snapshot has been received. Approval submissions are unavailable.";
    } else if (state.failure) {
      kind = state.failure.kind;
      label = kind === "unauthorized" ? "Access denied" : "Connection error";
      message = `${state.failure.message} ${state.snapshot ? "Displayed records may be stale. Approval drafts are retained." : "No valid run snapshot is available."}`;
    } else if (!state.snapshot) {
      kind = "loading";
      label = "Connecting";
      message = "Connecting to the design server. No run records have been loaded.";
    } else if (!snapshotFresh()) {
      kind = "stale";
      label = "Stale snapshot";
      message = "No fresh snapshot has been received for more than 10 seconds. Approval submissions are paused; drafts are retained.";
    }
    status.dataset.state = kind;
    if (status.textContent !== label) status.textContent = label;
    notice.hidden = !message;
    notice.dataset.state = kind;
    if (notice.textContent !== message) notice.textContent = message;
    byId("refresh-snapshot").disabled = state.inFlight || !state.token;
    byId("refresh-snapshot").textContent = state.inFlight ? "Refreshing" : "Refresh";
    byId("snapshot-age").textContent = state.snapshot
      ? `Observed ${formatTime(state.snapshot.observedAt)} · received ${formatElapsed(Math.max(0, (performance.now() - state.lastSuccess) / 1000))} ago · revision ${state.snapshot.revision}`
      : "No snapshot received.";
    for (const view of state.approvalViews.values()) updateApprovalAvailability(view);
  }

  async function responseError(response) {
    let detail = "";
    try {
      const body = await response.json();
      if (typeof body.error === "string") detail = body.error;
      else if (typeof body.message === "string") detail = body.message;
    } catch {
      detail = "";
    }
    return detail || `The server returned HTTP ${response.status}.`;
  }

  async function refreshSnapshot() {
    if (state.stopped) return;
    if (state.inFlight) {
      state.refreshQueued = true;
      return;
    }
    clearTimeout(state.pollTimer);
    if (!state.token || navigator.onLine === false) {
      updateConnection();
      state.pollTimer = setTimeout(refreshSnapshot, POLL_INTERVAL);
      return;
    }
    state.inFlight = true;
    const token = state.token;
    const controller = new AbortController();
    state.requestController = controller;
    const deadline = setTimeout(() => controller.abort(), 12000);
    updateConnection();
    try {
      const response = await fetch(new URL("api/snapshot", baseUrl), {
        headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
        cache: "no-store", credentials: "omit", redirect: "error", signal: controller.signal,
      });
      if (!response.ok) {
        const error = new Error(await responseError(response));
        error.kind = [401, 403].includes(response.status) ? "unauthorized" : "error";
        throw error;
      }
      const snapshot = validateSnapshot(await response.json());
      if (state.stopped || token !== state.token) return;
      state.snapshot = snapshot;
      // Preserve publication order without truncating submillisecond version timestamps.
      state.artworks = snapshot.artworks.slice().reverse();
      state.artworkById = new Map(state.artworks.map((artwork) => [artwork.id, artwork]));
      state.lastSuccess = performance.now();
      state.failure = null;
      renderSnapshot();
    } catch (error) {
      if (!state.stopped && token === state.token) {
        state.failure = {
          kind: error.kind || "error",
          message: error.name === "AbortError" ? "The snapshot request timed out." : error.message || "The snapshot request failed.",
        };
      }
    } finally {
      clearTimeout(deadline);
      state.inFlight = false;
      state.requestController = null;
      updateConnection();
      const delay = state.refreshQueued ? 0 : POLL_INTERVAL;
      state.refreshQueued = false;
      if (!state.stopped) state.pollTimer = setTimeout(refreshSnapshot, delay);
    }
  }

  function renderSnapshot() {
    const snapshot = state.snapshot;
    if (byId("server-url").textContent !== snapshot.server.url) byId("server-url").textContent = snapshot.server.url;
    byId("run-summary").textContent = `${snapshot.run.themeId} · ${snapshot.run.id}`;
    const mode = snapshot.run.mode === "yolo" ? "Autonomous yolo mode" : snapshot.run.mode === "guided" ? "Guided mode" : "Run mode unverified";
    byId("run-detail").textContent = `Phase ${snapshot.run.phase || "unverified"} · ${mode} · server started ${formatTime(snapshot.server.startedAt)}`;
    byId("run-status").textContent = snapshot.run.status;
    byId("run-status").dataset.state = snapshot.run.status;
    document.title = `${snapshot.run.themeId} · Design workspace`;
    for (const panel of document.querySelectorAll("[data-view-panel]")) panel.setAttribute("aria-busy", "false");
    renderProgress(snapshot);
    renderApprovals(snapshot);
    renderDecisions(snapshot);
    renderActiveGallery();
  }

  function renderMessages(root, messages, emptyText) {
    root.dataset.empty = String(messages.length === 0);
    root.replaceChildren(...(messages.length ? messages.map((message) => element("li", "", message)) : [element("li", "muted", emptyText)]));
  }

  function renderCoverage(id, value, required) {
    const progress = byId(`${id}-progress`);
    progress.hidden = required === 0;
    progress.max = Math.max(1, required);
    progress.value = Math.min(value, required);
    byId(`${id === "mockup" ? "mockup" : "verified"}-count`).textContent = `${numberFormat.format(value)} / ${numberFormat.format(required)} required cases`;
    progress.setAttribute("aria-valuetext", `${numberFormat.format(value)} of ${numberFormat.format(required)} required cases`);
  }

  function renderProgress(snapshot) {
    const coverage = snapshot.coverage;
    renderCoverage("mockup", coverage.mockups, coverage.required);
    renderCoverage("verified", coverage.verified, coverage.required);
    byId("inventory-status").textContent = coverage.inventoryComplete ? "Inventory complete" : "Inventory incomplete";
    const coverageNotes = [];
    if (!coverage.inventoryComplete) coverageNotes.push("Inventory is incomplete; the required case count can change.");
    if (!coverage.required) coverageNotes.push("No required cases are recorded. This does not establish completed coverage.");
    if (coverage.mockups > coverage.required || coverage.verified > coverage.required) coverageNotes.push("A recorded count exceeds the required total. Bars are capped; the counts above are unchanged.");
    coverageNotes.push("Verification requires a mockup, implementation, and fresh passed QA evidence for each required case.");
    byId("coverage-note").textContent = coverageNotes.join(" ");
    const gates = snapshot.gates.map((gate) => {
      const row = element("li");
      row.dataset.gateId = gate.id;
      row.append(element("span", "", gate.label), badge(gate.status), element("p", "gate-detail muted", gate.detail));
      return row;
    });
    byId("gate-list").replaceChildren(...(gates.length ? gates : [element("li", "empty-state", "No gate records are available. No gate is assumed passed.")]));
    byId("gate-count").textContent = `${snapshot.gates.filter((gate) => gate.status === "passed").length} / ${snapshot.gates.length} passed`;
    byId("next-action").textContent = snapshot.nextAction || "No next action has been reported.";
    renderMessages(byId("blocker-list"), snapshot.blockers, "No blockers reported.");
    renderMessages(byId("warning-list"), snapshot.warnings, "No warnings reported.");
    byId("warnings-section").hidden = snapshot.warnings.length === 0;
    for (const node of byId("statistics").querySelectorAll("[data-stat]")) {
      const key = node.dataset.stat;
      node.textContent = key === "elapsedSeconds" ? formatElapsed(snapshot.statistics[key]) : numberFormat.format(snapshot.statistics[key]);
    }
    const workers = snapshot.workers.map((worker) => {
      const item = element("li");
      item.dataset.workerId = worker.id;
      const heading = element("div", "work-item-heading");
      heading.append(element("span", "work-item-title monospace", worker.id), badge(worker.status));
      item.append(heading, element("p", "work-item-task", worker.task));
      if (worker.message) item.append(element("p", "work-item-message muted", worker.message));
      const meta = element("div", "work-item-meta");
      if (worker.model) meta.append(element("span", "", worker.model));
      const time = element("time");
      showTime(time, worker.updatedAt);
      meta.append(element("span", "", "Reported"), time);
      item.append(meta);
      return item;
    });
    byId("worker-list").replaceChildren(...(workers.length ? workers : [element("li", "empty-state", "No worker status has been reported.")]));
    byId("worker-count").textContent = `${numberFormat.format(snapshot.workers.length)} reported`;
    const tasks = snapshot.tasks.map((task) => {
      const item = element("li");
      item.dataset.taskId = task.id;
      const heading = element("div", "work-item-heading");
      heading.append(element("span", "work-item-title", task.title), badge(task.status));
      item.append(heading, element("p", "work-item-meta monospace", task.id));
      if (task.progress !== undefined) {
        const progress = element("progress");
        progress.max = 100;
        progress.value = task.progress;
        progress.setAttribute("aria-label", `${task.title}, reported progress`);
        progress.setAttribute("aria-valuetext", `${task.progress}% reported`);
        item.append(element("p", "work-item-meta", `${task.progress}% reported`), progress);
      }
      if (task.nextAction) item.append(element("p", "work-item-message muted", `Next action: ${task.nextAction}`));
      return item;
    });
    byId("task-list").replaceChildren(...(tasks.length ? tasks : [element("li", "empty-state", "No task records have been published.")]));
    byId("task-count").textContent = `${numberFormat.format(snapshot.tasks.length)} recorded`;
    renderHistory(snapshot.history);
  }

  function svgElement(tag, attributes, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderHistory(history) {
    const key = JSON.stringify(history);
    if (key === state.historyKey) return;
    state.historyKey = key;
    const chart = byId("history-chart");
    const rows = byId("history-rows");
    byId("history-details").hidden = history.length === 0;
    if (!history.length) {
      chart.replaceChildren(element("p", "empty-state", "No progress changes have been recorded yet."));
      byId("history-summary").textContent = "The graph will use recorded changes only.";
      rows.replaceChildren();
      return;
    }
    const points = history.slice().sort((left, right) => Date.parse(left.at) - Date.parse(right.at));
    const start = Date.parse(points[0].at);
    const end = Date.parse(points[points.length - 1].at);
    const maximum = points.reduce((value, point) => Math.max(value, point.required, point.verified), 1);
    const x = (point) => end === start ? 472 : 60 + ((Date.parse(point.at) - start) / (end - start)) * 824;
    const y = (value) => 206 - (value / maximum) * 170;
    const svg = svgElement("svg", { viewBox: "0 0 920 250", role: "img", "aria-labelledby": "history-svg-title history-svg-description" });
    svg.append(svgElement("title", { id: "history-svg-title" }, "Recorded verified and required coverage"));
    svg.append(svgElement("desc", { id: "history-svg-description" }, `${points.length} recorded observations. Exact times, counts, and passed gates are available in the history table.`));
    svg.append(svgElement("line", { x1: 60, x2: 884, y1: 206, y2: 206, class: "history-axis" }));
    svg.append(svgElement("line", { x1: 60, x2: 884, y1: 36, y2: 36, class: "history-axis" }));
    svg.append(svgElement("text", { x: 48, y: 211, "text-anchor": "end", class: "history-label" }, "0"));
    svg.append(svgElement("text", { x: 48, y: 41, "text-anchor": "end", class: "history-label" }, numberFormat.format(maximum)));
    for (const [field, className] of [["required", "history-required"], ["verified", "history-verified"]]) {
      if (points.length > 1) svg.append(svgElement("polyline", { points: points.map((point) => `${x(point)},${y(point[field])}`).join(" "), class: className }));
      for (const point of points) {
        const mark = svgElement("circle", { cx: x(point), cy: y(point[field]), r: field === "verified" ? 3.5 : 2.5, class: field === "verified" ? "history-point" : "history-required" });
        mark.append(svgElement("title", {}, `${formatTime(point.at)} · ${field} ${point[field]}`));
        svg.append(mark);
      }
    }
    svg.append(svgElement("text", { x: end === start ? 472 : 60, y: 236, "text-anchor": end === start ? "middle" : "start", class: "history-label" }, formatTime(points[0].at)));
    if (end !== start) svg.append(svgElement("text", { x: 884, y: 236, "text-anchor": "end", class: "history-label" }, formatTime(points[points.length - 1].at)));
    const legend = element("div", "history-legend");
    legend.append(element("span", "", "Verified cases"), element("span", "", "Required cases"));
    chart.replaceChildren(legend, svg);
    const last = points[points.length - 1];
    byId("history-summary").textContent = `${numberFormat.format(points.length)} recorded observations. Latest: ${last.verified} verified / ${last.required} required cases; ${last.passedGates} passed gates.`;
    rows.replaceChildren(...points.map((point) => {
      const row = element("tr");
      const date = element("td");
      const time = element("time");
      showTime(time, point.at);
      date.append(time);
      row.append(date, element("td", "", numberFormat.format(point.verified)), element("td", "", numberFormat.format(point.required)), element("td", "", numberFormat.format(point.passedGates)));
      return row;
    }));
  }

  function disposeGrid(root) {
    for (const [preview, job] of previewJobs) {
      if (!root.contains(preview)) continue;
      previewObserver?.unobserve(preview);
      previewResize?.unobserve(preview);
      if (job.node) job.node.removeAttribute("src");
      previewJobs.delete(preview);
    }
    root.replaceChildren();
    gridKeys.delete(root);
  }

  function scaleThumbnail(preview) {
    const job = previewJobs.get(preview);
    if (job?.node?.tagName !== "IFRAME") return;
    job.node.style.transform = `scale(${preview.clientWidth / DOCUMENT_WIDTH})`;
  }

  function previewFailure(preview, message) {
    const job = previewJobs.get(preview);
    if (job?.node) job.node.remove();
    preview.replaceChildren(element("span", "preview-error", message));
  }

  function loadPreview(preview) {
    const job = previewJobs.get(preview);
    if (!job || job.node) return;
    let url;
    try {
      url = artifactUrl(job.artwork);
    } catch (error) {
      previewFailure(preview, error.message);
      return;
    }
    const artwork = job.artwork;
    const media = document.createElement(artwork.kind === "image" ? "img" : "iframe");
    job.node = media;
    media.loading = "lazy";
    media.referrerPolicy = "no-referrer";
    if (artwork.kind === "image") {
      media.alt = "";
      media.decoding = "async";
    } else {
      media.className = "preview-frame";
      media.setAttribute("sandbox", "");
      media.setAttribute("inert", "");
      media.setAttribute("aria-hidden", "true");
      media.tabIndex = -1;
      media.title = `${artwork.title}, sandboxed preview with scripts disabled`;
      media.style.width = `${DOCUMENT_WIDTH}px`;
      media.style.height = `${DOCUMENT_HEIGHT}px`;
      previewResize?.observe(preview);
    }
    media.addEventListener("load", () => {
      if (!previewJobs.has(preview)) return;
      preview.querySelector(".preview-loading")?.remove();
    }, { once: true });
    media.addEventListener("error", () => previewFailure(preview, "Preview unavailable. Open the retained version to inspect or save it."), { once: true });
    preview.append(media);
    scaleThumbnail(preview);
    media.src = url;
  }

  function renderGrid(root, artworks, emptyText) {
    const key = JSON.stringify(artworks);
    if (gridKeys.get(root) === key) return;
    const focusedCard = document.activeElement?.closest(".artwork-card");
    const focusedId = focusedCard && root.contains(focusedCard) ? focusedCard.dataset.artworkId : null;
    disposeGrid(root);
    gridKeys.set(root, key);
    if (!artworks.length) {
      root.append(element("p", "empty-state", emptyText));
    }
    for (const artwork of artworks) {
      const fragment = byId("artwork-card-template").content.cloneNode(true);
      const card = fragment.querySelector(".artwork-card");
      card.dataset.artworkId = artwork.id;
      card.dataset.artworkVersion = artwork.version;
      const button = card.querySelector(".artwork-open");
      button.setAttribute("aria-label", `Open ${artwork.title}, ${artwork.kind}, version ${artwork.version}`);
      button.addEventListener("click", () => openArtwork(artwork, button));
      card.querySelector(".artwork-title").textContent = artwork.title;
      card.querySelector(".kind-label").textContent = artwork.kind === "image" ? "Image" : artwork.kind.toUpperCase();
      card.querySelector(".artwork-context").textContent = artwork.context;
      card.querySelector(".artwork-path").textContent = artwork.path;
      card.querySelector(".version-label").textContent = `Version ${artwork.version}`;
      showTime(card.querySelector("time"), artwork.createdAt);
      card.querySelector(".artifact-preview-note").textContent = artwork.kind === "image"
        ? "Select to inspect natural dimensions and zoom."
        : artwork.kind === "html" ? "Static HTML preview. Scripts disabled; script-rendered content needs a screenshot."
          : "Sandboxed PDF preview. Browser support varies; the retained PDF can be saved.";
      const preview = card.querySelector(".artifact-preview");
      previewJobs.set(preview, { artwork, node: null });
      root.append(fragment);
      if (previewObserver) previewObserver.observe(preview);
      else loadPreview(preview);
    }
    if (focusedId) {
      const target = root.querySelector(`[data-artwork-id="${CSS.escape(focusedId)}"] .artwork-open`) || byId(`nav-${state.view}`);
      target.focus({ preventScroll: true });
    }
  }

  function renderActiveGallery() {
    if (!state.snapshot) return;
    if (state.view === "feed") {
      const pageCount = Math.ceil(state.artworks.length / PAGE_SIZE);
      state.feedPage = Math.max(1, Math.min(state.feedPage, pageCount || 1));
      const start = (state.feedPage - 1) * PAGE_SIZE;
      const feed = state.artworks.slice(start, start + PAGE_SIZE);
      byId("feed-summary").textContent = feed.length
        ? `Versions ${numberFormat.format(start + 1)} to ${numberFormat.format(start + feed.length)} of ${numberFormat.format(state.artworks.length)}, newest first. Every retained version is available in the library.`
        : "No visual artifacts have been discovered in this run yet.";
      byId("feed-page").textContent = pageCount ? `Page ${state.feedPage} of ${pageCount}` : "No retained versions";
      byId("feed-previous").disabled = state.feedPage <= 1;
      byId("feed-next").disabled = state.feedPage >= pageCount;
      renderGrid(byId("feed-grid"), feed, "No visual artifacts have been discovered yet. New artwork will appear automatically.");
    }
    if (state.view === "library") renderLibrary();
  }

  function filteredArtworks() {
    const search = byId("library-search").value.trim().toLocaleLowerCase();
    const kind = byId("library-kind").value;
    const versions = byId("library-versions").value;
    let artworks = state.artworks;
    if (versions === "latest") {
      const paths = new Set();
      artworks = artworks.filter((artwork) => {
        if (paths.has(artwork.path)) return false;
        paths.add(artwork.path);
        return true;
      });
    }
    artworks = artworks.filter((artwork) => (kind === "all" || artwork.kind === kind) && (!search || [artwork.title, artwork.context, artwork.path, artwork.version, artwork.kind].some((value) => value.toLocaleLowerCase().includes(search))));
    if (byId("library-sort").value === "oldest") artworks = artworks.slice().reverse();
    if (byId("library-sort").value === "title") artworks = artworks.slice().sort((left, right) => left.title.localeCompare(right.title));
    return artworks;
  }

  function renderLibrary() {
    const artworks = filteredArtworks();
    const pageCount = Math.ceil(artworks.length / PAGE_SIZE);
    state.libraryPage = Math.max(1, Math.min(state.libraryPage, pageCount || 1));
    const start = (state.libraryPage - 1) * PAGE_SIZE;
    const current = artworks.slice(start, start + PAGE_SIZE);
    byId("library-summary").textContent = `${numberFormat.format(artworks.length)} matching versions · ${numberFormat.format(state.artworks.length)} total retained versions${artworks.length ? ` · showing ${numberFormat.format(start + 1)} to ${numberFormat.format(start + current.length)}` : ""}`;
    byId("library-page").textContent = pageCount ? `Page ${state.libraryPage} of ${pageCount}` : "No matching versions";
    byId("library-previous").disabled = state.libraryPage <= 1;
    byId("library-next").disabled = state.libraryPage >= pageCount;
    renderGrid(byId("library-grid"), current, state.artworks.length ? "No artwork matches these filters. Clear the filters to see all retained versions." : "No visual artifacts have been discovered in this run yet.");
  }

  function setView(view, focus = true) {
    if (!["progress", "feed", "library", "approvals"].includes(view)) return;
    if (state.view !== view) {
      if (state.view === "feed") disposeGrid(byId("feed-grid"));
      if (state.view === "library") disposeGrid(byId("library-grid"));
    }
    state.view = view;
    for (const button of document.querySelectorAll("[data-view]")) {
      if (button.dataset.view === view) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    }
    for (const panel of document.querySelectorAll("[data-view-panel]")) panel.hidden = panel.dataset.viewPanel !== view;
    renderActiveGallery();
    if (focus) {
      byId(`${view}-heading`).focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "instant" });
    }
  }

  function createApprovalView(request) {
    const prefix = `approval-${++approvalSequence}`;
    const card = element("article", "approval-card");
    card.dataset.approvalId = request.id;
    const header = element("header");
    const heading = element("div");
    const stage = element("p", "approval-stage");
    const title = element("h3");
    title.id = `${prefix}-title`;
    title.tabIndex = -1;
    heading.append(stage, title);
    const status = badge(request.status);
    header.append(heading, status);
    card.setAttribute("aria-labelledby", title.id);
    const context = element("p", "approval-context");
    const details = element("details");
    details.open = true;
    const summary = element("summary", "", "Review input files and content digest");
    const digest = element("code", "approval-digest");
    const inputs = element("ul", "approval-inputs");
    details.append(summary, digest, inputs);
    const readonlyOptions = element("div", "approval-readonly-options");
    const readonly = element("p", "approval-readonly");
    const form = element("form", "approval-form");
    form.dataset.approvalForm = request.id;
    const choices = element("fieldset");
    choices.append(element("legend", "", "1. Choose an artifact option"));
    const options = element("div", "approval-options");
    choices.append(options);
    const outcomes = element("fieldset");
    outcomes.append(element("legend", "", "2. Choose the decision outcome"));
    const outcomesRow = element("div", "approval-outcomes");
    for (const [value, label] of [["approved", "Approve the selected option"], ["rejected", "Request changes to the selected option"]]) {
      const row = element("label", "outcome-label");
      const input = element("input");
      input.type = "radio";
      input.name = "outcome";
      input.value = value;
      input.required = true;
      row.append(input, element("span", "", label));
      outcomesRow.append(row);
    }
    outcomes.append(outcomesRow);
    const rationaleLabel = element("label", "", "3. Explain your decision");
    const rationale = element("textarea");
    rationale.name = "rationale";
    rationale.required = true;
    rationale.rows = 4;
    rationale.id = `${prefix}-rationale`;
    rationaleLabel.htmlFor = rationale.id;
    rationale.placeholder = "State why this option is approved or what needs to change.";
    rationaleLabel.append(rationale);
    const confirmationLabel = element("label", "review-confirmation");
    const confirmation = element("input");
    confirmation.type = "checkbox";
    confirmation.name = "reviewed";
    confirmation.required = true;
    confirmationLabel.append(confirmation, element("span", "", "I reviewed the listed input files and the retained artwork versions for this decision."));
    const stale = element("div", "approval-stale");
    stale.hidden = true;
    const staleText = element("p");
    const useCurrent = element("button", "button button-quiet", "Review current inputs");
    useCurrent.type = "button";
    stale.append(staleText, useCurrent);
    const submitRow = element("div", "approval-submit-row");
    const submit = element("button", "button button-primary", "Record decision");
    submit.type = "submit";
    const availability = element("span", "muted");
    submitRow.append(submit, availability);
    const message = element("p", "approval-message");
    message.setAttribute("role", "status");
    message.tabIndex = -1;
    message.hidden = true;
    form.append(choices, outcomes, rationaleLabel, confirmationLabel, stale, submitRow);
    card.append(header, context, details, readonlyOptions, form, readonly, message);
    const view = {
      card, stage, title, status, context, digest, inputs, readonlyOptions, readonly,
      form, choices, options, outcomes, rationale, confirmation, stale, staleText,
      useCurrent, submit, availability, message, request, withdrawn: false,
      optionsKey: null, inputsKey: null,
      draft: { inputsDigest: request.inputsDigest, optionId: "", outcome: "", rationale: "", reviewed: false, submitting: false, conflict: false, result: null },
    };
    form.addEventListener("input", () => {
      view.draft.rationale = rationale.value;
      rationale.setCustomValidity("");
      view.draft.reviewed = confirmation.checked;
      view.draft.optionId = form.querySelector('input[name="optionId"]:checked')?.value || "";
      view.draft.outcome = form.querySelector('input[name="outcome"]:checked')?.value || "";
      updateApprovalAvailability(view);
    });
    form.addEventListener("change", (event) => {
      if (event.target.name === "optionId") {
        confirmation.checked = false;
        view.draft.reviewed = false;
      }
      updateApprovalAvailability(view);
    });
    useCurrent.addEventListener("click", () => {
      if (view.request.status !== "pending" || view.request.inputsDigest === view.draft.inputsDigest) return;
      view.draft.inputsDigest = view.request.inputsDigest;
      view.draft.reviewed = false;
      view.draft.conflict = false;
      view.draft.result = null;
      confirmation.checked = false;
      view.message.hidden = true;
      updateApprovalAvailability(view);
      view.options.querySelector("input")?.focus();
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitApproval(view);
    });
    return view;
  }

  function artworkOptions(option) {
    const list = element("ul", "option-artworks");
    if (!option.artworkIds.length) {
      list.append(element("li", "muted", "No visual artifact is attached to this option. Review the listed input files."));
      return list;
    }
    for (const id of option.artworkIds) {
      const row = element("li");
      const artwork = state.artworkById.get(id);
      if (artwork) {
        const button = element("button", "", artwork.title);
        button.type = "button";
        button.dataset.artworkId = artwork.id;
        button.append(element("span", "monospace", `${artwork.path} · version ${artwork.version}`));
        button.addEventListener("click", () => openArtwork(artwork, button));
        row.append(button);
      } else {
        row.append(element("p", "muted", `Artwork ${id} is not present in the snapshot. This version cannot be previewed.`));
      }
      list.append(row);
    }
    return list;
  }

  function updateApprovalOptions(view) {
    const key = JSON.stringify(view.request.options.map((option) => ({ ...option, artworks: option.artworkIds.map((id) => state.artworkById.get(id) || null) })));
    if (key === view.optionsKey) return;
    view.optionsKey = key;
    const active = document.activeElement;
    const focusedOption = view.options.contains(active) && active.name === "optionId" ? active.value : null;
    const focusedArtwork = view.options.contains(active) ? active.dataset.artworkId : null;
    const choices = [];
    const readonly = [];
    for (const option of view.request.options) {
      const choice = element("div", "approval-option");
      const label = element("label", "option-label");
      const input = element("input");
      input.type = "radio";
      input.name = "optionId";
      input.value = option.id;
      input.required = true;
      input.checked = view.draft.optionId === option.id;
      label.append(input, element("span", "", option.label));
      choice.append(label, artworkOptions(option));
      choices.push(choice);
      const item = element("section", "approval-option");
      item.append(element("h4", "", option.label), artworkOptions(option));
      readonly.push(item);
    }
    view.options.replaceChildren(...(choices.length ? choices : [element("p", "muted", "No selectable options were published.")]));
    view.readonlyOptions.replaceChildren(...readonly);
    view.readonlyOptions.classList.add("approval-options");
    if (focusedOption !== null || focusedArtwork) {
      const target = focusedArtwork
        ? Array.from(view.options.querySelectorAll("[data-artwork-id]")).find((node) => node.dataset.artworkId === focusedArtwork)
        : Array.from(view.options.querySelectorAll('input[name="optionId"]')).find((node) => node.value === focusedOption);
      (target || view.title).focus({ preventScroll: true });
    }
  }

  function updateApprovalAvailability(view) {
    if (!state.snapshot) return;
    const request = view.request;
    const draft = view.draft;
    const guided = state.snapshot.run.mode === "guided";
    const terminal = ["approved", "rejected"].includes(request.status);
    const recorded = draft.result?.inputsDigest === request.inputsDigest;
    const changed = request.inputsDigest !== draft.inputsDigest;
    const stale = request.status === "stale" || changed || draft.conflict || view.withdrawn;
    const selected = request.options.find((option) => option.id === draft.optionId);
    const unavailable = selected?.artworkIds.some((id) => !state.artworkById.has(id));
    const formHadFocus = view.form.contains(document.activeElement);
    view.form.hidden = !guided || terminal || Boolean(recorded);
    if (view.form.hidden && formHadFocus) (view.message.hidden ? view.title : view.message).focus({ preventScroll: true });
    view.readonlyOptions.hidden = guided && !terminal && !recorded;
    view.readonly.hidden = guided && !terminal && !recorded;
    if (!guided) view.readonly.textContent = `${state.snapshot.run.mode === "yolo" ? "Autonomous mode" : "Run mode unverified"}. Recorded request status: ${request.status}. No user approval is requested.`;
    else if (terminal) view.readonly.textContent = `Recorded decision: ${request.status}. This does not by itself establish that an acceptance gate passed.`;
    else if (recorded) view.readonly.textContent = `The server confirmed a decision recorded as ${draft.result.outcome}. Waiting for the next snapshot to reflect that record.`;
    view.choices.disabled = draft.submitting || terminal || !guided || view.withdrawn;
    view.outcomes.disabled = draft.submitting || terminal || !guided || view.withdrawn;
    view.rationale.readOnly = draft.submitting || terminal || !guided || view.withdrawn;
    view.confirmation.disabled = draft.submitting || stale || terminal || !guided;
    if (stale && draft.reviewed) {
      draft.reviewed = false;
      view.confirmation.checked = false;
    }
    view.stale.hidden = !stale;
    if (view.withdrawn) view.staleText.textContent = "This request is no longer in the latest snapshot. Your draft is retained, but it cannot be submitted.";
    else if (changed) view.staleText.textContent = `The request changed after this draft began. Draft digest ${draft.inputsDigest}. Current digest ${request.inputsDigest}. Review the current inputs before submitting. Your rationale and option selection are retained.`;
    else view.staleText.textContent = "This request is stale. The director must publish a refreshed digest-bound request before a decision can be recorded. Your draft is retained.";
    view.useCurrent.hidden = !changed || view.withdrawn;
    view.useCurrent.disabled = draft.submitting || request.status !== "pending";
    let reason = "";
    if (!guided) reason = state.snapshot.run.mode === "yolo" ? "Autonomous mode does not accept user approvals." : "Run mode is unverified. User approvals are disabled.";
    else if (view.withdrawn) reason = "Request not present in the current snapshot.";
    else if (terminal || recorded) reason = "A decision is already recorded.";
    else if (stale) reason = "Review a refreshed request before submitting.";
    else if (!snapshotFresh()) reason = "A fresh authenticated snapshot is required.";
    else if (!request.options.length) reason = "No options are available.";
    else if (!request.inputs.length || !request.inputsDigest) reason = "No digest-bound input files are available.";
    else if (unavailable) reason = "The selected option has an unavailable artwork version.";
    else if (draft.submitting) reason = "Recording the decision. Do not resubmit.";
    view.submit.disabled = Boolean(reason);
    view.submit.textContent = draft.submitting ? "Recording decision" : "Record decision";
    view.availability.textContent = reason || "Your decision applies only to the digest shown above.";
  }

  function renderApprovals(snapshot) {
    const guided = snapshot.run.mode === "guided";
    byId("approval-mode").textContent = guided
      ? "Guided mode. Inspect the actual retained versions, choose an option, and record your reason. Changed inputs invalidate old approvals."
      : snapshot.run.mode === "yolo"
        ? "Autonomous yolo mode. The director records its decisions and continues without waiting for user approval. Pending gates remain pending until evidence passes."
        : "Run mode is unverified. No user approval can be submitted.";
    const pending = snapshot.approvals.filter((request) => request.status === "pending").length;
    byId("approval-count").hidden = !guided || pending === 0;
    byId("approval-count").textContent = String(pending);
    byId("approval-count").setAttribute("aria-label", `${pending} pending requests`);
    const list = byId("approval-list");
    if (!state.approvalViews.size) list.replaceChildren();
    const present = new Set();
    for (const request of snapshot.approvals) {
      present.add(request.id);
      let view = state.approvalViews.get(request.id);
      if (!view) {
        view = createApprovalView(request);
        state.approvalViews.set(request.id, view);
        list.append(view.card);
      }
      view.request = request;
      view.withdrawn = false;
      view.stage.textContent = `${request.stage === "plan" ? "Plan" : "Design"} · ${request.id}`;
      view.title.textContent = request.title;
      view.context.textContent = request.context;
      view.status.textContent = request.status;
      view.status.dataset.state = request.status;
      view.digest.textContent = request.inputsDigest;
      const key = JSON.stringify(request.inputs);
      if (key !== view.inputsKey) {
        view.inputsKey = key;
        view.inputs.replaceChildren(...(request.inputs.length ? request.inputs.map((path) => element("li", "", path)) : [element("li", "", "No input files are listed. No approval can be submitted.")]));
      }
      updateApprovalOptions(view);
      updateApprovalAvailability(view);
    }
    for (const [id, view] of state.approvalViews) {
      if (!present.has(id)) {
        view.withdrawn = true;
        view.status.textContent = "Not in current snapshot";
        view.status.dataset.state = "stale";
        updateApprovalAvailability(view);
      }
    }
    if (!state.approvalViews.size) list.append(element("p", "empty-state", guided ? "No approval requests have been published. The dashboard does not create or assume an approval." : snapshot.run.mode === "yolo" ? "No approval requests are recorded. This autonomous run does not wait for user approvals." : "Approval requests are unavailable while run mode is unverified."));
  }

  function renderDecisions(snapshot) {
    const records = snapshot.decisions?.slice().reverse();
    const pageCount = records ? Math.ceil(records.length / PAGE_SIZE) : 0;
    state.decisionPage = Math.max(1, Math.min(state.decisionPage, pageCount || 1));
    const start = (state.decisionPage - 1) * PAGE_SIZE;
    const current = records?.slice(start, start + PAGE_SIZE);
    const key = JSON.stringify({ records: current, total: records?.length, page: state.decisionPage });
    if (key === state.decisionKey) return;
    state.decisionKey = key;
    byId("decision-count").textContent = records ? `${numberFormat.format(records.length)} actual records` : "Not supplied by this snapshot";
    byId("decision-page").textContent = pageCount ? `Page ${state.decisionPage} of ${pageCount}` : "No recorded pages";
    byId("decision-previous").disabled = state.decisionPage <= 1;
    byId("decision-next").disabled = state.decisionPage >= pageCount;
    const list = byId("decision-list");
    if (!current?.length) {
      list.replaceChildren(element("li", "empty-state", records ? "No decisions have been recorded." : "Recorded decision history is not available in this snapshot."));
      return;
    }
    list.replaceChildren(...current.map((decision, index) => {
      const item = element("li", "decision-record");
      item.dataset.decisionIndex = String(records.length - 1 - start - index);
      const heading = element("div", "decision-record-heading");
      heading.append(element("h4", "", decision.stage), badge(decision.outcome));
      const meta = element("div", "decision-meta muted");
      meta.append(element("span", "", `Actor ${decision.actor}`));
      if (decision.recordedAt && Number.isFinite(Date.parse(decision.recordedAt))) {
        const time = element("time");
        showTime(time, decision.recordedAt);
        meta.append(time);
      } else {
        meta.append(element("span", "", decision.recordedAt ? `Recorded time ${decision.recordedAt}` : "Timestamp not recorded"));
      }
      item.append(heading, meta, element("p", "decision-rationale", decision.rationale || "No rationale recorded."));
      if (decision.optionId !== undefined) item.append(element("p", "monospace", `Chosen option ${decision.optionId}`));
      if (decision.inputsDigest !== undefined) {
        const details = element("details");
        details.append(element("summary", "", "Reviewed input digest"), element("code", "approval-digest", decision.inputsDigest));
        item.append(details);
      }
      return item;
    }));
  }

  async function submitApproval(view) {
    updateApprovalAvailability(view);
    if (view.submit.disabled) return;
    const draft = view.draft;
    const request = view.request;
    const rationale = view.rationale.value.trim();
    view.rationale.setCustomValidity(rationale ? "" : "Explain the decision before submitting.");
    if (!view.form.reportValidity()) return;
    const option = request.options.find((item) => item.id === draft.optionId);
    if (!option || !request.inputs.length || !draft.inputsDigest || !draft.reviewed || !["approved", "rejected"].includes(draft.outcome)) {
      view.message.hidden = false;
      view.message.dataset.state = "error";
      view.message.textContent = "A listed input digest, an available option, an outcome, and your review confirmation are required. No decision was submitted.";
      return;
    }
    const payload = { id: request.id, inputsDigest: draft.inputsDigest, optionId: option.id, outcome: draft.outcome, rationale };
    draft.submitting = true;
    view.message.hidden = false;
    view.message.dataset.state = "pending";
    view.message.textContent = "Recording your decision against the reviewed input digest.";
    updateApprovalAvailability(view);
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(new URL("api/approval", baseUrl), {
        method: "POST", headers: { Authorization: `Bearer ${state.token}`, "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload), cache: "no-store", credentials: "omit", redirect: "error", signal: controller.signal,
      });
      if (!response.ok) {
        const detail = await responseError(response);
        if (response.status === 409) {
          draft.conflict = true;
          view.message.dataset.state = "stale";
          view.message.textContent = `Stale conflict. ${detail} No approval is assumed. Review a refreshed request; your draft is retained.`;
        } else {
          view.message.dataset.state = "error";
          view.message.textContent = `The server did not accept this decision. ${detail} Your draft is retained.`;
          if ([401, 403].includes(response.status)) state.failure = { kind: "unauthorized", message: detail };
        }
      } else {
        draft.result = { inputsDigest: payload.inputsDigest, outcome: payload.outcome };
        view.message.dataset.state = payload.outcome;
        view.message.textContent = payload.outcome === "approved"
          ? "Decision recorded as approved for the reviewed digest. Acceptance gates still require their own evidence."
          : "Decision recorded as rejected for the reviewed digest. Your request for changes was saved.";
      }
    } catch (error) {
      view.message.dataset.state = "error";
      view.message.textContent = `${error.name === "AbortError" ? "The decision request timed out." : "No submission confirmation was received."} The decision may or may not have been recorded. Refresh the recorded status before retrying. Your draft is retained.`;
    } finally {
      clearTimeout(deadline);
      draft.submitting = false;
      updateApprovalAvailability(view);
      refreshSnapshot();
    }
  }

  function applyViewerScale() {
    const viewer = state.viewer;
    if (!viewer?.ready) return;
    const stage = byId("viewer-stage");
    if (viewer.mode === "fit") viewer.scale = Math.max(0.001, Math.min(1, (stage.clientWidth - 32) / viewer.width, (stage.clientHeight - 32) / viewer.height));
    if (viewer.mode === "natural") viewer.scale = 1;
    const width = viewer.width * viewer.scale;
    const height = viewer.height * viewer.scale;
    if (viewer.artwork.kind === "image") {
      viewer.node.style.width = `${width}px`;
      viewer.node.style.height = `${height}px`;
    } else {
      viewer.wrapper.style.width = `${width}px`;
      viewer.wrapper.style.height = `${height}px`;
      viewer.node.style.transform = `scale(${viewer.scale})`;
    }
    byId("viewer-scale").textContent = `${Math.round(viewer.scale * 1000) / 10}%`;
    byId("viewer-fit").setAttribute("aria-pressed", String(viewer.mode === "fit"));
    byId("viewer-natural").setAttribute("aria-pressed", String(viewer.mode === "natural"));
    byId("viewer-zoom-out").disabled = viewer.scale <= 0.01;
    byId("viewer-zoom-in").disabled = viewer.scale >= 8;
  }

  function openArtwork(artwork, returnFocus) {
    const dialog = byId("artwork-dialog");
    let url;
    try {
      url = artifactUrl(artwork);
    } catch (error) {
      byId("connection-notice").hidden = false;
      byId("connection-notice").dataset.state = "error";
      byId("connection-notice").textContent = error.message;
      return;
    }
    if (state.viewer?.node) state.viewer.node.removeAttribute("src");
    const content = byId("viewer-content");
    content.replaceChildren();
    dialog.classList.remove("is-expanded");
    byId("viewer-expand").setAttribute("aria-pressed", "false");
    byId("viewer-title").textContent = artwork.title;
    byId("viewer-context").textContent = artwork.context;
    byId("viewer-metadata").textContent = `${artwork.path} · version ${artwork.version} · retained ${formatTime(artwork.createdAt)}`;
    byId("viewer-download").href = url;
    byId("viewer-download").download = artwork.path.split("/").pop() || "artwork";
    byId("viewer-scale").textContent = "Loading";
    byId("viewer-dimensions").textContent = artwork.kind === "image" ? "Natural image dimensions will be read from this retained file." : `Preview viewport ${DOCUMENT_WIDTH} × ${DOCUMENT_HEIGHT} CSS pixels. This is a viewer size, not the document's source dimensions.`;
    byId("viewer-policy").textContent = artwork.kind === "image"
      ? "Image-only display. Natural size shows one image pixel per CSS pixel."
      : artwork.kind === "html" ? "Sandboxed static HTML. Scripts, forms, and navigation are disabled. Script-rendered content needs a published screenshot."
        : "Sandboxed PDF. Browser PDF support varies. Save the retained PDF if this preview is blank or unavailable.";
    byId("viewer-load-status").textContent = "Loading the retained artifact.";
    byId("viewer-natural").textContent = artwork.kind === "image" ? "Natural size" : "100% scale";
    for (const id of ["viewer-fit", "viewer-natural", "viewer-zoom-in", "viewer-zoom-out"]) byId(id).disabled = true;
    const viewer = { artwork, returnFocus, node: null, wrapper: null, width: 0, height: 0, scale: 1, mode: "fit", ready: false };
    state.viewer = viewer;
    const media = document.createElement(artwork.kind === "image" ? "img" : "iframe");
    viewer.node = media;
    media.referrerPolicy = "no-referrer";
    if (artwork.kind === "image") {
      media.alt = artwork.title;
      media.addEventListener("load", () => {
        if (state.viewer !== viewer) return;
        viewer.width = media.naturalWidth;
        viewer.height = media.naturalHeight;
        viewer.ready = viewer.width > 0 && viewer.height > 0;
        byId("viewer-dimensions").textContent = `Natural dimensions ${numberFormat.format(viewer.width)} × ${numberFormat.format(viewer.height)} pixels.`;
        byId("viewer-load-status").textContent = viewer.ready ? "Retained image loaded." : "Image dimensions could not be read. Save the artifact to inspect it.";
        for (const id of ["viewer-fit", "viewer-natural"]) byId(id).disabled = !viewer.ready;
        applyViewerScale();
      }, { once: true });
      content.append(media);
    } else {
      viewer.width = DOCUMENT_WIDTH;
      viewer.height = DOCUMENT_HEIGHT;
      viewer.ready = true;
      viewer.wrapper = element("div", "viewer-document");
      media.setAttribute("sandbox", "");
      media.title = `${artwork.title}, sandboxed ${artwork.kind.toUpperCase()} with scripts disabled`;
      media.style.width = `${DOCUMENT_WIDTH}px`;
      media.style.height = `${DOCUMENT_HEIGHT}px`;
      media.addEventListener("load", () => {
        if (state.viewer !== viewer) return;
        byId("viewer-load-status").textContent = artwork.kind === "html"
          ? "The sandboxed document response loaded. Blank script-rendered content needs a published screenshot."
          : "The sandboxed PDF response loaded. If the browser cannot display it, save the retained PDF.";
      }, { once: true });
      viewer.wrapper.append(media);
      content.append(viewer.wrapper);
      for (const id of ["viewer-fit", "viewer-natural"]) byId(id).disabled = false;
    }
    media.addEventListener("error", () => {
      if (state.viewer !== viewer) return;
      byId("viewer-load-status").textContent = "The preview could not be loaded. Save the retained artifact or refresh the server snapshot.";
    }, { once: true });
    dialog.showModal();
    byId("viewer-close").focus();
    byId("viewer-stage").scrollTo(0, 0);
    viewerResize?.observe(byId("viewer-stage"));
    media.src = url;
    applyViewerScale();
  }

  function closeArtwork() {
    byId("artwork-dialog").close();
  }

  for (const button of document.querySelectorAll("[data-view]")) button.addEventListener("click", () => setView(button.dataset.view));
  for (const button of document.querySelectorAll("[data-open-library]")) button.addEventListener("click", () => setView("library"));
  document.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    byId("workspace-main").focus();
  });
  byId("refresh-snapshot").addEventListener("click", refreshSnapshot);
  byId("server-url").textContent = window.location.href;
  byId("copy-address").addEventListener("click", async () => {
    const address = byId("server-url").textContent;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard is unavailable.");
      await navigator.clipboard.writeText(address);
      byId("address-feedback").textContent = "Private address copied. Share it only with trusted reviewers.";
    } catch {
      const range = document.createRange();
      range.selectNodeContents(byId("server-url"));
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      byId("server-url").focus();
      byId("address-feedback").textContent = "Clipboard access is unavailable. The address is selected; copy it using your browser.";
    }
  });
  byId("library-filters").addEventListener("submit", (event) => event.preventDefault());
  for (const id of ["library-search", "library-kind", "library-versions", "library-sort"]) {
    byId(id).addEventListener(id === "library-search" ? "input" : "change", () => {
      state.libraryPage = 1;
      if (state.snapshot) renderLibrary();
    });
  }
  byId("library-clear").addEventListener("click", () => {
    byId("library-filters").reset();
    state.libraryPage = 1;
    if (state.snapshot) renderLibrary();
    byId("library-search").focus();
  });
  for (const [id, direction] of [["library-previous", -1], ["library-next", 1]]) byId(id).addEventListener("click", () => {
    state.libraryPage += direction;
    renderLibrary();
    byId("library-heading").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  });
  for (const [id, direction] of [["feed-previous", -1], ["feed-next", 1]]) byId(id).addEventListener("click", () => {
    state.feedPage += direction;
    renderActiveGallery();
    byId("feed-heading").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  });
  for (const [id, direction] of [["decision-previous", -1], ["decision-next", 1]]) byId(id).addEventListener("click", () => {
    state.decisionPage += direction;
    renderDecisions(state.snapshot);
    byId("decisions-heading").focus({ preventScroll: true });
  });
  byId("viewer-close").addEventListener("click", closeArtwork);
  byId("artwork-dialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeArtwork();
  });
  byId("artwork-dialog").addEventListener("close", () => {
    const viewer = state.viewer;
    viewerResize?.unobserve(byId("viewer-stage"));
    viewer?.node?.removeAttribute("src");
    byId("viewer-content").replaceChildren();
    state.viewer = null;
    const replacement = viewer ? byId(`${state.view}-panel`).querySelector(`[data-artwork-id="${CSS.escape(viewer.artwork.id)}"] .artwork-open`) : null;
    const target = viewer?.returnFocus?.isConnected ? viewer.returnFocus : replacement || byId(`nav-${state.view}`);
    target?.focus({ preventScroll: true });
  });
  byId("artwork-dialog").addEventListener("click", (event) => {
    if (event.target !== byId("artwork-dialog")) return;
    const bounds = byId("artwork-dialog").getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeArtwork();
  });
  for (const [id, mode] of [["viewer-fit", "fit"], ["viewer-natural", "natural"]]) byId(id).addEventListener("click", () => {
    if (!state.viewer?.ready) return;
    state.viewer.mode = mode;
    applyViewerScale();
    byId("viewer-stage").scrollTo(0, 0);
  });
  for (const [id, multiplier] of [["viewer-zoom-out", 0.8], ["viewer-zoom-in", 1.25]]) byId(id).addEventListener("click", () => {
    if (!state.viewer?.ready) return;
    state.viewer.mode = "zoom";
    state.viewer.scale = Math.max(0.01, Math.min(8, state.viewer.scale * multiplier));
    applyViewerScale();
  });
  byId("viewer-expand").addEventListener("click", () => {
    const expanded = byId("artwork-dialog").classList.toggle("is-expanded");
    byId("viewer-expand").setAttribute("aria-pressed", String(expanded));
    applyViewerScale();
  });
  window.addEventListener("resize", () => {
    if (!previewResize) for (const preview of previewJobs.keys()) scaleThumbnail(preview);
    if (!viewerResize && state.viewer?.mode === "fit") applyViewerScale();
  });
  window.addEventListener("online", refreshSnapshot);
  window.addEventListener("offline", updateConnection);
  window.addEventListener("hashchange", () => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token") || "";
    if (token === state.token) return;
    state.token = token;
    byId("server-url").textContent = window.location.href;
    state.failure = null;
    state.requestController?.abort();
    refreshSnapshot();
  });
  let ageTimer = setInterval(updateConnection, 1000);
  window.addEventListener("pagehide", () => {
    state.stopped = true;
    clearTimeout(state.pollTimer);
    clearInterval(ageTimer);
    state.requestController?.abort();
    previewObserver?.disconnect();
    previewResize?.disconnect();
    viewerResize?.disconnect();
  });
  window.addEventListener("pageshow", (event) => {
    if (!event.persisted) return;
    state.stopped = false;
    ageTimer = setInterval(updateConnection, 1000);
    for (const [preview, job] of previewJobs) {
      if (!job.node && previewObserver) previewObserver.observe(preview);
      if (job.node?.tagName === "IFRAME") previewResize?.observe(preview);
    }
    if (state.viewer) viewerResize?.observe(byId("viewer-stage"));
    refreshSnapshot();
  });
  refreshSnapshot();
})();
