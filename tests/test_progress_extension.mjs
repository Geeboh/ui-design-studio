import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import test from "node:test";
import designProgress from "../.omp/extensions/ui-design-progress.ts";

const WIDGET = "ui-design-progress";
const TASK_EVENT = "pi-tasks:state";

function writeJson(path, value) {
	writeFileSync(path, JSON.stringify(value));
}

function fixture(t, options = {}) {
	const base = mkdtempSync(join(tmpdir(), "design-progress-"));
	const project = join(base, "project with spaces");
	const runsRelative = options.runs ?? "work/design-runs";
	const runs = join(project, runsRelative);
	mkdirSync(runs, { recursive: true });
	writeJson(join(project, "ui-design-studio.json"), { paths: { runs: runsRelative } });
	t.after(() => rmSync(base, { recursive: true, force: true }));
	return { base, project, runs, runsRelative };
}

function addRun(f, id = "alpha", overrides = {}) {
	const root = join(f.runs, id);
	mkdirSync(root);
	const url = `http://192.0.2.45:54321/#token=${"0123456789abcdef".repeat(40)}`;
	const snapshot = {
		schemaVersion: "1.0", instanceId: `instance-${id}`, revision: "first", observedAt: new Date().toISOString(),
		run: { id, themeId: "test-theme", mode: "guided", phase: "design", status: "pending" },
		server: { url, startedAt: new Date().toISOString() },
		gates: [{ status: "passed" }, { status: "pending" }, { status: "pending" }, { status: "pending" }, { status: "failed" }],
		coverage: { required: 8, mockups: 4, verified: 2, inventoryComplete: false },
		nextAction: "Review the real mockups", blockers: ["A human choice is pending"], warnings: [],
		workers: [{ status: "active" }, { status: "blocked" }], tasks: [{ status: "done" }, { status: "active" }],
		statistics: { artworks: 6, workers: 2, tasks: 2, evidence: 4, passedEvidence: 1, elapsedSeconds: 125 },
		...overrides,
	};
	writeJson(join(root, "run.json"), { schemaVersion: "1.1", id });
	writeJson(join(root, ".design-server.json"), { schemaVersion: "1.0", instanceId: snapshot.instanceId, run: root, url: snapshot.server.url });
	writeJson(join(root, ".design-status.json"), snapshot);
	return { root, snapshot, url: snapshot.server.url };
}

function taskEvent(title = "The actual task") {
	return {
		version: 1, reason: "task_mutation", widgetId: "pi-tasks",
		state: {
			tasks: { T1: { id: "T1", title, status: "active", progress: 25, acceptanceCriteria: [{ id: "C1", status: "pending" }], evidence: [] } },
			activeTaskId: "T1", warnings: [], lastUpdatedAt: "2026-11-12T00:00:00Z",
		},
	};
}

