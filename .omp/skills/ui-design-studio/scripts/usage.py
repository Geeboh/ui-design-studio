"""Bounded local token, cost, and optional OMP usage telemetry."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from typing import Any, Callable

SCHEMA_VERSION = "1.0"
USAGE_FILE = "usage.json"
USAGE_DB_FILE = "usage.sqlite3"
MAX_RECORDS = 10_000
MAX_BYTES = 8 * 1024 * 1024
MAX_RECENT = 200
MAX_HISTORY = 1_500
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
RANGES = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000, "90d": 7776000, "all": None}
EXECUTION_STATES = {"completed", "failed", "aborted", "outcome_unknown"}
COST_STATES = {"unknown", "estimated", "observed", "not_billable"}


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def _parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("usage timestamps require a timezone")
    return parsed.astimezone(dt.timezone.utc)


def _integer(value: Any, label: str, *, optional: bool = True) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 2**53 - 1:
        raise ValueError(f"{label} must be a safe nonnegative integer or null")
    return value


def _text(value: Any, label: str, *, optional: bool = True, limit: int = 256) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be a nonempty bounded string or null")
    return value.strip()


def _cost(value: Any, label: str, *, actual: bool = False) -> dict[str, Any]:
    if value is None:
        return {"status": "unknown", "amountMinor": None, "currencyCode": None, "currencyExponent": None, "source": None, "observedAt": None}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    status = value.get("status", "unknown")
    if status not in COST_STATES or actual and status == "estimated":
        raise ValueError(f"{label}.status is invalid")
    amount = _integer(value.get("amountMinor"), f"{label}.amountMinor")
    currency = value.get("currencyCode")
    exponent = _integer(value.get("currencyExponent"), f"{label}.currencyExponent")
    source = _text(value.get("source"), f"{label}.source", limit=128)
    observed_at = value.get("observedAt")
    if observed_at is not None:
        observed_at = _text(observed_at, f"{label}.observedAt", limit=64)
        _parse_time(observed_at)
    if status == "unknown":
        if amount is not None or observed_at is not None:
            raise ValueError(f"{label}.unknown cannot claim an amount or observation time")
    elif status == "not_billable":
        if amount != 0 or currency is None or exponent is None or source is None or observed_at is None:
            raise ValueError(f"{label}.not_billable requires an observed zero cost")
    else:
        if amount is None or currency is None or exponent is None or source is None or observed_at is None:
            raise ValueError(f"{label}.{status} requires amount, currency, source, and observedAt")
    if currency is not None and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
        raise ValueError(f"{label}.currencyCode must be an uppercase ISO code")
    if exponent is not None and exponent > 6:
        raise ValueError(f"{label}.currencyExponent must be between 0 and 6")
    return {"status": status, "amountMinor": amount, "currencyCode": currency, "currencyExponent": exponent, "source": source, "observedAt": observed_at}


def validate_record(payload: Any, run_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("usage record must be an object")
    usage_id = payload.get("usageId")
    idempotency = payload.get("idempotencyKey")
    if not isinstance(usage_id, str) or not ID.fullmatch(usage_id):
        raise ValueError("usageId must be a portable bounded identifier")
    if not isinstance(idempotency, str) or not ID.fullmatch(idempotency):
        raise ValueError("idempotencyKey must be a portable bounded identifier")
    recorded_at = payload.get("recordedAt", _timestamp())
    if not isinstance(recorded_at, str):
        raise ValueError("recordedAt must be a timezone-aware timestamp")
    _parse_time(recorded_at)
    status = payload.get("executionStatus", "outcome_unknown")
    if status not in EXECUTION_STATES:
        raise ValueError("executionStatus is invalid")
    fingerprint = payload.get("requestFingerprint")
    if fingerprint is not None and (not isinstance(fingerprint, str) or not HASH.fullmatch(fingerprint)):
        raise ValueError("requestFingerprint must be a SHA-256 digest or null")
    token_input = _integer(payload.get("tokens", {}).get("input") if isinstance(payload.get("tokens"), dict) else None, "tokens.input")
    token_output = _integer(payload.get("tokens", {}).get("output") if isinstance(payload.get("tokens"), dict) else None, "tokens.output")
    cache_read = _integer(payload.get("tokens", {}).get("cacheRead") if isinstance(payload.get("tokens"), dict) else None, "tokens.cacheRead")
    cache_write = _integer(payload.get("tokens", {}).get("cacheWrite") if isinstance(payload.get("tokens"), dict) else None, "tokens.cacheWrite")
    total = token_input + token_output if token_input is not None and token_output is not None else None
    compression_value = payload.get("compression")
    compression = None
    if compression_value is not None:
        if not isinstance(compression_value, dict):
            raise ValueError("compression must be an object or null")
        before = _integer(compression_value.get("before"), "compression.before", optional=False)
        after = _integer(compression_value.get("after"), "compression.after", optional=False)
        if after > before:
            raise ValueError("compression.after cannot exceed compression.before")
        compression = {"before": before, "after": after, "saved": before - after, "source": _text(compression_value.get("source"), "compression.source", optional=False, limit=128)}
    record = {
        "recordType": "usageRequest", "schemaVersion": SCHEMA_VERSION,
        "usageId": usage_id, "runId": run_id, "idempotencyKey": idempotency,
        "requestFingerprint": fingerprint, "providerRequested": _text(payload.get("providerRequested"), "providerRequested"),
        "providerObserved": _text(payload.get("providerObserved"), "providerObserved"), "modelRequested": _text(payload.get("modelRequested"), "modelRequested"),
        "modelObserved": _text(payload.get("modelObserved"), "modelObserved"), "agentId": _text(payload.get("agentId"), "agentId"),
        "host": _text(payload.get("host"), "host"), "sessionId": _text(payload.get("sessionId"), "sessionId", limit=128),
        "recordedAt": recorded_at, "executionStatus": status,
        "durationMs": _integer(payload.get("durationMs"), "durationMs"), "ttftMs": _integer(payload.get("ttftMs"), "ttftMs"),
        "tokens": {"input": token_input, "output": token_output, "cacheRead": cache_read, "cacheWrite": cache_write, "total": total},
        "compression": compression,
        "cost": {"actual": _cost(payload.get("cost", {}).get("actual") if isinstance(payload.get("cost"), dict) else None, "cost.actual", actual=True),
                 "estimate": _cost(payload.get("cost", {}).get("estimate") if isinstance(payload.get("cost"), dict) else None, "cost.estimate"),
                 "providerCacheDiscount": _cost(payload.get("cost", {}).get("providerCacheDiscount") if isinstance(payload.get("cost"), dict) else None, "cost.providerCacheDiscount")},
        "providerReceiptId": _text(payload.get("providerReceiptId"), "providerReceiptId", limit=256),
    }
    return record


def _empty(run_id: str) -> dict[str, Any]:
    return {"schemaVersion": SCHEMA_VERSION, "runId": run_id, "revision": 0, "records": [], "retention": {"maxRecords": MAX_RECORDS, "maxBytes": MAX_BYTES, "droppedRecords": 0}, "updatedAt": None}


def _legacy_file(studio: Any, root: Path, run_id: str) -> tuple[dict[str, Any], list[str]]:
    path = studio.safe_path(root, USAGE_FILE, must_exist=False)
    if not path.exists():
        return _empty(run_id), []
    try:
        value = studio.read_json(path)
        if not isinstance(value, dict) or value.get("schemaVersion") != SCHEMA_VERSION or value.get("runId") != run_id or not isinstance(value.get("records"), list):
            raise ValueError("usage file shape is invalid")
        if len(value["records"]) > MAX_RECORDS:
            raise ValueError("usage file exceeds its record bound")
        records = [validate_record(item, run_id) for item in value["records"]]
        value["records"] = records
        return value, []
    except Exception as exc:
        return _empty(run_id), [f"Usage telemetry unavailable: {exc}"]


def _db_path(studio: Any, root: Path) -> Path:
    return studio.safe_path(root, USAGE_DB_FILE, must_exist=False)


def _db_meta(connection: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row is not None else default


def _set_db_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute("INSERT INTO metadata(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))


def _open_db(path: Path, run_id: str) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA auto_vacuum = INCREMENTAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS records (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            usage_id TEXT NOT NULL UNIQUE,
            idempotency_key TEXT NOT NULL UNIQUE,
            recorded_at TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS records_recorded_at ON records(recorded_at);
        """
    )
    stored_run = _db_meta(connection, "runId")
    if stored_run is None:
        _set_db_meta(connection, "runId", run_id)
        _set_db_meta(connection, "revision", "0")
        _set_db_meta(connection, "droppedRecords", "0")
        _set_db_meta(connection, "updatedAt", "")
        connection.commit()
    elif stored_run != run_id:
        connection.close()
        raise ValueError("usage database belongs to a different run")
    return connection


