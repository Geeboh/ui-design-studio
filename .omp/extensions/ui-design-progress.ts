import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import {
	accessSync,
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
	statSync,
} from "node:fs";
import { delimiter, dirname, isAbsolute, join, parse, relative, resolve, sep } from "node:path";
import { homedir } from "node:os";
import { request as httpRequest } from "node:http";
import { isIP } from "node:net";

const WIDGET = "ui-design-progress";
const TASK_EVENT = "pi-tasks:state";
const POLL_MS = 2_000;
const REPORT_MS = 30_000;
const MAX_JSON_BYTES = 8 * 1024 * 1024;
const MAX_READINESS_BYTES = 128 * 1024;
const STARTUP_MS = 8_000;
const MAX_RESTARTS = 3;

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
	on(event: string, handler: (event: unknown, context: unknown) => void | Promise<void>): void;
	registerCommand(name: string, command: { description: string; handler(args: string, context: unknown): void | Promise<void> }): void;
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
type Connection = {
	instanceId: string;
	repo: string;
	observedAt: string;
	localUrl: string;
	lanUrls: string[];
	qrUrl: string;
	text: string;
	selectedRun: { run: string; instanceId: string } | null;
};
type ConnectionSelection = { kind: "none" } | { kind: "selected"; connection: Connection }
	| { kind: "ambiguous"; ids: string[] } | { kind: "unavailable"; id: string };
type DashboardChild = {
	process: ChildProcessWithoutNullStreams;
	readiness: Promise<unknown>;
	exited: Promise<void>;
	stop(): Promise<void>;
};
type DashboardOwner = { kind: "owned"; child: DashboardChild } | { kind: "borrowed" };
type DashboardSupervisor =
	| { kind: "idle" }
	| { kind: "starting"; generation: number; attempt: number; child: DashboardChild; promise: Promise<Connection | undefined> }
	| { kind: "selecting"; generation: number; promise: Promise<Connection | undefined> }
	| { kind: "live"; generation: number; attempt: number; since: number; connection: Connection; owner: DashboardOwner }
	| { kind: "recovering"; promise: Promise<Connection | undefined>; cancel(): void }
	| { kind: "unavailable"; warning: string }
	| { kind: "missing"; warning: string }
	| { kind: "stopped" };
type DiscoveryProof =
	| { kind: "none" }
	| { kind: "pending"; connection: Connection }
	| { kind: "verified" | "rejected"; connection: Connection; checkedAt: number };
