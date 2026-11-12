import { createHash, randomUUID } from "node:crypto";
import {
	closeSync,
	constants,
	fstatSync,
	fsyncSync,
	lstatSync,
	mkdirSync,
	openSync,
	readFileSync,
	readdirSync,
	renameSync,
	unlinkSync,
	writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, join, parse, relative, resolve, sep } from "node:path";

const WIDGET = "ui-design-progress";
const TASK_EVENT = "pi-tasks:state";
const POLL_MS = 2_000;
const REPORT_MS = 30_000;
const MAX_JSON_BYTES = 8 * 1024 * 1024;

// The bundled host has no resolvable package types in offline installations.
// This subset follows the public docs/extensions.md contract and is checked at entry.
type HostContext = {
	cwd: string;
	mode: "tui" | "rpc" | "json" | "print";
	hasUI: boolean;
	agent?: { kind: "main" | "sub" };
	sessionManager: { getSessionId(): string };
	ui: {
		setWidget(key: string, lines: string[] | undefined, options: { placement: "belowEditor" }): void;
		setStatus(key: string, text: string | undefined): void;
		notify(message: string, type: "info" | "warning"): void;
	};
	setInterval?: (callback: () => void, delay: number) => unknown;
	clearTimer?: (timer: unknown) => void;
};
type HostAPI = {
	on(event: string, handler: (event: unknown, context: unknown) => void): void;
	registerCommand(name: string, command: { description: string; handler(args: string, context: unknown): void }): void;
	events: { on(name: string, handler: (event: unknown) => void): () => void };
	sendMessage(message: { customType: string; content: string; display: true }, options: { triggerTurn: false }): void;
};
type JsonObject = { [key: string]: Json };
type Json = null | boolean | number | string | Json[] | JsonObject;
type PiTasks = {
	version: 1;
	reason: "session_start" | "session_tree" | "task_mutation";
	widgetId: "pi-tasks";
	state: JsonObject;
};
type Snapshot = {
	instanceId: string;
	observedAt: string;
	run: { id: string; themeId: string; phase: string; status: string };
	url: string;
	gates: ("passed" | "pending" | "failed")[];
	coverage: { required: number; mockups: number; verified: number; inventoryComplete: boolean };
	workers: string[];
	tasks: string[];
	nextAction: string;
	blockers: string[];
	warnings: string[];
	statistics: { artworks: number; evidence: number; passedEvidence: number; elapsedSeconds: number };
};
type Run = { root: string; id: string };
type Session = {
	context: HostContext;
	id: string;
	project: string;
	runs: string | undefined;
	run: (Run & { source: "auto" | "explicit" }) | undefined;
	tasks: PiTasks | undefined;
	exported: PiTasks | undefined;
	lastLines: string;
	lastReport: number;
	stopTimer: () => void;
};
type Lifecycle = { kind: "waiting"; tasks: PiTasks | undefined } | { kind: "active"; session: Session } | { kind: "stopped" };

function objectFields(value: unknown): Record<string, unknown> | undefined {
	if (typeof value !== "object" || value === null || Array.isArray(value)) return undefined;
	return value as Record<string, unknown>;
}

function isHost(value: unknown): value is HostAPI {
	const fields = objectFields(value);
	const events = objectFields(fields?.events);
	return fields !== undefined && typeof fields.on === "function" && typeof fields.registerCommand === "function"
		&& typeof fields.sendMessage === "function" && events !== undefined && typeof events.on === "function";
}

function isContext(value: unknown): value is HostContext {
	const fields = objectFields(value);
	const manager = objectFields(fields?.sessionManager);
	const ui = objectFields(fields?.ui);
	const agent = objectFields(fields?.agent);
	return fields !== undefined && typeof fields.cwd === "string" && typeof fields.hasUI === "boolean"
		&& (fields.mode === "tui" || fields.mode === "rpc" || fields.mode === "json" || fields.mode === "print")
		&& manager !== undefined && typeof manager.getSessionId === "function"
		&& ui !== undefined && typeof ui.setWidget === "function"
		&& typeof ui.setStatus === "function" && typeof ui.notify === "function"
		&& (fields.agent === undefined || (agent !== undefined && (agent.kind === "main" || agent.kind === "sub")))
		&& (fields.setInterval === undefined || typeof fields.setInterval === "function")
		&& (fields.clearTimer === undefined || typeof fields.clearTimer === "function");
}