def _record_from_row(row: sqlite3.Row, run_id: str) -> dict[str, Any]:
    value = json.loads(str(row["payload"]))
    return validate_record(value, run_id)


def _db_data(path: Path, run_id: str) -> dict[str, Any]:
    connection = _open_db(path, run_id)
    try:
        connection.row_factory = sqlite3.Row
        records = [_record_from_row(row, run_id) for row in connection.execute("SELECT payload FROM records ORDER BY sequence")]
        return {
            "schemaVersion": SCHEMA_VERSION,
            "runId": run_id,
            "revision": int(_db_meta(connection, "revision", "0") or "0"),
            "records": records,
            "retention": {
                "maxRecords": MAX_RECORDS,
                "maxBytes": MAX_BYTES,
                "droppedRecords": int(_db_meta(connection, "droppedRecords", "0") or "0"),
            },
            "updatedAt": _db_meta(connection, "updatedAt") or None,
        }
    finally:
        connection.close()


def _db_size(path: Path) -> int:
    return sum(candidate.stat().st_size for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")) if candidate.exists())


def _drop_oldest(connection: sqlite3.Connection) -> bool:
    cursor = connection.execute("DELETE FROM records WHERE sequence = (SELECT sequence FROM records ORDER BY sequence LIMIT 1)")
    return cursor.rowcount > 0


def _trim_db(connection: sqlite3.Connection, path: Path) -> int:
    dropped = int(_db_meta(connection, "droppedRecords", "0") or "0")
    while connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] > MAX_RECORDS:
        if not _drop_oldest(connection):
            break
        dropped += 1
    connection.commit()
    while _db_size(path) > MAX_BYTES and connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] > 0:
        if not _drop_oldest(connection):
            break
        dropped += 1
        connection.commit()
        connection.execute("PRAGMA incremental_vacuum(1)")
    _set_db_meta(connection, "droppedRecords", str(dropped))
    return dropped


