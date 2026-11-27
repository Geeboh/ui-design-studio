"""Deterministic, bounded asset optimization for one design run.

The module owns no server state. Settings and immutable result artifacts live under
``<run>/optimization`` and every returned byte count is measured from those files.
"""
from __future__ import annotations

import base64
import datetime as _dt
import gzip
import hashlib
import html
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import zlib
import xml.etree.ElementTree as ET

SCHEMA_VERSION = "1.0"
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_RESULTS = 128
MAX_SOURCES = 32
MAX_NAME = 255
RESULT_ID = re.compile(r"opt-[0-9a-f]{32}\Z")
PRESETS = ("balanced", "maximum", "lossless", "custom")
RECOMMENDATION_MODES = ("safe", "aggressive")
TOOL_NAMES = ("pngcrush", "jpegoptim", "optipng", "svgomg", "htmlMinify", "cssMinify", "jsMinify")
TOOL_EXECUTABLES = {
    "pngcrush": ("pngcrush",),
    "jpegoptim": ("jpegoptim",),
    "optipng": ("optipng",),
    "svgomg": ("svgomg", "svgo"),
}

DEFAULT_TOOLS = {name: True for name in TOOL_NAMES}
PRESET_DEFAULTS = {
    "balanced": {"quality": 80, "level": 6, "minify": True, "compress": True, "recommendationMode": "safe"},
    "maximum": {"quality": 90, "level": 9, "minify": True, "compress": True, "recommendationMode": "aggressive"},
    "lossless": {"quality": 100, "level": 9, "minify": True, "compress": True, "recommendationMode": "safe"},
    "custom": {"quality": 80, "level": 6, "minify": True, "compress": False, "recommendationMode": "safe"},
}