function isMissing(error: unknown): boolean {
	return error instanceof Error && "code" in error && error.code === "ENOENT";
}

function portablePath(value: unknown): string {
	if (typeof value !== "string" || !value || isAbsolute(value) || /[\\:\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/u.test(value)
		|| value.split("/").some(part => !part || part === "." || part === "..")) {
		throw new Error("The design run path must be a plain project-relative path.");
	}
	return value;
}

function plainDirectory(path: string): string {
	const absolute = resolve(path);
	let cursor = parse(absolute).root;
	for (const part of absolute.slice(cursor.length).split(sep).filter(Boolean)) {
		cursor = join(cursor, part);
		const entry = lstatSync(cursor);
		if (!entry.isDirectory() || entry.isSymbolicLink()) throw new Error("Symlinked design directories are not permitted.");
	}
	return absolute;
}

function readJson(path: string, maxBytes = MAX_JSON_BYTES): unknown {
	plainDirectory(dirname(path));
	let descriptor: number | undefined;
	try {
		const entry = lstatSync(path);
		if (!entry.isFile() || entry.isSymbolicLink()) throw new Error("Design records must be plain files.");
		descriptor = openSync(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
		const opened = fstatSync(descriptor);
		if (!opened.isFile() || opened.size > maxBytes) throw new Error("Design record exceeds the safe JSON size.");
		const text = readFileSync(descriptor, "utf8");
		if (Buffer.byteLength(text) > maxBytes) throw new Error("Design record exceeds the safe JSON size.");
		const value: unknown = JSON.parse(text);
		return value;
	} catch (error) {
		if (isMissing(error)) return undefined;
		throw error;
	} finally {
		if (descriptor !== undefined) closeSync(descriptor);
	}
}

function text(value: unknown): string {
	if (typeof value !== "string" || value.length > 65_536) throw new Error("Invalid design progress text.");
	return value.replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/gu, " ");
}

function count(value: unknown): number {
	if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) throw new Error("Invalid design progress count.");
	return value;
}

function strings(value: unknown): string[] {
	if (!Array.isArray(value)) throw new Error("Invalid design progress list.");
	return value.map(text);
}

function serverUrl(value: unknown): string {
	if (typeof value !== "string" || /[\s\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/u.test(value)) throw new Error("Invalid design server URL.");
	const url = new URL(value);
	if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) {
		throw new Error("Invalid design server URL.");
	}
	return value;
}

function snapshot(value: unknown): Snapshot {
	const fields = objectFields(value);
	const run = objectFields(fields?.run);
	const server = objectFields(fields?.server);
	const coverage = objectFields(fields?.coverage);
	const statistics = objectFields(fields?.statistics);
	if (!fields || fields.schemaVersion !== "1.0" || !run || !server || !coverage || !statistics
		|| !Array.isArray(fields.gates) || !Array.isArray(fields.workers) || !Array.isArray(fields.tasks)) {
		throw new Error("Invalid design status snapshot.");
	}
	const instanceId = text(fields.instanceId);
	if (!instanceId) throw new Error("Missing design server instance identity.");
	const observedAt = text(fields.observedAt);
	if (!Number.isFinite(Date.parse(observedAt))) throw new Error("Invalid design status timestamp.");
	const gates = fields.gates.map(value => {
		const gate = objectFields(value);
		if (!gate || (gate.status !== "passed" && gate.status !== "pending" && gate.status !== "failed")) {
			throw new Error("Invalid design gate status.");
		}
		return gate.status;
	});
	const statuses = (items: unknown[]): string[] => items.map(item => text(objectFields(item)?.status));
	if (typeof coverage.inventoryComplete !== "boolean") throw new Error("Invalid coverage inventory status.");
	if (typeof statistics.elapsedSeconds !== "number" || !Number.isFinite(statistics.elapsedSeconds) || statistics.elapsedSeconds < 0) {
		throw new Error("Invalid design elapsed time.");
	}
	return {
		instanceId, observedAt,
		run: { id: text(run.id), themeId: text(run.themeId), phase: text(run.phase), status: text(run.status) },
		url: serverUrl(server.url),
		gates,
		coverage: { required: count(coverage.required), mockups: count(coverage.mockups),
			verified: count(coverage.verified), inventoryComplete: coverage.inventoryComplete },
		workers: statuses(fields.workers), tasks: statuses(fields.tasks),
		nextAction: text(fields.nextAction), blockers: strings(fields.blockers), warnings: strings(fields.warnings),
		statistics: { artworks: count(statistics.artworks), evidence: count(statistics.evidence),
			passedEvidence: count(statistics.passedEvidence), elapsedSeconds: statistics.elapsedSeconds },
	};
}

