"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const status = byId("connection-status");
  const notice = byId("connection-notice");
  const list = byId("run-list");
  const params = new URLSearchParams(window.location.hash.slice(1));
  const token = params.get("token");
  const authenticated = params.size === 1 && /^[A-Za-z0-9_-]{16,256}$/.test(token || "");
  const rows = new Map();
  let timer = null;
  let pending = false;
  let currentAddress = "";
  let addressSignature = "";

  function showStatus(state, message) {
    status.dataset.state = state;
    status.textContent = state === "connected" ? "Connected" : state === "unauthorized" ? "Authentication error" : "Unavailable";
    notice.dataset.state = state;
    notice.textContent = message;
  }

  function dashboardUrl(value) {
    if (typeof value !== "string" || /[\u0000-\u0020\u007f-\u009f\\]/.test(value)) return null;
    try {
      const url = new URL(value);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search
          || !/^#token=[A-Za-z0-9_-]{16,256}$/.test(url.hash)) return null;
      return url.href;
    } catch {
      return null;
    }
  }

  function directAddress(details) {
    const addresses = [details.localUrl, ...(details.lanUrls || []), details.url].map(dashboardUrl).filter(Boolean);
    return addresses.find((value) => new URL(value).hostname === window.location.hostname)
      || dashboardUrl(details.url) || dashboardUrl(details.qrUrl) || addresses[0] || null;
  }

  async function request(path, payload) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(path, {
        method: payload ? "POST" : "GET",
        headers: { Authorization: `Bearer ${token}`, ...(payload ? { "Content-Type": "application/json" } : {}) },
        ...(payload ? { body: JSON.stringify(payload) } : {}),
        cache: "no-store",
        credentials: "omit",
        redirect: "error",
        referrerPolicy: "no-referrer",
        signal: controller.signal,
      });
      if (response.status === 401) {
        const error = new Error("Authentication required. Open the complete private address from your coding client.");
        error.unauthorized = true;
        throw error;
      }
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.error === "string" ? result.error : "The dashboard request failed.");
      return result;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function selectAddress(element) {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(element);
    selection.removeAllRanges();
    selection.addRange(range);
    element.focus();
  }

  async function copyAddress(value, element) {
    try {
      await navigator.clipboard.writeText(value);
      byId("address-feedback").textContent = "Private address copied.";
    } catch {
      selectAddress(element);
      byId("address-feedback").textContent = "Address selected. Use your device's Copy command.";
    }
  }

  function renderAddresses(details) {
    currentAddress = directAddress(details) || "";
    byId("server-url").textContent = currentAddress;
    byId("copy-address").disabled = !currentAddress;
    const addresses = [["Loopback", details.localUrl], ...(details.lanUrls || []).map((value) => ["LAN", value])];
    const signature = JSON.stringify(addresses);
    if (signature === addressSignature) return;
    addressSignature = signature;
    const container = byId("connection-addresses");
    container.replaceChildren();
    for (const [label, value] of addresses) {
      const url = dashboardUrl(value);
      if (!url) continue;
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = url;
      link.referrerPolicy = "no-referrer";
      link.textContent = `${label} ${url}`;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "button button-quiet button-small";
      copy.textContent = `Copy ${label} address`;
      copy.addEventListener("click", () => copyAddress(url, link));
      item.append(link, document.createTextNode(" "), copy);
      container.append(item);
    }
    if (!(details.lanUrls || []).length) {
      const item = document.createElement("li");
      item.textContent = "LAN unavailable for this connection.";
      container.append(item);
    }
  }

  async function openRun(run, control) {
    control.setAttribute("aria-disabled", "true");
    if (control.tagName === "BUTTON") control.disabled = true;
    notice.textContent = "Opening the design run.";
    try {
      const details = await request("/api/open", { run });
      const destination = directAddress(details);
      if (!destination) throw new Error("The run has no usable dashboard address.");
      window.location.assign(destination);
    } catch (error) {
      showStatus(error.unauthorized ? "unauthorized" : "error", error.message || "The design run could not be opened.");
      if (error.unauthorized) hidePrivateData();
      control.removeAttribute("aria-disabled");
      if (control.tagName === "BUTTON") control.disabled = false;
    }
  }

  function renderRuns(runs) {
    const present = new Set();
    for (const run of runs) {
      if (typeof run.run !== "string") continue;
      present.add(run.run);
      let row = rows.get(run.run);
      if (!row) {
        const item = document.createElement("li");
        const heading = document.createElement("h3");
        const path = document.createElement("p");
        const detail = document.createElement("p");
        const availability = document.createElement("p");
        const address = document.createElement("code");
        address.className = "work-item-meta monospace";
        address.tabIndex = 0;
        address.setAttribute("aria-label", "Private run dashboard address");
        const actions = document.createElement("div");
        path.className = "work-item-meta monospace";
        detail.className = "work-item-message";
        availability.className = "work-item-meta";
        actions.className = "work-item-meta";
        item.append(heading, path, detail, availability, address, actions);
        row = { item, heading, path, detail, availability, address, actions, live: null, destination: null };
        rows.set(run.run, row);
        list.append(item);
      }
      row.heading.textContent = `${run.id}${run.selected ? " (selected)" : ""}`;
      row.path.textContent = run.run;
      row.detail.textContent = `Recorded phase: ${run.phase}. Recorded status: ${run.status}.`;
      const destination = run.live && run.dashboard ? directAddress(run.dashboard) : null;
      row.availability.textContent = destination
        ? ((run.dashboard.lanUrls || []).length ? "Dashboard live." : "Dashboard live. LAN unavailable for this run.")
        : "Dashboard stopped. Open this run to start its dashboard.";
      row.address.textContent = destination || "";
      row.address.hidden = !destination;
      if (row.live !== Boolean(destination) || row.destination !== destination) {
        row.live = Boolean(destination);
        row.destination = destination;
        const control = document.createElement(destination ? "a" : "button");
        control.className = "button button-primary";
        control.textContent = destination ? "Open dashboard" : "Open run";
        if (destination) {
          control.href = destination;
          control.referrerPolicy = "no-referrer";
        } else {
          control.type = "button";
        }
        control.addEventListener("click", (event) => {
          if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
          event.preventDefault();
          if (control.getAttribute("aria-disabled") !== "true") openRun(run.run, control);
        });
        row.actions.replaceChildren(control);
      }
    }
    for (const [run, row] of rows) {
      if (!present.has(run)) {
        row.item.remove();
        rows.delete(run);
      }
    }
    byId("empty-runs").hidden = present.size !== 0;
    byId("run-count").textContent = `${present.size} recorded ${present.size === 1 ? "run" : "runs"}`;
  }

  function hidePrivateData() {
    byId("session-panel").hidden = true;
    byId("runs-panel").hidden = true;
    byId("server-url").textContent = "";
    currentAddress = "";
    byId("copy-address").disabled = true;
    byId("repository").textContent = "";
    byId("session-identity").textContent = "";
    byId("connection-addresses").replaceChildren();
    addressSignature = "";
    list.replaceChildren();
    rows.clear();
  }

  async function refresh() {
    if (pending || !authenticated) return;
    pending = true;
    window.clearTimeout(timer);
    byId("refresh-session").disabled = true;
    byId("runs-panel").setAttribute("aria-busy", "true");
    try {
      const details = await request("/api/session");
      renderAddresses(details);
      byId("repository").textContent = details.repo;
      byId("session-identity").textContent = `Connection ${details.instanceId}`;
      renderRuns(Array.isArray(details.runs) ? details.runs : []);
      byId("session-panel").hidden = false;
      byId("runs-panel").hidden = false;
      showStatus("connected", "Connection dashboard is live. Select a run to open its separate workspace.");
    } catch (error) {
      hidePrivateData();
      showStatus(error.unauthorized ? "unauthorized" : "offline", error.message || "The connection dashboard is unavailable.");
    } finally {
      pending = false;
      byId("refresh-session").disabled = false;
      byId("runs-panel").setAttribute("aria-busy", "false");
      timer = window.setTimeout(refresh, 2000);
    }
  }

  byId("copy-address").addEventListener("click", () => copyAddress(currentAddress, byId("server-url")));
  byId("refresh-session").addEventListener("click", refresh);
  document.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    byId("workspace-main").focus();
  });
  window.addEventListener("hashchange", () => window.location.reload());
  window.addEventListener("pagehide", () => window.clearTimeout(timer));
  if (authenticated) {
    refresh();
  } else {
    hidePrivateData();
    byId("refresh-session").disabled = true;
    showStatus("unauthorized", "Authentication required. Open the complete private address from your coding client.");
  }
})();