def _read_file(studio: Any, root: Path, run_id: str) -> tuple[dict[str, Any], list[str]]:
    path = _db_path(studio, root)
    if path.exists():
        try:
            return _db_data(path, run_id), []
        except Exception as exc:
            return _empty(run_id), [f"Usage telemetry unavailable: {exc}"]
    return _legacy_file(studio, root, run_id)


def _same_record(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return {key: value for key, value in left.items() if key != "recordedAt"} == {key: value for key, value in right.items() if key != "recordedAt"}


def record_usage(studio: Any, root: Path, payload: Any, records_lock: Callable) -> dict[str, Any]:
    run = studio.read_json(studio.safe_path(root, "run.json"))
    run_id = run.get("id", Path(root).name)
    record = validate_record(payload, run_id)
    with records_lock(studio, root):
        path = _db_path(studio, root)
        had_db = path.exists()
        legacy, warnings = _legacy_file(studio, root, run_id) if not had_db else (_empty(run_id), [])
        if warnings:
            raise studio.StudioError(warnings[0])
        connection = _open_db(path, run_id)
        try:
            if not had_db:
                for item in legacy["records"]:
                    connection.execute(
                        "INSERT INTO records(usage_id, idempotency_key, recorded_at, payload) VALUES (?, ?, ?, ?)",
                        (item["usageId"], item["idempotencyKey"], item["recordedAt"], json.dumps(item, ensure_ascii=False, separators=(",", ":"))),
                    )
                _set_db_meta(connection, "revision", str(legacy["revision"]))
                _set_db_meta(connection, "droppedRecords", str(legacy.get("retention", {}).get("droppedRecords", 0)))
                _set_db_meta(connection, "updatedAt", legacy.get("updatedAt") or "")
                connection.commit()
            connection.row_factory = sqlite3.Row
            existing = connection.execute("SELECT payload, usage_id FROM records WHERE idempotency_key = ?", (record["idempotencyKey"],)).fetchone()
            if existing is not None:
                prior = _record_from_row(existing, run_id)
                if _same_record(prior, record):
                    return {"status": "PASS", "usageId": prior["usageId"], "revision": int(_db_meta(connection, "revision", "0") or "0"), "replayed": True}
                raise studio.StudioError("Usage idempotency key was reused with different content")
            connection.execute(
                "INSERT INTO records(usage_id, idempotency_key, recorded_at, payload) VALUES (?, ?, ?, ?)",
                (record["usageId"], record["idempotencyKey"], record["recordedAt"], json.dumps(record, ensure_ascii=False, separators=(",", ":"))),
            )
            revision = int(_db_meta(connection, "revision", "0") or "0") + 1
            _set_db_meta(connection, "revision", str(revision))
            _set_db_meta(connection, "updatedAt", _timestamp())
            connection.commit()
            _trim_db(connection, path)
            connection.commit()
            os.chmod(path, 0o600)
            return {"status": "PASS", "usageId": record["usageId"], "revision": revision, "replayed": False}
        finally:
            connection.close()


def _range_start(range_key: str, now: dt.datetime) -> dt.datetime | None:
    if range_key not in RANGES:
        raise ValueError("usage range must be 1h, 24h, 7d, 30d, 90d, or all")
    seconds = RANGES[range_key]
    return None if seconds is None else now - dt.timedelta(seconds=seconds)


def _currency_key(cost: dict[str, Any]) -> str | None:
    if cost.get("currencyCode") is None or cost.get("currencyExponent") is None:
        return None
    return f"{cost['currencyCode']}:{cost['currencyExponent']}"


def _cost_totals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for record in records:
        for name, field in (("actual", "actual"), ("estimate", "estimate"), ("providerCacheDiscount", "providerCacheDiscount")):
            cost = record["cost"][field]
            key = _currency_key(cost)
            if key is None:
                continue
            row = totals.setdefault(key, {"currencyCode": cost["currencyCode"], "currencyExponent": cost["currencyExponent"], "actualMinor": 0, "estimatedMinor": 0, "providerCacheDiscountMinor": 0, "unknownRequests": 0})
            if cost["status"] in {"observed", "not_billable"} and cost["amountMinor"] is not None:
                if name == "actual": row["actualMinor"] += cost["amountMinor"]
                elif name == "providerCacheDiscount": row["providerCacheDiscountMinor"] += cost["amountMinor"]
            elif cost["status"] == "estimated" and name == "estimate" and cost["amountMinor"] is not None:
                row["estimatedMinor"] += cost["amountMinor"]
        if record["cost"]["actual"]["status"] == "unknown":
            key = _currency_key(record["cost"]["actual"])
            if key is not None and key in totals:
                totals[key]["unknownRequests"] += 1
    return sorted(totals.values(), key=lambda item: (item["currencyCode"], item["currencyExponent"]))


def _optional_sum(records: list[dict[str, Any]], path: tuple[str, ...]) -> int | None:
    if not records:
        return None
    values: list[int] = []
    for record in records:
        value: Any = record
        for part in path:
            value = value.get(part) if isinstance(value, dict) else None
        if value is None:
            return None
        values.append(value)
    return sum(values)


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {"requests": len(records), "completed": sum(item["executionStatus"] == "completed" for item in records), "failed": sum(item["executionStatus"] == "failed" for item in records), "aborted": sum(item["executionStatus"] == "aborted" for item in records), "outcomeUnknown": sum(item["executionStatus"] == "outcome_unknown" for item in records), "inputTokens": _optional_sum(records, ("tokens", "input")), "outputTokens": _optional_sum(records, ("tokens", "output")), "cacheReadTokens": _optional_sum(records, ("tokens", "cacheRead")), "cacheWriteTokens": _optional_sum(records, ("tokens", "cacheWrite")), "totalTokens": _optional_sum(records, ("tokens", "total")), "compressionSavedTokens": _optional_sum(records, ("compression", "saved")), "unknownTokenRequests": sum(item["tokens"]["input"] is None or item["tokens"]["output"] is None for item in records), "unknownCostRequests": sum(item["cost"]["actual"]["status"] == "unknown" for item in records), "costs": _cost_totals(records)}


def _breakdown(records: list[dict[str, Any]], observed_key: str, requested_key: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, bool], list[dict[str, Any]]] = {}
    for record in records:
        value = record.get(observed_key) or record.get(requested_key) or "unknown"
        observed = bool(record.get(observed_key))
        grouped.setdefault((value, observed), []).append(record)
    rows = []
    for (name, observed), entries in grouped.items():
        row = {"name": name, "observed": observed, **_summary(entries)}
        rows.append(row)
    return sorted(rows, key=lambda item: (-item["requests"], item["name"]))