function isJson(value: unknown, depth = 0): value is Json {
	if (depth > 64) return false;
	if (value === null || typeof value === "string" || typeof value === "boolean") return true;
	if (typeof value === "number") return Number.isFinite(value);
	if (Array.isArray(value)) return value.every(item => isJson(item, depth + 1));
	const fields = objectFields(value);
	return fields !== undefined && Object.values(fields).every(item => isJson(item, depth + 1));
}

function isJsonObject(value: unknown): value is JsonObject {
	return objectFields(value) !== undefined && isJson(value);
}

function piTasks(value: unknown): PiTasks | undefined {
	const fields = objectFields(value);
	if (!fields || fields.version !== 1 || fields.widgetId !== "pi-tasks"
		|| (fields.reason !== "session_start" && fields.reason !== "session_tree" && fields.reason !== "task_mutation")
		|| !isJsonObject(fields.state)) return undefined;
	const state = fields.state;
	const tasks = objectFields(state.tasks);
	if (!tasks) return undefined;
	for (const [id, item] of Object.entries(tasks)) {
		const task = objectFields(item);
		if (!task || task.id !== id || typeof task.title !== "string"
			|| (task.status !== "pending" && task.status !== "active" && task.status !== "blocked"
				&& task.status !== "review" && task.status !== "done" && task.status !== "cancelled")
			|| typeof task.progress !== "number" || !Number.isFinite(task.progress) || task.progress < 0 || task.progress > 100) return undefined;
	}
	if (state.activeTaskId !== undefined && (typeof state.activeTaskId !== "string"
		|| !Object.hasOwn(tasks, state.activeTaskId))) return undefined;
	const encoded = JSON.stringify(state);
	if (Buffer.byteLength(encoded) > MAX_JSON_BYTES) return undefined;
	const cloned: unknown = JSON.parse(encoded);
	if (!isJsonObject(cloned)) return undefined;
	return { version: 1, reason: fields.reason, widgetId: "pi-tasks", state: cloned };
}

function configuredRuns(project: string): string {
	const value = readJson(join(project, "ui-design-studio.json"), 64 * 1024);
	const config = objectFields(value);
	if (value !== undefined && !config) throw new Error("ui-design-studio.json must be an object.");
	const paths = objectFields(config?.paths);
	if (config?.paths !== undefined && !paths) throw new Error("Configuration paths must be an object.");
	return join(project, portablePath(paths?.runs ?? "docs/design/runs"));
}

function readRun(root: string): Run {
	plainDirectory(root);
	const record = objectFields(readJson(join(root, "run.json")));
	if (!record || (record.schemaVersion !== "1.0" && record.schemaVersion !== "1.1") || typeof record.id !== "string" || !record.id) {
		throw new Error("The selected directory has no valid design run record.");
	}
	return { root, id: record.id };
}

function readLocator(root: string): { instanceId: string; url: string } | undefined {
	const value = readJson(join(root, ".design-server.json"), 64 * 1024);
	if (value === undefined) return undefined;
	const locator = objectFields(value);
	if (!locator || locator.schemaVersion !== "1.0" || locator.run !== root
		|| typeof locator.instanceId !== "string" || !locator.instanceId) throw new Error("Invalid design server locator.");
	return { instanceId: locator.instanceId, url: serverUrl(locator.url) };
}