function host(t, project, options = {}) {
	const handlers = new Map();
	const bus = new Map();
	const commands = new Map();
	const timers = new Map();
	const widgets = new Map([["pi-tasks", ["Existing Pi Tasks widget"]]]);
	const statuses = new Map([["pi-tasks", "Existing Pi Tasks status"]]);
	const placements = [];
	const notifications = [];
	const reports = [];
	let timerId = 0;
	let sessionId = options.sessionId ?? "session-A";
	const context = {
		cwd: project, mode: options.mode ?? "tui", hasUI: options.hasUI ?? true, agent: { kind: options.agent ?? "main" },
		sessionManager: { getSessionId: () => sessionId },
		ui: {
			setWidget(key, lines, placement) {
				placements.push([key, placement]);
				if (lines === undefined) widgets.delete(key);
				else widgets.set(key, lines);
			},
			setStatus(key, value) {
				if (value === undefined) statuses.delete(key);
				else statuses.set(key, value);
			},
			notify: (message, type) => notifications.push({ message, type }),
		},
		setInterval(callback, delay) {
			assert.equal(delay, 2000);
			timers.set(++timerId, callback);
			return timerId;
		},
		clearTimer: id => timers.delete(id),
	};
	const api = {
		on(name, handler) {
			const list = handlers.get(name) ?? [];
			list.push(handler);
			handlers.set(name, list);
		},
		registerCommand: (name, command) => commands.set(name, command),
		events: {
			on(name, handler) {
				const list = bus.get(name) ?? new Set();
				list.add(handler);
				bus.set(name, list);
				return () => list.delete(handler);
			},
		},
		sendMessage: (message, options) => reports.push({ message, options }),
	};
	designProgress(api);
	function emit(name) {
		for (const handler of handlers.get(name) ?? []) handler({ type: name }, context);
	}
	t.after(() => emit("session_shutdown"));
	return {
		context, timers, widgets, statuses, placements, notifications, reports, bus,
		emit,
		state(event) { for (const handler of bus.get(TASK_EVENT) ?? []) handler(event); },
		tick() { for (const callback of [...timers.values()]) callback(); },
		command(args) { commands.get(WIDGET).handler(args, context); },
		setSession(id) { sessionId = id; },
	};
}

function exportPath(run, sessionId = "session-A") {
	return join(run.root, "progress-pi-tasks", `${createHash("sha256").update(sessionId).digest("hex")}.json`);
}

function exported(run) {
	const director = JSON.parse(readFileSync(join(run.root, "progress-pi-tasks-director.json"), "utf8"));
	return JSON.parse(readFileSync(exportPath(run, director.sessionId), "utf8"));
}

test("pins a separate wrapping URL row with honest gates, coverage, workers and tasks", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	const lines = runtime.widgets.get(WIDGET);
	assert.equal(lines.at(-1), run.url);
	assert.ok(run.url.length > 600);
	assert.ok(lines.length <= 10);
	assert.match(lines.join("\n"), /design \| pending/);
	assert.match(lines.join("\n"), /1\/5 passed \(20%\) \| 3 pending \| 1 failed/);
	assert.match(lines.join("\n"), /2\/8 verified \(25% declared\) \| 4 mockups \| inventory pending/);
	assert.match(lines.join("\n"), /Workers 1\/2 reported active \| Tasks 1\/2 done/);
	assert.match(lines.join("\n"), /Artworks 6 \| Evidence 1\/4 passed \| Elapsed 2m 5s/);
	assert.match(lines.join("\n"), /Next Review the real mockups/);
	assert.match(lines.join("\n"), /Blocker A human choice is pending/);
	assert.deepEqual(runtime.widgets.get("pi-tasks"), ["Existing Pi Tasks widget"]);
	assert.equal(runtime.statuses.get("pi-tasks"), "Existing Pi Tasks status");
	assert.ok(runtime.placements.every(([key, placement]) => key === WIDGET && placement.placement === "belowEditor"));
	assert.equal(runtime.timers.size, 1);
	assert.equal(existsSync(exportPath(run)), false);
});

test("polls changed status and marks old snapshots stale without passing pending gates", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	run.snapshot.observedAt = new Date(Date.now() - 60_000).toISOString();
	run.snapshot.nextAction = "Inspect new HTML artwork";
	run.snapshot.coverage.verified = 3;
	writeJson(join(run.root, ".design-status.json"), run.snapshot);
	runtime.tick();
	const output = runtime.widgets.get(WIDGET).join("\n");
	assert.match(output, /STALE snapshot/);
	assert.match(output, /3\/8 verified/);
	assert.match(output, /1\/5 passed \(20%\) \| 3 pending/);
	assert.match(output, /Next Inspect new HTML artwork/);
});