type Session = {
	context: HostContext;
	id: string;
	project: string;
	runs: string | undefined;
	run: (Run & { source: "auto" | "explicit" }) | undefined;
	dashboardId: string | undefined;
	dashboardGeneration: number;
	dashboard: DashboardSupervisor;
	discoveryProof: DiscoveryProof;
	children: Set<DashboardChild>;
	banners: number;
	resumeRun: Run | undefined;
	openedRuns: Set<string>;
	opening: Promise<void> | undefined;
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

function connectionUrl(value: unknown, loopback: boolean): string {
	const raw = serverUrl(value);
	const url = new URL(raw);
	const octets = url.hostname.split(".").map(Number);
	if (url.protocol !== "http:" || isIP(url.hostname) !== 4 || Number(url.port || 80) < 1 || url.pathname !== "/"
		|| url.search || !/^#token=[A-Za-z0-9_-]{16,256}$/u.test(url.hash)
		|| (loopback ? url.hostname !== "127.0.0.1"
			: octets[0] === 0 || octets[0] === 127 || (octets[0] ?? 0) >= 224
				|| (octets[0] === 169 && octets[1] === 254))) {
		throw new Error("Invalid dashboard connection URL.");
	}
	return raw;
}

function connectionRecord(value: unknown, project: string, id: string, readiness = false): Connection {
	const fields = objectFields(value);
	if (!fields || fields.schemaVersion !== "1.0" || fields.state !== "live" || fields.run !== null
		|| fields.instanceId !== id || !/^[0-9a-f]{48}$/u.test(id) || fields.repo !== plainDirectory(project)
		|| typeof fields.observedAt !== "string"
		|| (!readiness && (typeof fields.startedAt !== "string" || !Number.isFinite(Date.parse(fields.startedAt))))
		|| !Array.isArray(fields.lanUrls) || fields.lanUrls.length > 256) throw new Error("Invalid dashboard connection record.");
	const observed = Date.parse(fields.observedAt);
	if (!Number.isFinite(observed) || Date.now() - observed > 15_000 || observed - Date.now() > 5_000) {
		throw new Error("Dashboard connection record has expired.");
	}
	const localUrl = connectionUrl(fields.localUrl, true);
	const local = new URL(localUrl);
	const lanUrls = fields.lanUrls.map(value => {
		const raw = connectionUrl(value, false);
		const url = new URL(raw);
		if (url.port !== local.port || url.hash !== local.hash) throw new Error("Dashboard aliases do not match.");
		return raw;
	});
	const qrUrl = lanUrls[0] ?? localUrl;
	if (fields.qrUrl !== qrUrl || typeof fields.text !== "string" || fields.text.length > 65_536) {
		throw new Error("Invalid dashboard command text.");
	}
	const commandText = fields.text;
	const hints = readiness ? [" (/ui-design-dashboard stop to stop)"] : [""];
	const headings = hints.map(hint =>
		`[ok] Dashboard live → ${localUrl}${hint}\n${lanUrls.length ? lanUrls.map(url => `[lan] ${url}`).join("\n") : "[lan] unavailable"}\n\n`);
	const heading = headings.find(value => commandText.startsWith(value));
	if (!heading || !/^[ \n\u2580-\u259f]+$/u.test(commandText.slice(heading.length))
		|| !/[\u2580-\u259f]/u.test(commandText.slice(heading.length))) throw new Error("Invalid dashboard QR output.");
	let selectedRun: Connection["selectedRun"] = null;
	if (fields.selectedRun !== null && !(readiness && fields.selectedRun === undefined)) {
		const selected = objectFields(fields.selectedRun);
		if (!selected || typeof selected.instanceId !== "string" || !/^[0-9a-f]{48}$/u.test(selected.instanceId)) {
			throw new Error("Invalid selected dashboard run.");
		}
		selectedRun = { run: portablePath(selected.run), instanceId: selected.instanceId };
	}
	return { instanceId: id, repo: project, observedAt: fields.observedAt, localUrl, lanUrls, qrUrl, text: fields.text, selectedRun };
}

function connections(session: Session): ConnectionSelection {
	const directory = join(session.project, ".ui-design-studio", "runtime", "mcp");
	let entries;
	try {
		plainDirectory(directory);
		entries = readdirSync(directory, { withFileTypes: true });
	} catch (error) {
		if (!isMissing(error)) throw error;
		return session.dashboardId ? { kind: "unavailable", id: session.dashboardId } : { kind: "none" };
	}
	const candidates: Connection[] = [];
	const expired: string[] = [];
	for (const entry of entries) {
		if (!entry.isFile() || entry.isSymbolicLink() || !/^[0-9a-f]{48}\.json$/u.test(entry.name)) continue;
		try {
			candidates.push(connectionRecord(readJson(join(directory, entry.name), 128 * 1024), session.project, entry.name.slice(0, -5)));
		} catch (error) {
			if (error instanceof Error && error.message === "Dashboard connection record has expired.") expired.push(entry.name.slice(0, -5));
			continue;
		}
	}
	if (session.dashboardId) {
		const connection = candidates.find(value => value.instanceId === session.dashboardId);
		return connection ? { kind: "selected", connection } : { kind: "unavailable", id: session.dashboardId };
	}
	if (candidates.length > 1) return { kind: "ambiguous", ids: candidates.map(value => value.instanceId).sort() };
	const connection = candidates[0];
	return connection ? { kind: "selected", connection } : expired[0] ? { kind: "unavailable", id: expired[0] } : { kind: "none" };
}

function connectionLines(connection: Connection): string[] {
	return [
		`UI Design Studio | Connection ${connection.instanceId}`,
		connection.localUrl,
		connection.lanUrls[0] ?? "LAN unavailable",
		`ui-design dashboard-info --repo ${shellQuote(connection.repo)} --session ${connection.instanceId}`,
	];
}

function probeConnection(connection: Connection): Promise<void> {
	const { promise, resolve, reject } = Promise.withResolvers<void>();
	const endpoint = new URL(connection.localUrl);
	const token = endpoint.hash.slice("#token=".length);
	endpoint.hash = "";
	endpoint.pathname = "/api/identity";
	const request = httpRequest(endpoint, { method: "GET", agent: false, headers: { Authorization: `Bearer ${token}` } }, response => {
		const chunks: Buffer[] = [];
		let length = 0;
		response.on("data", (chunk: Buffer) => {
			length += chunk.length;
			if (length > 64 * 1024) request.destroy(new Error("Dashboard identity exceeds the safe size."));
			else chunks.push(chunk);
		});
		response.on("error", reject);
		response.on("end", () => {
			clearTimeout(timer);
			try {
				const identity = objectFields(JSON.parse(Buffer.concat(chunks).toString("utf8")));
				if (response.statusCode !== 200 || identity?.instanceId !== connection.instanceId || identity.repo !== connection.repo) {
					throw new Error("Dashboard identity does not match the selected connection.");
				}
				resolve();
			} catch (error) { reject(error); }
		});
	});
	const timer = setTimeout(() => request.destroy(new Error("Dashboard identity probe timed out.")), 2_000);
	request.on("error", error => { clearTimeout(timer); reject(error); });
	request.end();
	return promise;
}

function dashboardRuntime(project: string): string {
	const binary = process.platform === "win32" ? "ui-design.exe" : "ui-design";
	const bin = process.platform === "win32" ? "Scripts" : "bin";
	const candidates = [
		join(project, ".venv-ui-design", bin, binary),
		join(homedir(), ".local", "share", "ui-design-studio", "mcp", bin, binary),
		...(process.env.PATH ?? "").split(delimiter).filter(Boolean).map(directory => resolve(project, directory, binary)),
	];
	for (const candidate of candidates) {
		try {
			if (!statSync(candidate).isFile()) continue;
			accessSync(candidate, constants.X_OK);
			return candidate;
		} catch { /* A missing runtime candidate must not hide a later installed runtime. */ }
	}
	throw new Error("Dashboard runtime is missing. From the UI Design Studio release directory, run bash install.sh --mcp-global, then /ui-design-dashboard start.");
}

function diagnostic(value: unknown): string {
	return text(String(value).replace(/https?:\/\/[^\s]+/giu, "[URL redacted]")
		.replace(/\bBearer\s+\S+/giu, "Bearer [redacted]")
		.replace(/(?:#token=|token[=:]\s*)[A-Za-z0-9_-]+/giu, "token=[redacted]")
		.replace(/[A-Za-z0-9_-]{32,}/gu, "[redacted]"));
}

function spawnDashboard(project: string): DashboardChild {
	const child = spawn(dashboardRuntime(project), ["dashboard-serve", "--repo", project, "--json", "--parent-stdio"], {
		cwd: project, shell: false, detached: false, stdio: ["pipe", "pipe", "pipe"],
	});
	const ready = Promise.withResolvers<unknown>();
	const exited = Promise.withResolvers<void>();
	let output = Buffer.alloc(0);
	let stderr = "";
	let settled = false;
	let stopped: Promise<void> | undefined;
	const fail = (message: string): void => {
		if (settled) return;
		settled = true;
		clearTimeout(timer);
		ready.reject(new Error(message));
	};
	const timer = setTimeout(() => fail("Dashboard startup timed out."), STARTUP_MS);
	child.stdout.on("data", (chunk: Buffer) => {
		if (settled) return;
		if (output.length + chunk.length > MAX_READINESS_BYTES) {
			fail("Dashboard readiness exceeds the safe JSON size.");
			return;
		}
		output = Buffer.concat([output, chunk]);
		const newline = output.indexOf(10);
		if (newline < 0) return;
		try {
			if (output.subarray(newline + 1).toString("utf8").trim()) throw new Error();
			const value: unknown = JSON.parse(output.subarray(0, newline).toString("utf8"));
			settled = true;
			clearTimeout(timer);
			ready.resolve(value);
		} catch { fail("Dashboard returned invalid JSON readiness."); }
		output = Buffer.alloc(0);
	});
	child.stderr.on("data", (chunk: Buffer) => {
		stderr = diagnostic(stderr + chunk.toString("utf8")).slice(-4_096);
	});
	child.stdin.on("error", () => {});
	child.once("error", error => {
		fail(`Dashboard could not start. ${diagnostic(error.message)}`);
		exited.resolve();
	});
	child.once("close", () => {
		fail(`Dashboard exited before readiness.${stderr ? " The runtime reported startup errors; run dashboard-serve directly for diagnostics." : ""}`);
		exited.resolve();
	});
	return {
		process: child, readiness: ready.promise, exited: exited.promise,
		stop() {
			if (stopped) return stopped;
			fail("Dashboard startup was stopped.");
			child.stdin.end();
			const terminate = setTimeout(() => child.kill("SIGTERM"), 1_000);
			const kill = setTimeout(() => child.kill("SIGKILL"), 2_000);
			const deadline = Promise.withResolvers<void>();
			const timeout = setTimeout(deadline.resolve, 3_000);
			stopped = Promise.race([exited.promise, deadline.promise]).then(() => {
				clearTimeout(timeout); clearTimeout(terminate); clearTimeout(kill);
			});
			return stopped;
		},
	};
}

function openConnectionRun(connection: Connection, run: string): Promise<void> {
	const { promise, resolve, reject } = Promise.withResolvers<void>();
	const endpoint = new URL(connection.localUrl);
	const token = endpoint.hash.slice("#token=".length);
	endpoint.hash = "";
	endpoint.pathname = "/api/open";
	const body = JSON.stringify({ run });
	const request = httpRequest(endpoint, { method: "POST", agent: false, headers: {
		Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body),
	} }, response => {
		let length = 0;
		response.on("data", (chunk: Buffer) => {
			length += chunk.length;
			if (length > MAX_READINESS_BYTES) request.destroy(new Error("Dashboard open response exceeds the safe size."));
		});
		response.on("error", reject);
		response.on("end", () => {
			clearTimeout(timer);
			if (response.statusCode === 200) resolve();
			else reject(new Error("Dashboard could not open the selected run."));
		});
	});
	const timer = setTimeout(() => request.destroy(new Error("Dashboard run selection timed out.")), STARTUP_MS);
	request.on("error", error => { clearTimeout(timer); reject(error); });
	request.end(body);
	return promise;
}

function unfinished(run: Run): boolean {
	const record = objectFields(readJson(join(run.root, "run.json")));
	return record?.id === run.id && !["complete", "completed", "done", "cancelled", "registered"].includes(String(record.status))
		&& !["complete", "completed"].includes(String(record.phase));
}

function resumableRuns(runs: string): Run[] {
	try {
		plainDirectory(runs);
		return readdirSync(runs, { withFileTypes: true }).flatMap(entry => {
			if (!entry.isDirectory() || entry.isSymbolicLink()) return [];
			try {
				const run = readRun(join(runs, portablePath(entry.name)));
				return unfinished(run) ? [run] : [];
			} catch { return []; }
		});
	} catch (error) {
		if (isMissing(error)) return [];
		throw error;
	}
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

	function current(session: Session, generation = session.dashboardGeneration): boolean {
		return lifecycle.kind === "active" && lifecycle.session === session && session.dashboardGeneration === generation
			&& session.context.agent?.kind !== "sub" && session.context.sessionManager.getSessionId() === session.id
			&& resolve(session.context.cwd) === session.project;
	}

	function clear(session: Session): Promise<void> {
		if (session.dashboard.kind === "recovering") session.dashboard.cancel();
		session.dashboardGeneration++;
		session.dashboard = { kind: "stopped" };
		try { session.stopTimer(); }
		finally { hide(session); }
		return Promise.all([...session.children].map(child => child.stop())).then(() => {});
	}

	function banner(session: Session, connection: Connection): void {
		if (!current(session) || session.dashboard.kind !== "live" || session.dashboard.connection.instanceId !== connection.instanceId) return;
		pi.sendMessage({ customType: "ui-design-studio:dashboard", content: connection.text, display: true }, { triggerTurn: false });
		session.banners++;
	}

	function recovery(session: Session, attempt: number, warning: string): void {
		if (!current(session)) return;
		const generation = ++session.dashboardGeneration;
		session.dashboardId = undefined;
		if (attempt > MAX_RESTARTS) {
			session.dashboard = { kind: "unavailable", warning: `${warning} Automatic recovery stopped. Use /ui-design-dashboard start.` };
			session.context.ui.notify(session.dashboard.warning, "warning");
		} else {
			const flight = Promise.withResolvers<Connection | undefined>();
			const timer = setTimeout(() => {
				if (!current(session, generation)) { flight.resolve(undefined); return; }
				session.dashboard = { kind: "idle" };
				ensureDashboard(session, attempt).then(flight.resolve, flight.reject);
			}, Math.min(4_000, 500 * 2 ** (attempt - 1)));
			session.dashboard = { kind: "recovering", promise: flight.promise,
				cancel() { clearTimeout(timer); flight.resolve(undefined); } };
		}
		refresh();
	}

	function ensureDashboard(session: Session, attempt = 0): Promise<Connection | undefined> {
		if (!current(session)) return Promise.resolve(undefined);
		const state = session.dashboard;
		if (state.kind === "live") return Promise.resolve(state.connection);
		if (state.kind === "starting" || state.kind === "selecting" || state.kind === "recovering") return state.promise;
		if (state.kind === "stopped" || state.kind === "unavailable" || state.kind === "missing") return Promise.resolve(undefined);
		const generation = ++session.dashboardGeneration;
		let child: DashboardChild;
		try { child = spawnDashboard(session.project); }
		catch (error) {
			const warning = diagnostic(error instanceof Error ? error.message : error);
			session.dashboard = { kind: "missing", warning };
			session.context.ui.notify(warning, "warning");
			return Promise.resolve(undefined);
		}
		session.children.add(child);
		const flight = Promise.withResolvers<Connection | undefined>();
		session.dashboard = { kind: "starting", generation, attempt, child, promise: flight.promise };
		child.exited.then(() => {
			session.children.delete(child);
			if (!current(session, generation)) return;
			const state = session.dashboard;
			if (state.kind === "live" && state.owner.kind === "owned" && state.owner.child === child) {
				recovery(session, Date.now() - state.since > REPORT_MS ? 1 : attempt + 1, "Dashboard process exited.");
			}
		});
		void (async () => {
			try {
				const value = await child.readiness;
				const id = objectFields(value)?.instanceId;
				if (typeof id !== "string") throw new Error("Dashboard readiness is missing its instance identity.");
				const connection = connectionRecord(value, session.project, id, true);
				await probeConnection(connection);
				if (!current(session, generation)) { await child.stop(); flight.resolve(undefined); return; }
				if (child.process.exitCode !== null || child.process.signalCode !== null) throw new Error("Dashboard exited during readiness verification.");
				session.dashboardId = id;
				session.dashboard = { kind: "live", generation, attempt, since: Date.now(), connection, owner: { kind: "owned", child } };
				await synchronizeRun(session);
				if (current(session, generation)) {
					banner(session, connection);
					refresh();
				}
				flight.resolve(current(session, generation) ? connection : undefined);
			} catch (error) {
				await child.stop();
				if (current(session, generation)) {
					const warning = diagnostic(error instanceof Error ? error.message : error);
					session.context.ui.notify(warning, "warning");
					recovery(session, attempt + 1, warning);
				}
				flight.resolve(undefined);
			}
		})();
		refresh();
		return flight.promise;
	}

	function synchronizeRun(session: Session, explicit?: Run): Promise<void> {
		if (!current(session) || session.dashboard.kind !== "live") return Promise.resolve();
		if (session.opening) return session.opening.then(() => explicit ? synchronizeRun(session, explicit) : undefined);
		const state = session.dashboard;
		const generation = session.dashboardGeneration;
		let run: Run | undefined = explicit;
		try {
			if (!run && !state.connection.selectedRun && session.resumeRun && unfinished(session.resumeRun)) run = session.resumeRun;
			if (!run) {
				const candidates = resumableRuns(configuredRuns(session.project)).filter(item => !session.openedRuns.has(item.root));
				if (candidates.length === 1) run = candidates[0];
			}
			if (!run || (!explicit && session.openedRuns.has(run.root) && !session.resumeRun)) return Promise.resolve();
			if (!explicit && state.connection.selectedRun?.run === relative(session.project, run.root).split(sep).join("/")) return Promise.resolve();
			const selected = run;
			session.resumeRun = selected;
			session.opening = openConnectionRun(state.connection, relative(session.project, selected.root).split(sep).join("/"))
				.then(() => {
					if (!current(session, generation) || session.dashboard !== state) return;
					session.openedRuns.add(selected.root);
					session.resumeRun = selected;
					refresh();
				}).catch(error => {
					if (current(session, generation)) session.context.ui.notify(diagnostic(error instanceof Error ? error.message : error), "warning");
				}).finally(() => { session.opening = undefined; });
			return session.opening;
		} catch (error) {
			session.context.ui.notify(diagnostic(error instanceof Error ? error.message : error), "warning");
			return Promise.resolve();
		}
	}

	function selectedConnection(session: Session): ConnectionSelection {
		const state = session.dashboard;
		if (state.kind !== "live") {
			const selection = connections(session);
			if (selection.kind !== "selected") return selection;
			const connection = selection.connection;
			const proof = session.discoveryProof;
			const same = proof.kind !== "none" && proof.connection.instanceId === connection.instanceId
				&& proof.connection.localUrl === connection.localUrl && proof.connection.text === connection.text;
			if (same && proof.kind === "pending") return { kind: "none" };
			if (same && proof.kind !== "none" && proof.kind !== "pending" && Date.now() - proof.checkedAt < POLL_MS) {
				return proof.kind === "verified" ? selection : { kind: "none" };
			}
			const pending: DiscoveryProof = { kind: "pending", connection };
			session.discoveryProof = pending;
			void probeConnection(connection).then(() => {
				if (!current(session) || session.discoveryProof !== pending) return;
				session.discoveryProof = { kind: "verified", connection, checkedAt: Date.now() };
				refresh();
			}).catch(() => {
				if (!current(session) || session.discoveryProof !== pending) return;
				session.discoveryProof = { kind: "rejected", connection, checkedAt: Date.now() };
				refresh();
			});
			return { kind: "none" };
		}
		const selection = connections(session);
		if (selection.kind !== "selected" || selection.connection.instanceId !== state.connection.instanceId
			|| selection.connection.localUrl !== state.connection.localUrl) return { kind: "unavailable", id: state.connection.instanceId };
		const connection = selection.connection;
		if (state.owner.kind === "owned") {
			connection.text = connection.text.replace(`[ok] Dashboard live → ${connection.localUrl}\n`,
				`[ok] Dashboard live → ${connection.localUrl} (/ui-design-dashboard stop to stop)\n`);
		}
		state.connection = connection;
		if (!session.opening && connection.selectedRun) {
			const root = join(session.project, connection.selectedRun.run);
			const scope = relative(configuredRuns(session.project), root);
			if (!scope || scope === ".." || scope.startsWith(`..${sep}`) || isAbsolute(scope)) {
				throw new Error("Selected connection run is outside paths.runs.");
			}
			const locator = readLocator(root);
			if (locator?.instanceId === connection.selectedRun.instanceId) {
				const selected = readRun(root);
				if (unfinished(selected)) {
					session.resumeRun = selected;
					session.openedRuns.add(selected.root);
				}
			}
		}
		if (session.resumeRun && !session.opening && (!connection.selectedRun || !readLocator(session.resumeRun.root))) {
			session.resumeRun = undefined;
		}
		return { kind: "selected", connection };
	}

	function display(session: Session, lines: string[]): void {
		const encoded = JSON.stringify(lines);
		session.context.ui.setStatus(WIDGET, lines[0]);
		if (session.context.hasUI && session.context.mode === "tui") {
			if (encoded !== session.lastLines) session.context.ui.setWidget(WIDGET, lines, { placement: "belowEditor" });
		} else if (Date.now() - session.lastReport >= REPORT_MS || !session.lastReport) {
			const run = session.run ? relative(session.project, session.run.root).split(sep).join("/") : undefined;
			const report = `${lines.join("\n")}\nPersistent footer unavailable.${run ? ` Run tools/ui-design status ${shellQuote(run)} --watch for periodic progress.` : ""}`;
			if (session.context.hasUI) session.context.ui.notify(report, "info");
			else pi.sendMessage({ customType: "ui-design-studio:progress", content: report, display: true }, { triggerTurn: false });
			session.lastReport = Date.now();
		}
		session.lastLines = encoded;
	}

	function refresh(): void {
		if (lifecycle.kind !== "active") return;
		const session = lifecycle.session;
		if (!current(session)) {
			clear(session);
			lifecycle = { kind: "waiting", tasks: undefined };
			return;
		}
		if (session.dashboard.kind === "stopped") {
			display(session, ["UI Design Studio | Dashboard stopped. Use /ui-design-dashboard start."]);
			return;
		}
		if (session.dashboard.kind === "unavailable") {
			display(session, [`UI Design Studio | Dashboard unavailable. ${session.dashboard.warning}`]);
			return;
		}
		if (session.dashboard.kind === "starting" || session.dashboard.kind === "selecting" || session.dashboard.kind === "recovering") {
			display(session, [`UI Design Studio | Dashboard ${session.dashboard.kind === "recovering" ? "recovering" : "starting"}.`]);
			return;
		}
		let url: string | undefined;
		let pinned: string[] = [];
		try {
			const runs = configuredRuns(session.project);
			if (session.runs !== undefined && session.runs !== runs) {
				session.run = undefined;
				session.tasks = undefined;
				session.exported = undefined;
			}
			session.runs = runs;
			let selection = selectedConnection(session);
			if (selection.kind === "unavailable" && !session.dashboardId && session.run?.source !== "explicit" && discover(runs).length) {
				selection = { kind: "none" };
				session.run = undefined;
			}
			const connection = selection.kind === "selected" ? selection.connection : undefined;
			if (connection) pinned = connectionLines(connection);
			if (session.run?.source !== "explicit" && selection.kind !== "none") {
				session.run = undefined;
				session.exported = undefined;
				if (selection.kind === "ambiguous") {
					display(session, ["UI Design Studio | Multiple dashboard connections.", ...selection.ids,
						"Select /ui-design-dashboard SESSION_ID."]);
					return;
				}
				if (selection.kind === "unavailable") {
					display(session, [`UI Design Studio | Connection ${selection.id} unavailable.`]);
					return;
				}
				const selected = connection?.selectedRun;
				if (!selected) {
					display(session, [...pinned, "Waiting for a design run. Start or resume from your coding client."]);
					return;
				}
				const root = join(session.project, selected.run);
				const child = relative(runs, root);
				if (!child || child === ".." || child.startsWith(`..${sep}`) || isAbsolute(child)) {
					throw new Error("Selected connection run is outside paths.runs.");
				}
				const locator = readLocator(root);
				if (!locator || locator.instanceId !== selected.instanceId) {
					display(session, [...pinned, "Selected run stopped. Resume explicitly from your coding client."]);
					return;
				}
				session.run = { ...readRun(root), source: "auto" };
			}
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
					display(session, [...pinned, "UI Design Studio | Design server stopped. Start tools/ui-design design-serve RUN."]);
				} else {
					session.run = undefined;
					session.tasks = undefined;
					session.exported = undefined;
					if (pinned.length) display(session, [...pinned, "Selected run stopped. Resume explicitly from your coding client."]);
					else hide(session);
				}
				return;
			}
			url = locator.url;
			const raw = readJson(join(run.root, ".design-status.json"));
			if (raw === undefined) {
				display(session, [...pinned, "UI Design Studio | Waiting for the design server status snapshot.", url]);
				return;
			}
			const status = snapshot(raw);
			if (status.run.id !== run.id) throw new Error("Design status belongs to a different run.");
			if (locator.instanceId !== status.instanceId || url !== status.url) {
				throw new Error("Design status belongs to a different server.");
			}
			const progress = linesFor(status);
			const lines = pinned.length ? [...pinned, progress[0] ?? "", progress.slice(1, 3).join(" | "),
				progress.slice(3, 5).join(" | "), progress.slice(5, -1).join(" | "), status.url] : progress;
			try { exportTasks(session, run); }
			catch (error) { lines.splice(lines.length - 1, 0, `Pi Tasks export unavailable. ${text(error instanceof Error ? error.message : String(error))}`); }
			display(session, lines);
		} catch (error) {
			if (!session.run && !pinned.length) {
				hide(session);
				return;
			}
			const lines = [...pinned, `UI Design Studio | Progress unavailable. ${text(error instanceof Error ? error.message : String(error))}`];
			if (url) lines.push(url);
			display(session, lines);
		}
	}

	function start(context: unknown): Session | undefined {
		if (!isContext(context) || context.agent?.kind === "sub" || lifecycle.kind === "stopped") return;
		const id = context.sessionManager.getSessionId();
		if (typeof id !== "string" || !id) return;
		const project = resolve(context.cwd);
		if (lifecycle.kind === "active" && lifecycle.session.id === id && lifecycle.session.project === project) {
			lifecycle.session.context = context;
			refresh();
			return lifecycle.session;
		}
		const tasks = lifecycle.kind === "waiting" ? lifecycle.tasks : undefined;
		if (lifecycle.kind === "active") clear(lifecycle.session);
		const session: Session = { context, id, project, runs: undefined, run: undefined, dashboardId: undefined, dashboardGeneration: 0,
			dashboard: { kind: "idle" }, children: new Set(), banners: 0, resumeRun: undefined, openedRuns: new Set(), opening: undefined,
			discoveryProof: { kind: "none" },
			tasks, exported: undefined, lastLines: "", lastReport: 0, stopTimer: () => {} };
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
		return session;
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
	for (const event of ["session_start", "session_switch", "session_branch", "session_tree", "before_agent_start"]) {
		pi.on(event, async (_event, context) => {
			if (isContext(context) && context.agent?.kind !== "sub" && lifecycle.kind === "active"
				&& (lifecycle.session.id !== context.sessionManager.getSessionId() || lifecycle.session.project !== resolve(context.cwd))) {
				const previous = lifecycle.session;
				lifecycle = { kind: "waiting", tasks: undefined };
				await clear(previous);
			}
			const session = start(context);
			if (!session) return;
			await ensureDashboard(session);
			await synchronizeRun(session);
		});
	}
	pi.on("turn_start", (_event, context) => { start(context); });
	pi.on("tool_call", async (event, context) => {
		const session = start(context);
		if (!session) return;
		const fields = objectFields(event);
		const input = objectFields(fields?.input);
		if (fields?.toolName === "read" && typeof input?.path === "string"
			&& /^(?:skill:\/\/|(?:.*\/)?\.omp\/skills\/)ui-(?:assess|design(?:-studio)?|plan|theme|produce|review|finalize|yolo)(?:\/|:|$)/u.test(input.path)) {
			await ensureDashboard(session);
			await synchronizeRun(session);
		}
	});
	pi.on("tool_result", async (_event, context) => {
		const session = start(context);
		if (!session) return;
		await ensureDashboard(session);
		await synchronizeRun(session);
		refresh();
	});
	pi.on("session_shutdown", async (_event, context) => {
		if (isContext(context) && context.agent?.kind === "sub") {
			if (lifecycle.kind !== "active") {
				lifecycle = { kind: "stopped" };
				unsubscribe();
			}
			return;
		}
		const previous = lifecycle;
		lifecycle = { kind: "stopped" };
		unsubscribe();
		if (previous.kind === "active") await clear(previous.session);
	});
	pi.registerCommand("ui-design-progress", {
		description: "Pin a design run and select this session as its task director, or use auto for read-only discovery.",
		async handler(args, context) {
			const session = start(context);
			if (!session) return;
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
				await ensureDashboard(session);
				await synchronizeRun(session, session.run?.source === "explicit" ? session.run : undefined);
			} catch (error) {
				session.context.ui.notify(text(error instanceof Error ? error.message : String(error)), "warning");
			}
		},
	});
	pi.registerCommand("ui-design-dashboard", {
		description: "Start or stop this session's dashboard, or select a connection by SESSION_ID, and print verified URLs and QR.",
		async handler(args, context) {
			const session = start(context);
			if (!session) return;
			let requestGeneration = session.dashboardGeneration;
			try {
				const argument = args.trim();
				if (argument === "stop") {
					if (session.dashboard.kind === "recovering") session.dashboard.cancel();
					session.dashboardGeneration++;
					session.dashboard = { kind: "stopped" };
					session.dashboardId = undefined;
					refresh();
					await Promise.all([...session.children].map(child => child.stop()));
					return;
				}
				if (argument && argument !== "start" && !/^[0-9a-f]{48}$/u.test(argument)) {
					throw new Error("Use /ui-design-dashboard [start|stop|SESSION_ID].");
				}
				if (!argument && session.dashboard.kind === "stopped") {
					session.context.ui.notify("Dashboard is stopped. Use /ui-design-dashboard start.", "info");
					return;
				}
				if (!argument || argument === "start") {
					if (session.dashboard.kind === "stopped" || session.dashboard.kind === "unavailable" || session.dashboard.kind === "missing"
						|| (session.dashboard.kind === "live" && session.dashboard.owner.kind === "borrowed")) {
						session.dashboardGeneration++;
						session.dashboardId = undefined;
						session.dashboard = { kind: "idle" };
					}
					const before = session.banners;
					const connection = await ensureDashboard(session);
					if (connection && current(session) && session.banners === before) {
						requestGeneration = session.dashboardGeneration;
						const state = session.dashboard;
						await probeConnection(connection);
						if (!current(session) || session.dashboard !== state) return;
						refresh();
						banner(session, connection);
					}
					return;
				}
				const owned = session.dashboard.kind === "live" && session.dashboard.owner.kind === "owned"
					&& session.dashboard.connection.instanceId === argument ? session.dashboard : undefined;
				if (owned) {
					await probeConnection(owned.connection);
					if (current(session) && session.dashboard === owned) banner(session, owned.connection);
					return;
				}
				if (session.dashboard.kind === "recovering") session.dashboard.cancel();
				const generation = ++session.dashboardGeneration;
				requestGeneration = generation;
				const flight = Promise.withResolvers<Connection | undefined>();
				session.dashboard = { kind: "selecting", generation, promise: flight.promise };
				session.dashboardId = argument;
				session.resumeRun = undefined;
				refresh();
				try {
					await Promise.all([...session.children].map(child => child.stop()));
					if (!current(session, generation)) return;
					const selection = connections(session);
					if (selection.kind !== "selected") throw new Error("Dashboard is not running.");
					const connection = selection.connection;
					await probeConnection(connection);
					if (!current(session, generation)) return;
					const latest = connections(session);
					if (latest.kind !== "selected" || latest.connection.instanceId !== connection.instanceId
						|| latest.connection.localUrl !== connection.localUrl || latest.connection.text !== connection.text) {
						throw new Error("Dashboard changed during verification. Select the connection again.");
					}
					session.dashboard = { kind: "live", generation, attempt: 0, since: Date.now(), connection, owner: { kind: "borrowed" } };
					refresh();
					banner(session, connection);
					flight.resolve(connection);
				} finally { flight.resolve(undefined); }
			} catch (error) {
				if (current(session, requestGeneration)) {
					const warning = diagnostic(error instanceof Error ? error.message : error);
					if (session.dashboard.kind === "selecting") session.dashboard = { kind: "unavailable", warning };
					session.context.ui.notify(warning, "warning");
					refresh();
				}
			}
		},
	});
}