function discover(runs: string): Run[] {
	let entries;
	try {
		plainDirectory(runs);
		entries = readdirSync(runs, { withFileTypes: true });
	} catch (error) {
		if (isMissing(error)) return [];
		throw error;
	}
	const result: Run[] = [];
	for (const entry of entries) {
		if (!entry.isDirectory() || entry.isSymbolicLink()) continue;
		try {
			const root = join(runs, portablePath(entry.name));
			if (readLocator(root)) result.push(readRun(root));
		} catch {
			// An unsafe or incomplete run must not hide a separate, usable run.
		}
	}
	return result;
}

function bar(done: number, total: number): string {
	const filled = total > 0 ? Math.max(0, Math.min(12, Math.floor(done * 12 / total))) : 0;
	return `[${"#".repeat(filled)}${".".repeat(12 - filled)}]`;
}

function linesFor(status: Snapshot): string[] {
	const passed = status.gates.filter(gate => gate === "passed").length;
	const pending = status.gates.filter(gate => gate === "pending").length;
	const failed = status.gates.filter(gate => gate === "failed").length;
	const coverage = status.coverage;
	const stats = status.statistics;
	const gatesPercent = status.gates.length > 0 ? `${Math.round(passed * 1000 / status.gates.length) / 10}%` : "unknown";
	const coveragePercent = coverage.required > 0 ? `${Math.round(coverage.verified * 1000 / coverage.required) / 10}%` : "unknown";
	const elapsed = `${Math.floor(stats.elapsedSeconds / 60)}m ${Math.floor(stats.elapsedSeconds % 60)}s`;
	const stale = Date.now() - Date.parse(status.observedAt) > 15_000;
	const lines = [
		`UI Design Studio | ${status.run.themeId} | ${status.run.phase} | ${status.run.status}${stale ? " | STALE snapshot" : ""}`,
		`Gates ${bar(passed, status.gates.length)} ${passed}/${status.gates.length} passed (${gatesPercent}) | ${pending} pending | ${failed} failed`,
		`Coverage ${bar(coverage.verified, coverage.required)} ${coverage.verified}/${coverage.required} verified (${coveragePercent} declared) | ${coverage.mockups} mockups | inventory ${coverage.inventoryComplete ? "complete" : "pending"}`,
		`Workers ${status.workers.filter(state => state === "active").length}/${status.workers.length} reported active | Tasks ${status.tasks.filter(state => state === "done").length}/${status.tasks.length} done`,
		`Artworks ${stats.artworks} | Evidence ${stats.passedEvidence}/${stats.evidence} passed | Elapsed ${elapsed}`,
		`Next ${status.nextAction || "not recorded"}`,
		`Blocker ${status.blockers.length ? status.blockers.join(" | ") : "none reported"}`,
	];
	if (status.warnings.length) lines.push(`Warning ${status.warnings.join(" | ")}`);
	// OMP wraps each Text row. One unmodified URL row stays below the ten-row limit.
	lines.push(status.url);
	return lines;
}

function writeProgress(root: string, destination: string, value: JsonObject): void {
	plainDirectory(root);
	plainDirectory(dirname(destination));
	readJson(destination);
	const temporary = join(dirname(destination), `.progress-${randomUUID()}.tmp`);
	let descriptor: number | undefined;
	try {
		descriptor = openSync(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | (constants.O_NOFOLLOW ?? 0), 0o600);
		writeFileSync(descriptor, JSON.stringify(value) + "\n", "utf8");
		fsyncSync(descriptor);
		closeSync(descriptor);
		descriptor = undefined;
		plainDirectory(root);
		plainDirectory(dirname(destination));
		readJson(destination);
		renameSync(temporary, destination);
	} finally {
		if (descriptor !== undefined) closeSync(descriptor);
		try { unlinkSync(temporary); } catch (error) { if (!isMissing(error)) throw error; }
	}
}