test("clones authentic v1 Pi Tasks state and exports atomically without touching its widget", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project);
	const event = taskEvent();
	const expected = structuredClone(event.state);
	runtime.state(event);
	event.state.tasks.T1.title = "Changed after publication";
	runtime.emit("session_start");
	runtime.command(relative(f.project, run.root));
	const output = exported(run);
	assert.deepEqual(output.state, expected);
	assert.equal(output.version, 1);
	assert.equal(output.widgetId, "pi-tasks");
	assert.equal(output.reason, "task_mutation");
	assert.equal(output.sessionId, "session-A");
	assert.equal(output.runId, "alpha");
	assert.ok(Number.isFinite(Date.parse(output.updatedAt)));
	assert.equal(statSync(exportPath(run)).mode & 0o777, 0o600);
	assert.deepEqual(readdirSync(run.root).filter(name => name.endsWith(".tmp")), []);
	const first = readFileSync(exportPath(run), "utf8");
	runtime.tick();
	assert.equal(readFileSync(exportPath(run), "utf8"), first);
	runtime.state(taskEvent("Next actual task title"));
	assert.equal(exported(run).state.tasks.T1.title, "Next actual task title");
	assert.deepEqual(runtime.widgets.get("pi-tasks"), ["Existing Pi Tasks widget"]);
});

test("rejects unknown event versions and malformed task fields without exporting fabricated tasks", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	runtime.command(relative(f.project, run.root));
	runtime.state({ ...taskEvent(), version: 2 });
	const malformed = taskEvent();
	malformed.state.tasks.T1.progress = 101;
	runtime.state(malformed);
	runtime.state({ version: 1, reason: "task_mutation", widgetId: "other", state: {} });
	assert.equal(existsSync(exportPath(run)), false);
});

test("requires explicit selection for multiple servers and keeps the selected run isolated", t => {
	const f = fixture(t);
	const first = addRun(f, "alpha");
	const second = addRun(f, "beta");
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	runtime.state(taskEvent());
	assert.match(runtime.widgets.get(WIDGET)[0], /Multiple design servers/);
	assert.equal(existsSync(exportPath(first)), false);
	runtime.command(relative(f.project, second.root));
	assert.equal(exported(second).runId, "beta");
	assert.equal(existsSync(exportPath(first)), false);
	assert.equal(runtime.widgets.get(WIDGET).at(-1), second.url);
	unlinkSync(join(second.root, ".design-server.json"));
	runtime.tick();
	assert.match(runtime.widgets.get(WIDGET)[0], /server stopped/);
	assert.equal(existsSync(exportPath(first)), false);
});

test("refuses paths outside configured runs, traversal, and unsafe configuration", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	runtime.command("../outside");
	runtime.command(run.root);
	runtime.command("other/project-run");
	assert.equal(runtime.notifications.length, 3);
	assert.ok(runtime.notifications.every(item => item.type === "warning"));
	writeJson(join(f.project, "ui-design-studio.json"), { paths: { runs: "../outside" } });
	runtime.state(taskEvent());
	assert.equal(existsSync(exportPath(run)), false);
	assert.match(runtime.widgets.get(WIDGET)[0], /project-relative path/);
});

test("rejects symlinked configuration, run roots, status, and export destinations", t => {
	const f = fixture(t);
	const run = addRun(f);
	const outside = join(f.base, "outside.json");
	writeFileSync(outside, "{\"preserve\":true}");
	const runtime = host(t, f.project);
	mkdirSync(join(run.root, "progress-pi-tasks"));
	const destination = exportPath(run);
	symlinkSync(outside, destination);
	runtime.state(taskEvent());
	runtime.emit("session_start");
	runtime.command(relative(f.project, run.root));
	assert.equal(readFileSync(outside, "utf8"), "{\"preserve\":true}");
	assert.ok(runtime.widgets.get(WIDGET).some(line => line.includes("Pi Tasks export unavailable")));
	assert.equal(runtime.widgets.get(WIDGET).at(-1), run.url);
	unlinkSync(destination);
	unlinkSync(join(run.root, ".design-status.json"));
	symlinkSync(outside, join(run.root, ".design-status.json"));
	runtime.tick();
	assert.match(runtime.widgets.get(WIDGET)[0], /plain files/);
	assert.equal(existsSync(destination), false);
	unlinkSync(join(f.project, "ui-design-studio.json"));
	symlinkSync(outside, join(f.project, "ui-design-studio.json"));
	runtime.tick();
	assert.match(runtime.widgets.get(WIDGET)[0], /plain files/);
});