# Registry order is API order. Do not infer behavior from a filename elsewhere.
OPTIMIZER_REGISTRY = (
    {"id": "png", "type": "image", "extensions": (".png",), "tool": "pngcrush", "builtin": "copy"},
    {"id": "jpeg", "type": "image", "extensions": (".jpg", ".jpeg"), "tool": "jpegoptim", "builtin": "copy"},
    {"id": "optipng", "type": "image", "extensions": (".png",), "tool": "optipng", "builtin": "copy"},
    {"id": "svg", "type": "svg", "extensions": (".svg",), "tool": "svgomg", "builtin": "svg"},
    {"id": "html", "type": "html", "extensions": (".html", ".htm"), "tool": "htmlMinify", "builtin": "html"},
    {"id": "css", "type": "css", "extensions": (".css",), "tool": "cssMinify", "builtin": "css"},
    {"id": "js", "type": "js", "extensions": (".js", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"), "tool": "jsMinify", "builtin": "js"},
    {"id": "json", "type": "json", "extensions": (".json",), "tool": None, "builtin": "json"},
    {"id": "text", "type": "text", "extensions": (".txt", ".text", ".md", ".markdown", ".csv", ".xml"), "tool": None, "builtin": "text"},
    {"id": "pdf", "type": "pdf", "extensions": (".pdf",), "tool": None, "builtin": "copy"},
    {"id": "compressed", "type": "compressed", "extensions": (".gz", ".tgz", ".br"), "tool": None, "builtin": "copy"},
)

EXTENSION_TYPE = {extension: entry["type"] for entry in OPTIMIZER_REGISTRY for extension in entry["extensions"]}


def _timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="microseconds")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _number(value: Any, low: int, high: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{field} must be an integer between {low} and {high}")
    return value


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def validate_settings(value: Any = None, *, base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate and normalize settings without accepting unknown fields."""
    source = DEFAULT_SETTINGS() if value is None else value
    if not isinstance(source, dict):
        raise ValueError("Optimization settings must be an object")
    allowed = {"schemaVersion", "preset", "quality", "level", "minify", "compress", "tools", "recommendationMode"}
    unknown = set(source) - allowed
    if unknown:
        raise ValueError("Optimization settings contain unsupported fields: " + ", ".join(sorted(unknown)))
    preset = source.get("preset", base.get("preset") if isinstance(base, dict) else "balanced")
    if preset not in PRESETS:
        raise ValueError("Optimization preset is invalid")
    defaults = dict(PRESET_DEFAULTS[preset])
    defaults["tools"] = dict(DEFAULT_TOOLS)
    if isinstance(base, dict) and preset == base.get("preset"):
        defaults.update({key: base[key] for key in ("quality", "level", "minify", "compress", "recommendationMode") if key in base})
        if isinstance(base.get("tools"), dict):
            defaults["tools"].update(base["tools"])
    merged = {**defaults, **source}
    schema = merged.get("schemaVersion", SCHEMA_VERSION)
    if schema != SCHEMA_VERSION:
        raise ValueError("Optimization schemaVersion must be '1.0'")
    quality = _number(merged.get("quality"), 1, 100, "Optimization quality")
    level = _number(merged.get("level"), 0, 9, "Optimization level")
    minify = _bool(merged.get("minify"), "Optimization minify")
    compress = _bool(merged.get("compress"), "Optimization compress")
    mode = merged.get("recommendationMode")
    if mode not in RECOMMENDATION_MODES:
        raise ValueError("Optimization recommendationMode is invalid")
    tools = merged.get("tools")
    if not isinstance(tools, dict) or set(tools) != set(TOOL_NAMES):
        raise ValueError("Optimization tools must contain every supported tool toggle")
    normalized_tools = {name: _bool(tools[name], f"Optimization tools.{name}") for name in TOOL_NAMES}
    return {"schemaVersion": SCHEMA_VERSION, "preset": preset, "quality": quality, "level": level,
            "minify": minify, "compress": compress, "tools": normalized_tools, "recommendationMode": mode}


def DEFAULT_SETTINGS() -> dict[str, Any]:
    return validate_settings({"schemaVersion": SCHEMA_VERSION, "preset": "balanced", **PRESET_DEFAULTS["balanced"], "tools": dict(DEFAULT_TOOLS)})


def _executable(name: str) -> str | None:
    for candidate in TOOL_EXECUTABLES.get(name, ()):
        found = shutil.which(candidate)
        if found:
            return found
    return None

def _brotli_available() -> bool:
    try:
        import brotli  # type: ignore
    except ImportError:
        return False
    return callable(getattr(brotli, "compress", None))


def tool_availability() -> dict[str, Any]:
    tools: dict[str, Any] = {}
    for name in TOOL_NAMES:
        executable = _executable(name)
        if name in TOOL_EXECUTABLES:
            tools[name] = {"available": executable is not None, "executable": executable,
                           "reason": "ready" if executable else "executable not found"}
        else:
            tools[name] = {"available": True, "executable": None, "reason": "built-in conservative transform"}
    return {"tools": tools, "builtins": ["svg", "html", "css", "js", "json", "text", "gzip", "brotli"],
            "compression": {"gzip": True, "brotli": _brotli_available()},
            "limitBytes": MAX_SOURCE_BYTES}


def recommendations(settings: dict[str, Any], capabilities: dict[str, Any] | None = None) -> list[str]:
    settings = validate_settings(settings)
    capabilities = capabilities or tool_availability()
    tools = capabilities.get("tools", {})
    result: list[str] = []
    if settings["recommendationMode"] == "aggressive":
        result.append("Aggressive mode can change formatting and removes more bytes.")
    else:
        result.append("Safe mode keeps conservative transforms and preserves output when bytes grow.")
    for name in ("pngcrush", "optipng", "jpegoptim", "svgomg"):
        if settings["tools"].get(name) and not tools.get(name, {}).get("available", False):
            result.append(f"{name} is unavailable; built-in fallback will preserve image bytes or sanitize SVG.")
    if settings["compress"]:
        result.append("Compression measurements include deterministic gzip and optional Brotli artifacts.")
        if not capabilities.get("compression", {}).get("brotli", False):
            result.append("Brotli is unavailable in this runtime; gzip remains available.")
    if settings["minify"]:
        result.append("Minification uses lexical rules and keeps the original when a transform grows output.")
    return result


def identify_type(name: str) -> str:
    extension = Path(name).suffix.lower()
    return EXTENSION_TYPE.get(extension, "binary")


def _strip_comments_and_space(value: str, *, css: bool = False, js: bool = False) -> str:
    """Remove comments and collapse only whitespace outside quoted literals."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    pending_space = False
    length = len(value)
    while index < length:
        char = value[index]
        if quote:
            if pending_space:
                output.append(" ")
                pending_space = False
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            if pending_space and output and output[-1] not in "({[,;:=!<>+-*/%&|?:":
                output.append(" ")
            pending_space = False
            output.append(char)
            quote = char
            index += 1
            continue
        if value.startswith("/*", index):
            end = value.find("*/", index + 2)
            index = length if end < 0 else end + 2
            pending_space = bool(output)
            continue
        if js and value.startswith("//", index):
            end = value.find("\n", index + 2)
            index = length if end < 0 else end
            pending_space = bool(output)
            continue
        if char.isspace():
            pending_space = True
            index += 1
            continue
        if pending_space:
            previous = output[-1] if output else ""
            if previous and (previous.isalnum() or previous in "_$") and (char.isalnum() or char in "_$"):
                output.append(" ")
            elif css and previous in ("@",) and char.isalpha():
                output.append(" ")
            pending_space = False
        output.append(char)
        index += 1
    return "".join(output).strip()


def minify_html(value: str) -> str:
    value = re.sub(r"<!--[\s\S]*?-->", "", value)
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"\x00{len(protected) - 1}\x00"

    value = re.sub(r"<(?:pre|textarea|script|style)\b[\s\S]*?</(?:pre|textarea|script|style)>", protect, value, flags=re.I)
    value = re.sub(r">\s+<", "><", value)
    value = re.sub(r"\s{2,}", " ", value).strip()
    for index, original in enumerate(protected):
        if re.match(r"<script\b", original, re.I):
            original = re.sub(r"(<script\b[^>]*>)([\s\S]*?)(</script>)", lambda m: m.group(1) + _strip_comments_and_space(m.group(2), js=True) + m.group(3), original, flags=re.I)
        elif re.match(r"<style\b", original, re.I):
            original = re.sub(r"(<style\b[^>]*>)([\s\S]*?)(</style>)", lambda m: m.group(1) + minify_css(m.group(2)) + m.group(3), original, flags=re.I)
        value = value.replace(f"\x00{index}\x00", original)
    return value


def minify_css(value: str) -> str:
    value = _strip_comments_and_space(value, css=True)
    return re.sub(r"\s*([{}:;,>+~])\s*", r"\1", value).replace(";}", "}")


def minify_js(value: str) -> str:
    return _strip_comments_and_space(value, js=True)


def minify_text(value: str) -> str:
    lines = [line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def minify_json(value: bytes) -> bytes:
    parsed = json.loads(value.decode("utf-8"))
    return _canonical(parsed)


def sanitize_svg(value: bytes) -> bytes:
    root = ET.fromstring(value)
    forbidden = {"script", "foreignobject", "iframe", "object", "embed", "animate", "animatemotion", "animatetransform", "set"}
    for parent in root.iter():
        for child in list(parent):
            if child.tag.rsplit("}", 1)[-1].lower() in forbidden:
                parent.remove(child)
        for key, attribute in list(parent.attrib.items()):
            local = key.rsplit("}", 1)[-1].lower()
            if local.startswith("on") or local in {"base", "xmlns:xlink"}:
                del parent.attrib[key]
                continue
            if local in {"href", "src"} and (attribute.strip().lower().startswith("javascript:") or attribute.strip().startswith("//")):
                del parent.attrib[key]
                continue
            if local == "style":
                parent.attrib[key] = minify_css(attribute)
        if parent.tag.rsplit("}", 1)[-1].lower() == "style" and parent.text:
            parent.text = minify_css(parent.text)
        if parent.text and parent.tag.rsplit("}", 1)[-1].lower() not in {"text", "tspan", "title", "desc"}:
            parent.text = parent.text.strip() or None
        if parent.tail:
            parent.tail = parent.tail.strip() or None
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_NAME or "\\" in value:
        raise ValueError("Optimization source name is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts) or any(ord(char) < 32 for char in value):
        raise ValueError("Optimization source name is invalid")
    return path.as_posix()


def _transform(name: str, data: bytes, settings: dict[str, Any]) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    kind = identify_type(name)
    operations: list[dict[str, Any]] = []
    measurements: dict[str, Any] = {"inputSha256": _digest(data), "type": kind}
    current = data
    if kind == "svg" and settings["minify"]:
        try:
            candidate = sanitize_svg(current)
            if len(candidate) < len(current):
                current = candidate
                operations.append({"id": "svg-sanitize", "label": "Sanitize and minify SVG", "tool": "builtin-svg", "status": "applied", "details": "Removed unsafe nodes and insignificant whitespace."})
            else:
                operations.append({"id": "svg-sanitize", "label": "Sanitize and minify SVG", "tool": "builtin-svg", "status": "unchanged", "details": "Sanitized output was not smaller; original bytes kept."})
        except (ET.ParseError, UnicodeError, ValueError) as exc:
            operations.append({"id": "svg-sanitize", "label": "Sanitize and minify SVG", "tool": "builtin-svg", "status": "failed", "details": f"Invalid SVG: {exc}"})
    elif kind in {"html", "css", "js", "json", "text"} and settings["minify"]:
        try:
            decoded = current.decode("utf-8")
            if kind == "html":
                candidate = minify_html(decoded).encode("utf-8")
                tool = "builtin-html"
                label = "Conservative HTML minification"
            elif kind == "css":
                candidate = minify_css(decoded).encode("utf-8")
                tool = "builtin-css"
                label = "Conservative CSS minification"
            elif kind == "js":
                candidate = minify_js(decoded).encode("utf-8")
                tool = "builtin-js"
                label = "Conservative JavaScript minification"
            elif kind == "json":
                candidate = minify_json(current)
                tool = "builtin-json"
                label = "Canonical JSON minification"
            else:
                candidate = minify_text(decoded).encode("utf-8")
                tool = "builtin-text"
                label = "Conservative text minification"
            if len(candidate) < len(current):
                current = candidate
                operations.append({"id": "minify", "label": label, "tool": tool, "status": "applied", "details": "Output measured smaller than source."})
            else:
                operations.append({"id": "minify", "label": label, "tool": tool, "status": "unchanged", "details": "Original bytes kept because output was not smaller."})
        except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
            operations.append({"id": "minify", "label": f"Minify {kind}", "tool": f"builtin-{kind}", "status": "failed", "details": f"Transform skipped: {exc}"})
    elif kind in {"image", "pdf", "compressed", "binary"}:
        operations.append({"id": "copy", "label": "Preserve source bytes", "tool": "builtin-copy", "status": "unchanged", "details": "No safe built-in transform for this resource."})
    measurements["transformedBytes"] = len(current)
    return current, operations, measurements


def _external_transform(name: str, data: bytes, current: bytes, settings: dict[str, Any], capabilities: dict[str, Any], operations: list[dict[str, Any]]) -> bytes:
    extension = Path(name).suffix.lower()
    tool_name = {".png": "pngcrush", ".jpg": "jpegoptim", ".jpeg": "jpegoptim", ".svg": "svgomg"}.get(extension)
    if extension == ".png" and settings["tools"].get("optipng") and capabilities["tools"]["optipng"]["available"]:
        tool_name = "optipng"
    if not tool_name or not settings["tools"].get(tool_name, False):
        return current
    capability = capabilities["tools"].get(tool_name, {})
    executable = capability.get("executable")
    if not capability.get("available") or not executable:
        operations.append({"id": tool_name, "label": f"Run {tool_name}", "tool": tool_name, "status": "unavailable", "details": "Executable not found; original bytes preserved."})
        return current
    extension = Path(name).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="ui-opt-") as temporary:
        directory = Path(temporary)
        source = directory / ("source" + extension)
        output = directory / ("optimized" + extension)
        source.write_bytes(data)
        if tool_name == "pngcrush":
            command = [executable, "-q", "-rem", "alla", "-reduce", str(source), str(output)]
        elif tool_name == "optipng":
            command = [executable, "-quiet", "-out", str(output), str(source)]
        elif tool_name == "jpegoptim":
            output = directory / source.name
            command = [executable, "--quiet", "--strip-all", "--dest", str(directory), str(source)]
        else:
            command = [executable, "--input", str(source), "--output", str(output), "--multipass"]
        try:
            completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
            if completed.returncode != 0:
                raise RuntimeError((completed.stderr or completed.stdout).decode("utf-8", "replace")[-500:] or f"exit {completed.returncode}")
            if not output.is_file():
                raise RuntimeError("tool produced no output")
            candidate = output.read_bytes()
            if not candidate or len(candidate) >= len(current):
                operations.append({"id": tool_name, "label": f"Run {tool_name}", "tool": tool_name, "status": "unchanged", "details": "Tool output was not smaller; original bytes preserved."})
                return current
            operations.append({"id": tool_name, "label": f"Run {tool_name}", "tool": tool_name, "status": "applied", "details": f"External output measured {len(candidate)} bytes."})
            return candidate
        except (OSError, subprocess.SubprocessError, RuntimeError, UnicodeError) as exc:
            operations.append({"id": tool_name, "label": f"Run {tool_name}", "tool": tool_name, "status": "failed", "details": f"Tool failed; original bytes preserved: {exc}"})
            return current


def _brotli(data: bytes, level: int) -> bytes | None:
    try:
        import brotli  # type: ignore
    except ImportError:
        return None
    return brotli.compress(data, quality=min(level, 11), mode=getattr(brotli, "MODE_GENERIC", 0))


def optimize_bytes(name: str, data: bytes, settings: dict[str, Any], capabilities: dict[str, Any] | None = None) -> tuple[bytes, list[dict[str, Any]], dict[str, Any], dict[str, bytes]]:
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_SOURCE_BYTES:
        raise ValueError(f"Optimization source must be between 1 and {MAX_SOURCE_BYTES} bytes")
    name = _safe_relative(name)
    settings = validate_settings(settings)
    capabilities = capabilities or tool_availability()
    current, operations, measurements = _transform(name, data, settings)
    current = _external_transform(name, data, current, settings, capabilities, operations)
    artifacts: dict[str, bytes] = {}
    if settings["compress"] and identify_type(name) not in {"image", "pdf", "compressed", "binary"}:
        compressed = gzip.compress(current, compresslevel=settings["level"], mtime=0)
        artifacts["gzip"] = compressed
        brotli = _brotli(current, settings["level"])
        if brotli is not None:
            artifacts["brotli"] = brotli
        measurements["gzipBytes"] = len(compressed)
        measurements["brotliBytes"] = len(brotli) if brotli is not None else None
        selected_name, selected = min((("gzip", compressed), ("brotli", brotli)) if brotli is not None else (("gzip", compressed),), key=lambda pair: len(pair[1]))
        if len(selected) < len(current):
            current = selected
            operations.append({"id": "compress", "label": "Create compression artifacts", "tool": selected_name, "status": "applied",
                               "details": "Selected " + selected_name + " after measuring available compression artifacts."})
        else:
            operations.append({"id": "compress", "label": "Create compression artifacts", "tool": "gzip/brotli", "status": "unchanged", "details": "Compression artifacts were larger than transformed bytes; transformed output kept."})
    elif settings["compress"]:
        operations.append({"id": "compress", "label": "Create compression artifacts", "tool": "gzip/brotli", "status": "skipped", "details": "Binary resource is not compressed again."})
    measurements.update({"beforeBytes": len(data), "afterBytes": len(current), "outputSha256": _digest(current),
                          "savingsBytes": len(data) - len(current),
                          "savingsPercent": round((len(data) - len(current)) * 100 / len(data), 2)})
    return current, operations, measurements, artifacts


def _optimization_dir(studio: Any, root: Path) -> Path:
    directory = studio.safe_path(root, "optimization", must_exist=False, allow_dir=True)
    if directory.exists() and directory.is_symlink():
        raise ValueError("Optimization directory cannot be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_settings(studio: Any, root: Path) -> dict[str, Any]:
    path = studio.safe_path(root, "optimization/settings.json", must_exist=False)
    if not path.exists():
        return DEFAULT_SETTINGS()
    value = studio.read_json(path)
    return validate_settings(value)


def save_settings(studio: Any, root: Path, value: Any) -> dict[str, Any]:
    settings = validate_settings(value, base=load_settings(studio, root))
    directory = _optimization_dir(studio, root)
    studio.atomic_json(studio.safe_path(directory, "settings.json", must_exist=False), settings)
    return settings


def _record_valid(studio: Any, root: Path, record: dict[str, Any]) -> bool:
    try:
        if not isinstance(record, dict) or not RESULT_ID.fullmatch(record.get("id", "")):
            return False
        result_root = studio.safe_path(root, record["beforePath"], must_exist=True)
        after = studio.safe_path(root, record["afterPath"], must_exist=True)
        return result_root.is_file() and after.is_file() and result_root.stat().st_size == record["beforeBytes"] and after.stat().st_size == record["afterBytes"]
    except (OSError, ValueError, TypeError, KeyError):
        return False


def result_records(studio: Any, root: Path) -> list[dict[str, Any]]:
    results_root = studio.safe_path(root, "optimization/results", must_exist=False, allow_dir=True)
    if not results_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for target in sorted(results_root.iterdir(), key=lambda item: item.name):
        if target.is_symlink() or not target.is_dir() or not RESULT_ID.fullmatch(target.name):
            continue
        try:
            record = studio.read_json(studio.safe_path(target, "record.json"))
            if _record_valid(studio, root, record):
                records.append(record)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            continue
    return records[-MAX_RESULTS:]


def _write_result(studio: Any, root: Path, source: dict[str, Any], settings: dict[str, Any], capabilities: dict[str, Any], *, example: bool = False) -> dict[str, Any]:
    name = _safe_relative(source["sourceName"])
    data = source["data"]
    after, operations, measurements, artifacts = optimize_bytes(name, data, settings, capabilities)
    identity = _canonical({"name": name, "input": _digest(data), "settings": settings, "capabilities": capabilities})
    result_id = "opt-" + _digest(identity)[:32]
    result_path = f"optimization/results/{result_id}"
    record_path = studio.safe_path(root, result_path, must_exist=False, allow_dir=True)
    if record_path.exists():
        existing = studio.read_json(studio.safe_path(record_path, "record.json"))
        if _record_valid(studio, root, existing):
            return existing
        raise ValueError("Optimization result ID already exists with invalid content")
    results_root = _optimization_dir(studio, root) / "results"
    results_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".result-", dir=results_root))
    try:
        before = temporary / "before"
        after_path = temporary / "after"
        studio.atomic_bytes(before, data, 0o600)
        studio.atomic_bytes(after_path, after, 0o600)
        artifact_paths: dict[str, str] = {}
        for label, content in artifacts.items():
            target = temporary / label
            studio.atomic_bytes(target, content, 0o600)
            artifact_paths[label] = f"{result_path}/{label}"
        record = {"id": result_id, "type": identify_type(name), "sourceName": name,
                  "beforeBytes": len(data), "afterBytes": len(after), "savingsBytes": len(data) - len(after),
                  "savingsPercent": round((len(data) - len(after)) * 100 / len(data), 2),
                  "beforePath": f"{result_path}/before", "afterPath": f"{result_path}/after",
                  "operations": operations, "measurements": {**measurements, "artifacts": artifact_paths},
                  "createdAt": _timestamp(), "example": bool(example)}
        studio.atomic_json(temporary / "record.json", record)
        os.chmod(temporary / "record.json", 0o600)
        os.replace(temporary, record_path)
        return record
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def _example_sources() -> list[dict[str, Any]]:
    # Deterministic real formats with high-contrast, multi-color visual coverage.
    png = zlib.decompress(base64.b64decode("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"))
    jpeg = base64.b64decode("/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYzLjIwLjEwMQD/2wBDAAgQEBMQExYWFhYWFhoYGhsbGxoaGhobGxsdHR0iIiIdHR0bGx0dICAiIiUmJSMjIiMmJigoKDAwLi44ODpFRVP/xABMAAEBAAAAAAAAAAAAAAAAAAAABgEBAQAAAAAAAAAAAAAAAAAABgcQAQAAAAAAAAAAAAAAAAAAAAARAQAAAAAAAAAAAAAAAAAAAAD/wAARCAAIAAgDASIAAhEAAxEA/9oADAMBAAIRAxEAPwCLAE1/f//Z")
    svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="240" viewBox="0 0 480 240"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#16324f"/><stop offset=".5" stop-color="#e85d75"/><stop offset="1" stop-color="#f2c14e"/></linearGradient></defs><rect width="480" height="240" fill="url(#g)"/><circle cx="90" cy="120" r="58" fill="#07111f" stroke="#fff" stroke-width="5"/><circle cx="240" cy="120" r="58" fill="#fff" fill-opacity=".08" stroke="#07111f" stroke-width="5"/><path d="M330 180L390 50l60 130z" fill="#2ec4b6" stroke="#07111f" stroke-width="8" onclick="bad()"/></svg>"""
    return [
        {"sourceName": "sample.png", "data": png},
        {"sourceName": "sample.jpeg", "data": jpeg},
        {"sourceName": "sample.svg", "data": svg},
        {"sourceName": "sample.html", "data": b"<!doctype html>\n<html> <head> <title> Sample </title> </head> <body>  <h1>Hello</h1> <!-- remove --> </body> </html>"},
        {"sourceName": "sample.css", "data": b"/* theme */\n.card { color: #3366ff; padding: 8px 8px; }\n"},
        {"sourceName": "sample.js", "data": b"// greeting\nfunction greet(name) { return \"Hello, \" + name; }\n"},
        {"sourceName": "sample.json", "data": b'{\n  "items": [ 1, 2, 3 ],\n  "title": "Sample"\n}\n'},
        {"sourceName": "sample.txt", "data": b"A short text sample.\n\n\nWith repeated blank lines.\n"},
        {"sourceName": "sample.pdf", "data": b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"},
    ]


def _source_from_payload(studio: Any, root: Path, value: dict[str, Any], reference_loader: Any = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Optimization sources must be objects")
    name = value.get("sourceName", value.get("name"))
    if not isinstance(name, str):
        raise ValueError("Optimization sourceName is required")
    if "data" in value:
        encoded = value["data"]
        if not isinstance(encoded, str):
            raise ValueError("Optimization source data must be base64")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("Optimization source data must be valid base64") from exc
    elif "path" in value:
        relative = _safe_relative(value["path"])
        data = studio.safe_path(root, relative).read_bytes()
    elif reference_loader is not None and isinstance(value.get("referenceId", value.get("id")), str):
        reference_id = value.get("referenceId", value.get("id"))
        record, data = reference_loader.file(reference_id)
        name = value.get("sourceName") or record["originalName"]
    else:
        raise ValueError("Optimization source must contain data, path, or referenceId")
    if not 1 <= len(data) <= MAX_SOURCE_BYTES:
        raise ValueError(f"Optimization source must be between 1 and {MAX_SOURCE_BYTES} bytes")
    return {"sourceName": _safe_relative(name), "data": data}


def run_optimization(studio: Any, root: Path, payload: Any = None, reference_loader: Any = None) -> dict[str, Any]:
    """Run requested sources and atomically persist settings and output bytes."""
    payload = {} if payload is None else payload
    if not isinstance(payload, dict):
        raise ValueError("Optimization request must be an object")
    allowed = {"settings", "sources", "source", "paths", "ids", "referenceIds", "example", "examples"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError("Optimization request contains unsupported fields: " + ", ".join(sorted(unknown)))
    settings_value = payload.get("settings", load_settings(studio, root))
    settings = validate_settings(settings_value, base=load_settings(studio, root))
    save_settings(studio, root, settings)
    capabilities = tool_availability()
    sources: list[dict[str, Any]] = []
    if payload.get("example") or payload.get("examples"):
        sources.extend(_example_sources())
    raw_sources = payload.get("sources", [])
    if raw_sources:
        if not isinstance(raw_sources, list) or len(raw_sources) > MAX_SOURCES:
            raise ValueError(f"Optimization sources must contain at most {MAX_SOURCES} items")
        sources.extend(_source_from_payload(studio, root, item, reference_loader) for item in raw_sources)
    if isinstance(payload.get("source"), dict):
        sources.append(_source_from_payload(studio, root, payload["source"], reference_loader))
    paths = payload.get("paths", [])
    if paths:
        if not isinstance(paths, list) or len(paths) > MAX_SOURCES:
            raise ValueError(f"Optimization paths must contain at most {MAX_SOURCES} items")
        sources.extend(_source_from_payload(studio, root, {"path": path, "sourceName": path}) for path in paths)
    ids = payload.get("referenceIds", payload.get("ids", []))
    if ids:
        if reference_loader is None or not isinstance(ids, list) or len(ids) > MAX_SOURCES:
            raise ValueError("Optimization referenceIds are invalid")
        sources.extend(_source_from_payload(studio, root, {"referenceId": reference_id}, reference_loader) for reference_id in ids)
    if not sources:
        sources = _example_sources()
    if len(sources) > MAX_SOURCES:
        raise ValueError(f"Optimization sources must contain at most {MAX_SOURCES} items")
    results = [_write_result(studio, root, source, settings, capabilities, example=source["sourceName"].startswith("sample.")) for source in sources]
    return {"status": "PASS", "schemaVersion": SCHEMA_VERSION, "settings": settings,
            "capabilities": capabilities, "recommendations": recommendations(settings, capabilities),
            "results": results, "examples": [item for item in results if item.get("example")]}


def projection(studio: Any, root: Path, *, include_examples: bool = True) -> dict[str, Any]:
    settings = load_settings(studio, root)
    capabilities = tool_availability()
    records = result_records(studio, root)
    examples = [record for record in records if record.get("example")] if include_examples else []
    return {"schemaVersion": SCHEMA_VERSION, "settings": settings, "capabilities": capabilities,
            "recommendations": recommendations(settings, capabilities), "results": records, "examples": examples}


def ensure_examples(studio: Any, root: Path) -> dict[str, Any]:
    existing = projection(studio, root)
    if len(existing["examples"]) >= len(_example_sources()):
        return existing
    return run_optimization(studio, root, {"example": True, "settings": existing["settings"]})


def read_content(studio: Any, root: Path, result_id: str, variant: str = "after") -> tuple[dict[str, Any], bytes, str]:
    if not isinstance(result_id, str) or not RESULT_ID.fullmatch(result_id) or variant not in {"before", "after", "gzip", "brotli"}:
        raise ValueError("Optimization result path is invalid")
    result = next((record for record in result_records(studio, root) if record["id"] == result_id), None)
    if result is None:
        raise ValueError("Optimization result not found")
    relative = result["afterPath"] if variant == "after" else result["beforePath"]
    if variant in {"gzip", "brotli"}:
        relative = result.get("measurements", {}).get("artifacts", {}).get(variant, "")
        if not relative:
            raise ValueError("Optimization artifact not found")
    path = studio.safe_path(root, relative, must_exist=True)
    data = path.read_bytes()
    return result, data, ("application/gzip" if variant == "gzip" else "application/octet-stream" if variant == "brotli" else "application/octet-stream")