def _history(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        day = _parse_time(record["recordedAt"]).date().isoformat()
        buckets.setdefault(day, []).append(record)
    points = []
    for day, entries in sorted(buckets.items()):
        summary = _summary(entries)
        points.append({"startAt": day + "T00:00:00+00:00", "endAt": day + "T23:59:59.999999+00:00", **summary})
    return points[-MAX_HISTORY:]


def project(studio: Any, root: Path, *, omp_probe: Any = None, range_key: str = "24h") -> dict[str, Any]:
    run = studio.read_json(studio.safe_path(root, "run.json"))
    run_id = run.get("id", Path(root).name)
    data, warnings = _read_file(studio, root, run_id)
    now = dt.datetime.now(dt.timezone.utc)
    start = _range_start(range_key, now)
    retained = data["records"]
    selected = [item for item in retained if start is None or _parse_time(item["recordedAt"]) >= start]
    local = {"schemaVersion": SCHEMA_VERSION, "available": bool(data["records"]), "source": "run-json", "revision": data["revision"], "scope": "run", "complete": True, "generatedAt": _timestamp(), "range": range_key, "session": _summary(selected), "lifetime": _summary(retained), "history": _history(selected), "byModel": _breakdown(selected, "modelObserved", "modelRequested"), "byProvider": _breakdown(selected, "providerObserved", "providerRequested"), "byAgent": _breakdown(selected, "agentId", "agentId"), "recent": list(reversed(selected[-MAX_RECENT:])), "limits": data["retention"], "warnings": warnings}
    local["omp"] = omp_probe.snapshot(start=False) if omp_probe is not None else {"status": "unavailable", "reason": "OMP probe is not configured"}
    return local


def _csv_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    first = value.lstrip(" \t\r\n")[:1]
    return "'" + value if first in {"=", "+", "-", "@"} else value


def export_data(studio: Any, root: Path, *, omp_probe: Any = None, format_name: str = "json") -> tuple[bytes, str, str]:
    usage = project(studio, root, omp_probe=omp_probe, range_key="all")
    run = studio.read_json(studio.safe_path(root, "run.json"))
    run_id = run.get("id", Path(root).name)
    data, _ = _read_file(studio, root, run_id)
    if format_name == "json":
        return json.dumps({"usage": usage, "records": data["records"]}, indent=2, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", "prism-usage.json"
    if format_name != "csv":
        raise ValueError("usage export format must be json or csv")
    output = io.StringIO(newline="")
    fields = ["usageId", "recordedAt", "sessionId", "providerRequested", "providerObserved", "modelRequested", "modelObserved", "agentId", "executionStatus", "inputTokens", "outputTokens", "cacheReadTokens", "cacheWriteTokens", "totalTokens", "compressionSavedTokens", "actualStatus", "actualAmountMinor", "actualCurrencyCode", "actualCurrencyExponent", "estimateStatus", "providerCacheDiscountStatus", "providerCacheDiscountAmountMinor", "providerReceiptId"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for record in data["records"]:
        actual = record["cost"]["actual"]
        estimate = record["cost"]["estimate"]
        discount = record["cost"]["providerCacheDiscount"]
        row = {"usageId": record["usageId"], "recordedAt": record["recordedAt"], "sessionId": record["sessionId"], "providerRequested": record["providerRequested"], "providerObserved": record["providerObserved"], "modelRequested": record["modelRequested"], "modelObserved": record["modelObserved"], "agentId": record["agentId"], "executionStatus": record["executionStatus"], "inputTokens": record["tokens"]["input"], "outputTokens": record["tokens"]["output"], "cacheReadTokens": record["tokens"]["cacheRead"], "cacheWriteTokens": record["tokens"]["cacheWrite"], "totalTokens": record["tokens"]["total"], "compressionSavedTokens": record["compression"]["saved"] if record["compression"] else None, "actualStatus": actual["status"], "actualAmountMinor": actual["amountMinor"], "actualCurrencyCode": actual["currencyCode"], "actualCurrencyExponent": actual["currencyExponent"], "estimateStatus": estimate["status"], "providerCacheDiscountStatus": discount["status"], "providerCacheDiscountAmountMinor": discount["amountMinor"], "providerReceiptId": record["providerReceiptId"]}
        writer.writerow({key: _csv_text(value) for key, value in row.items()})
    return output.getvalue().encode("utf-8"), "text/csv; charset=utf-8", "prism-usage.csv"


class OMPUsageProbe:
    """Best-effort native OMP stats adapter. PRISM remains usable without it."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = str(Path(project_root).resolve())
        self._lock = threading.Lock()
        self._value: dict[str, Any] = {"status": "idle", "source": "omp stats --json", "reason": "Open Usage to request OMP statistics"}
        self._thread: threading.Thread | None = None
        self._fetched_at = 0.0

    def snapshot(self, *, start: bool = True) -> dict[str, Any]:
        if not start:
            with self._lock:
                return dict(self._value)
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                if time.monotonic() - self._fetched_at >= 30:
                    self._value = {"status": "loading", "source": "omp stats --json"}
                    self._thread = threading.Thread(target=self._refresh, name="prism-omp-usage", daemon=True)
                    self._thread.start()
            return dict(self._value)

    def _refresh(self) -> None:
        command = os.environ.get("PRISM_OMP_COMMAND") or shutil.which("omp")
        if not command:
            value = {"status": "unavailable", "reason": "OMP command is not installed"}
        else:
            try:
                result = subprocess.run([command, "stats", "--json"], capture_output=True, text=True, timeout=15, check=False)
                if result.returncode != 0:
                    raise RuntimeError(f"OMP stats exited with {result.returncode}")
                start = result.stdout.find("{")
                if start < 0:
                    raise RuntimeError("OMP stats returned no JSON")
                parsed = json.JSONDecoder().raw_decode(result.stdout[start:])[0]
                value = {"status": "ready", "source": "omp stats --json", "observedAt": _timestamp(), "projectRoot": self.project_root, **{key: parsed.get(key, []) for key in ("overall", "byModel", "byFolder", "byAgentType", "bySideChannel", "timeSeries")}}
            except Exception as exc:
                value = {"status": "unavailable", "source": "omp stats --json", "reason": str(exc)[:240]}
        with self._lock:
            self._value = value
            self._fetched_at = time.monotonic()
            self._thread = None