test("does not follow symlinked configured run directories", t => {
	const f = fixture(t);
	const run = addRun(f);
	const alias = join(f.project, "aliased-runs");
	symlinkSync(f.runs, alias, "dir");
	writeJson(join(f.project, "ui-design-studio.json"), { paths: { runs: "aliased-runs" } });
	const runtime = host(t, f.project);
	runtime.state(taskEvent());
	runtime.emit("session_start");
	assert.equal(existsSync(exportPath(run)), false);
	assert.equal(runtime.widgets.has(WIDGET), false);
});

test("rejects mismatched run and server identities before exporting state", t => {
	const f = fixture(t);
	const run = addRun(f);
	run.snapshot.instanceId = "another-instance";
	writeJson(join(run.root, ".design-status.json"), run.snapshot);
	const runtime = host(t, f.project);
	runtime.state(taskEvent());
	runtime.emit("session_start");
	assert.match(runtime.widgets.get(WIDGET)[0], /different server/);
	assert.equal(existsSync(exportPath(run)), false);
	run.snapshot.instanceId = "instance-alpha";
	run.snapshot.run.id = "another-run";
	writeJson(join(run.root, ".design-status.json"), run.snapshot);
	runtime.tick();
	assert.match(runtime.widgets.get(WIDGET)[0], /different run/);
});

test("keeps factory instances, projects, and session switches separate", t => {
	const a = fixture(t);
	const b = fixture(t);
	const runA = addRun(a);
	const runB = addRun(b);
	const first = host(t, a.project);
	const second = host(t, b.project, { sessionId: "session-B" });
	first.emit("session_start");
	second.emit("session_start");
	first.command(relative(a.project, runA.root));
	second.command(relative(b.project, runB.root));
	first.state(taskEvent("Only project A"));
	assert.equal(existsSync(exportPath(runB, "session-B")), false);
	second.state(taskEvent("Only project B"));
	assert.equal(exported(runA).state.tasks.T1.title, "Only project A");
	assert.equal(exported(runB).state.tasks.T1.title, "Only project B");
	first.emit("session_before_switch");
	first.setSession("session-C");
	first.emit("session_switch");
	assert.equal(exported(runA).sessionId, "session-A");
	first.state(taskEvent("New session task"));
	assert.equal(exported(runA).sessionId, "session-A");
	first.command(relative(a.project, runA.root));
	assert.equal(exported(runA).sessionId, "session-C");
	first.context.cwd = b.project;
	first.emit("tool_call");
	assert.equal(exported(runB).sessionId, "session-B");
	first.state(taskEvent("New project task"));
	assert.equal(exported(runB).sessionId, "session-B");
	first.command(relative(b.project, runB.root));
	assert.equal(exported(runB).sessionId, "session-C");
	assert.equal(exported(runB).state.tasks.T1.title, "New project task");
});

test("subagents never start a footer timer or overwrite main-session task exports", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project, { agent: "sub" });
	runtime.state(taskEvent());
	runtime.emit("session_start");
	assert.equal(runtime.timers.size, 0);
	assert.equal(runtime.widgets.has(WIDGET), false);
	assert.equal(existsSync(exportPath(run)), false);
});