function exportTasks(session: Session, run: Run & { source: "auto" | "explicit" }): void {
	if (run.source !== "explicit" || !session.tasks || session.exported === session.tasks) return;
	if (readRun(run.root).id !== run.id) throw new Error("The active design run changed identity.");
	const director = objectFields(readJson(join(run.root, "progress-pi-tasks-director.json")));
	if (director?.runId !== run.id || director.sessionId !== session.id) return;
	const directory = join(run.root, "progress-pi-tasks");
	try { mkdirSync(directory, { mode: 0o700 }); }
	catch (error) {
		if (!(error instanceof Error) || !("code" in error) || error.code !== "EEXIST") throw error;
	}
	const key = createHash("sha256").update(session.id).digest("hex");
	writeProgress(run.root, join(directory, `${key}.json`), {
		...session.tasks, sessionId: session.id, runId: run.id, updatedAt: new Date().toISOString(),
	});
	session.exported = session.tasks;
}

function shellQuote(path: string): string {
	return `'${path.replaceAll("'", "'\\''")}'`;
}

export default function designProgress(value: unknown): void {
	if (!isHost(value)) throw new Error("UI Design Studio requires the documented OMP extension API.");
	const pi = value;
	let lifecycle: Lifecycle = { kind: "waiting", tasks: undefined };

	function hide(session: Session): void {
		try { session.context.ui.setWidget(WIDGET, undefined, { placement: "belowEditor" }); }
		finally { session.context.ui.setStatus(WIDGET, undefined); }
		session.lastLines = "";
		session.lastReport = 0;
	}

	function clear(session: Session): void {
		try { session.stopTimer(); }
		finally { hide(session); }
	}

	function display(session: Session, lines: string[]): void {
		const encoded = JSON.stringify(lines);
		session.context.ui.setStatus(WIDGET, lines[0]);
		if (session.context.hasUI && session.context.mode === "tui") {
			if (encoded !== session.lastLines) session.context.ui.setWidget(WIDGET, lines, { placement: "belowEditor" });
		} else if (Date.now() - session.lastReport >= REPORT_MS || !session.lastReport) {
			const run = session.run ? relative(session.project, session.run.root).split(sep).join("/") : "RUN";
			const report = `${lines.join("\n")}\nPersistent footer unavailable. Run tools/ui-design status ${shellQuote(run)} --watch for periodic progress.`;
			if (session.context.hasUI) session.context.ui.notify(report, "info");
			else pi.sendMessage({ customType: "ui-design-studio:progress", content: report, display: true }, { triggerTurn: false });
			session.lastReport = Date.now();
		}
		session.lastLines = encoded;
	}

	function refresh(): void {
		if (lifecycle.kind !== "active") return;
		const session = lifecycle.session;
		if (session.context.sessionManager.getSessionId() !== session.id) {
			clear(session);
			lifecycle = { kind: "waiting", tasks: undefined };
			return;
		}
		let url: string | undefined;
		try {
			const runs = configuredRuns(session.project);
			if (session.runs !== undefined && session.runs !== runs) {
				session.run = undefined;
				session.tasks = undefined;
				session.exported = undefined;
			}
			session.runs = runs;
			if (!session.run) {
				const candidates = discover(runs);
				if (candidates.length !== 1) {
					if (candidates.length) display(session, ["UI Design Studio | Multiple design servers. Select /ui-design-progress RUN."]);
					else hide(session);
					return;
				}
				const candidate = candidates[0];
				if (!candidate) return;
				session.run = { ...candidate, source: "auto" };
			}
			const run = session.run;
			const locator = readLocator(run.root);
			if (!locator) {
				if (run.source === "explicit") {
					display(session, ["UI Design Studio | Design server stopped. Start tools/ui-design design-serve RUN."]);
				} else {
					session.run = undefined;
					session.tasks = undefined;
					session.exported = undefined;
					hide(session);
				}
				return;
			}
			url = locator.url;
			const raw = readJson(join(run.root, ".design-status.json"));
			if (raw === undefined) {
				display(session, ["UI Design Studio | Waiting for the design server status snapshot.", url]);
				return;
			}
			const status = snapshot(raw);
			if (status.run.id !== run.id) throw new Error("Design status belongs to a different run.");
			if (locator.instanceId !== status.instanceId || url !== status.url) {
				throw new Error("Design status belongs to a different server.");
			}
			const lines = linesFor(status);
			try { exportTasks(session, run); }
			catch (error) { lines.splice(lines.length - 1, 0, `Pi Tasks export unavailable. ${text(error instanceof Error ? error.message : String(error))}`); }
			display(session, lines);
		} catch (error) {
			if (!session.run) {
				hide(session);
				return;
			}
			const lines = [`UI Design Studio | Progress unavailable. ${text(error instanceof Error ? error.message : String(error))}`];
			if (url) lines.push(url);
			display(session, lines);
		}
	}

	function start(context: unknown): void {
		if (!isContext(context) || context.agent?.kind === "sub" || lifecycle.kind === "stopped") return;
		const id = context.sessionManager.getSessionId();
		if (typeof id !== "string" || !id) return;
		const project = resolve(context.cwd);
		if (lifecycle.kind === "active" && lifecycle.session.id === id && lifecycle.session.project === project) {
			lifecycle.session.context = context;
			refresh();
			return;
		}
		const tasks = lifecycle.kind === "waiting" ? lifecycle.tasks : undefined;
		if (lifecycle.kind === "active") clear(lifecycle.session);
		const session: Session = { context, id, project, runs: undefined, run: undefined, tasks, exported: undefined,
			lastLines: "", lastReport: 0, stopTimer: () => {} };
		lifecycle = { kind: "active", session };
		if (context.setInterval && context.clearTimer) {
			const timer = context.setInterval(refresh, POLL_MS);
			session.stopTimer = () => context.clearTimer?.(timer);
		} else {
			const timer = setInterval(() => {
				try { refresh(); }
				catch { /* Background failures must never escape into the host process. */ }
			}, POLL_MS);
			timer.unref();
			session.stopTimer = () => clearInterval(timer);
		}
		refresh();
	}

	const unsubscribe = pi.events.on(TASK_EVENT, event => {
		try {
			const tasks = piTasks(event);
			if (!tasks || lifecycle.kind === "stopped") return;
			if (lifecycle.kind === "waiting") lifecycle.tasks = tasks;
			else {
				lifecycle.session.tasks = tasks;
				refresh();
			}
		} catch {
			// Malformed observer data must not interrupt a persisted Pi Tasks transition.
		}
	});
	for (const event of ["session_start", "session_switch", "session_branch", "session_tree", "tool_call", "tool_result", "turn_start"]) {
		pi.on(event, (_event, context) => start(context));
	}
	pi.on("session_before_switch", () => {
		if (lifecycle.kind === "active") clear(lifecycle.session);
		lifecycle = { kind: "waiting", tasks: undefined };
	});
	pi.on("session_shutdown", () => {
		const previous = lifecycle;
		lifecycle = { kind: "stopped" };
		try { if (previous.kind === "active") clear(previous.session); }
		finally { unsubscribe(); }
	});
	pi.registerCommand("ui-design-progress", {
		description: "Pin a design run and select this session as its task director, or use auto for read-only discovery.",
		handler(args, context) {
			start(context);
			if (lifecycle.kind !== "active") return;
			const session = lifecycle.session;
			try {
				const argument = args.trim();
				if (argument && argument !== "auto") {
					const runs = configuredRuns(session.project);
					const root = join(session.project, portablePath(argument));
					const child = relative(runs, root);
					if (!child || child === ".." || child.startsWith(`..${sep}`) || isAbsolute(child)) {
						throw new Error("Select a run inside the configured paths.runs directory.");
					}
					session.run = { ...readRun(root), source: "explicit" };
					session.runs = runs;
					writeProgress(root, join(root, "progress-pi-tasks-director.json"), {
						schemaVersion: "1.0", runId: session.run.id, sessionId: session.id,
					});
				} else if (argument === "auto") session.run = undefined;
				session.exported = undefined;
				refresh();
			} catch (error) {
				session.context.ui.notify(text(error instanceof Error ? error.message : String(error)), "warning");
			}
		},
	});
}