test("reports periodic non-UI watch instructions without ANSI or triggering a turn", t => {
	const f = fixture(t);
	const run = addRun(f);
	run.snapshot.nextAction = "Review\u001b[31m the result";
	writeJson(join(run.root, ".design-status.json"), run.snapshot);
	let now = Date.now();
	t.mock.method(Date, "now", () => now);
	const runtime = host(t, f.project, { mode: "print", hasUI: false });
	runtime.emit("session_start");
	assert.equal(runtime.reports.length, 1);
	assert.equal(runtime.widgets.has(WIDGET), false);
	assert.match(runtime.reports[0].message.content, /tools\/ui-design status 'work\/design-runs\/alpha' --watch/);
	assert.ok(runtime.reports[0].message.content.includes(run.url));
	assert.doesNotMatch(runtime.reports[0].message.content, /\u001b/u);
	assert.deepEqual(runtime.reports[0].options, { triggerTurn: false });
	runtime.tick();
	assert.equal(runtime.reports.length, 1);
	now += 30_001;
	runtime.tick();
	assert.equal(runtime.reports.length, 2);
});

test("uses notification fallback for UI clients without a native TUI", t => {
	const f = fixture(t);
	addRun(f);
	const runtime = host(t, f.project, { mode: "rpc" });
	runtime.emit("session_start");
	assert.equal(runtime.notifications.length, 1);
	assert.match(runtime.notifications[0].message, /--watch/);
	assert.equal(runtime.reports.length, 0);
	assert.equal(runtime.widgets.has(WIDGET), false);
});

test("cleans owned timers, widgets, status, and event subscriptions on shutdown", t => {
	const f = fixture(t);
	const run = addRun(f);
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	runtime.state(taskEvent());
	runtime.command(relative(f.project, run.root));
	const before = readFileSync(exportPath(run), "utf8");
	runtime.emit("session_shutdown");
	assert.equal(runtime.timers.size, 0);
	assert.equal(runtime.widgets.has(WIDGET), false);
	assert.equal(runtime.statuses.has(WIDGET), false);
	assert.equal(runtime.bus.get(TASK_EVENT).size, 0);
	assert.deepEqual(runtime.widgets.get("pi-tasks"), ["Existing Pi Tasks widget"]);
	runtime.state(taskEvent("Must never be exported"));
	assert.equal(readFileSync(exportPath(run), "utf8"), before);
});

test("contained timer fallback is unrefed and cleared on shutdown", t => {
	const f = fixture(t);
	const run = addRun(f);
	let callback;
	let unrefed = false;
	let cleared = false;
	const handle = { unref() { unrefed = true; } };
	t.mock.method(globalThis, "setInterval", handler => { callback = handler; return handle; });
	t.mock.method(globalThis, "clearInterval", timer => { assert.equal(timer, handle); cleared = true; });
	const runtime = host(t, f.project);
	delete runtime.context.setInterval;
	delete runtime.context.clearTimer;
	runtime.emit("session_start");
	assert.equal(unrefed, true);
	assert.equal(typeof callback, "function");
	runtime.context.ui.setWidget = () => { throw new Error("Unavailable UI"); };
	run.snapshot.nextAction = "Force a new render";
	writeJson(join(run.root, ".design-status.json"), run.snapshot);
	assert.doesNotThrow(() => callback());
	runtime.context.ui.setWidget = () => {};
	runtime.emit("session_shutdown");
	assert.equal(cleared, true);
});

test("reads supported legacy run records and handles missing or malformed snapshots conservatively", t => {
	const f = fixture(t);
	const run = addRun(f);
	writeJson(join(run.root, "run.json"), { schemaVersion: "1.0", id: "alpha" });
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	assert.equal(runtime.widgets.get(WIDGET).at(-1), run.url);
	unlinkSync(join(run.root, ".design-status.json"));
	runtime.tick();
	assert.match(runtime.widgets.get(WIDGET)[0], /Waiting/);
	assert.equal(runtime.widgets.get(WIDGET).at(-1), run.url);
	writeFileSync(join(run.root, ".design-status.json"), "not JSON");
	runtime.tick();
	assert.match(runtime.widgets.get(WIDGET)[0], /Progress unavailable/);
	assert.equal(runtime.widgets.get(WIDGET).at(-1), run.url);
});

test("unknown denominators do not invent percentages or completed inventory", t => {
	const f = fixture(t);
	addRun(f, "alpha", { gates: [], coverage: { required: 0, mockups: 0, verified: 0, inventoryComplete: false } });
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	const output = runtime.widgets.get(WIDGET).join("\n");
	assert.match(output, /0\/0 passed \(unknown\)/);
	assert.match(output, /0\/0 verified \(unknown declared\)/);
	assert.match(output, /inventory pending/);
	assert.doesNotMatch(output, /NaN|Infinity|100%/);
});

test("stays silent without a design server and begins reporting when one starts", t => {
	const f = fixture(t);
	let now = Date.now();
	t.mock.method(Date, "now", () => now);
	const runtime = host(t, f.project, { mode: "print", hasUI: false });
	runtime.emit("session_start");
	runtime.tick();
	now += 30_001;
	runtime.tick();
	assert.equal(runtime.reports.length, 0);
	assert.equal(runtime.widgets.has(WIDGET), false);
	assert.equal(runtime.statuses.has(WIDGET), false);
	assert.equal(runtime.timers.size, 1);
	const run = addRun(f);
	runtime.tick();
	assert.equal(runtime.reports.length, 1);
	assert.ok(runtime.reports[0].message.content.includes(run.url));
	unlinkSync(join(run.root, ".design-server.json"));
	now += 30_001;
	runtime.tick();
	runtime.tick();
	assert.equal(runtime.reports.length, 1);
	assert.equal(runtime.statuses.has(WIDGET), false);
});

test("clears an automatically bound revoked URL and discovers the next run without stale task export", t => {
	const f = fixture(t);
	const first = addRun(f);
	const runtime = host(t, f.project);
	runtime.emit("session_start");
	runtime.state(taskEvent("Only the first run"));
	unlinkSync(join(first.root, ".design-server.json"));
	runtime.tick();
	assert.equal(runtime.widgets.has(WIDGET), false);
	assert.equal(runtime.statuses.has(WIDGET), false);
	assert.deepEqual(runtime.widgets.get("pi-tasks"), ["Existing Pi Tasks widget"]);
	const second = addRun(f, "beta");
	runtime.tick();
	assert.equal(runtime.widgets.get(WIDGET).at(-1), second.url);
	assert.equal(existsSync(exportPath(second)), false);
	runtime.state(taskEvent("Only the next run"));
	assert.equal(existsSync(exportPath(second)), false);
	runtime.command(relative(f.project, second.root));
	assert.equal(exported(second).state.tasks.T1.title, "Only the next run");
	assert.equal(existsSync(exportPath(first)), false);
});

test("automatic observers cannot replace a director and explicit handoff keeps both session records", t => {
	const f = fixture(t);
	const run = addRun(f);
	const first = host(t, f.project);
	const second = host(t, f.project, { sessionId: "session-B" });
	first.emit("session_start");
	second.emit("session_start");
	first.state(taskEvent("Director work"));
	second.state(taskEvent("Unrelated work"));
	assert.equal(existsSync(join(run.root, "progress-pi-tasks-director.json")), false);
	first.command(relative(f.project, run.root));
	assert.equal(exported(run).sessionId, "session-A");
	assert.equal(exported(run).state.tasks.T1.title, "Director work");
	const retained = readFileSync(exportPath(run), "utf8");
	second.state(taskEvent("Still unrelated work"));
	assert.equal(readFileSync(exportPath(run), "utf8"), retained);
	assert.equal(existsSync(exportPath(run, "session-B")), false);
	second.command(relative(f.project, run.root));
	assert.equal(exported(run).sessionId, "session-B");
	assert.equal(exported(run).state.tasks.T1.title, "Still unrelated work");
	first.state(taskEvent("Late old director event"));
	assert.equal(exported(run).sessionId, "session-B");
	assert.equal(readFileSync(exportPath(run), "utf8"), retained);
});
