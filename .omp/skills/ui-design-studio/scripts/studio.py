#!/usr/bin/env python3
"""UI Design Studio: portable theme packaging and honest evidence gates.

Python >=3.10, standard library only. Run from a virtual environment.
These checks validate declared artifacts; they do not replace browser, usability,
screen-reader, security, or application integration reviews.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import datetime as dt
import gzip
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile
import xml.etree.ElementTree as ET

VERSION = "1.2.0"
SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED_TOKENS = {
    **{f"color.{name}": "color" for name in (
        "background", "surface", "text", "muted", "primary", "on-primary",
        "border", "focus", "danger", "on-danger", "success", "on-success")},
    **{f"space.{name}": "dimension" for name in ("1", "2", "3", "4", "6", "8")},
    **{f"radius.{name}": "dimension" for name in ("sm", "md", "lg")},
    "motion.fast": "duration", "font.family": "fontFamily",
}
REQUIRED_CONTRASTS = [
    ("color.text", "color.background", 4.5),
    ("color.text", "color.surface", 4.5),
    ("color.muted", "color.background", 4.5),
    ("color.on-primary", "color.primary", 4.5),
    ("color.on-danger", "color.danger", 4.5),
    ("color.on-success", "color.success", 4.5),
    ("color.focus", "color.background", 3.0),
    ("color.border", "color.surface", 3.0),
]
REQUIRED_EVIDENCE = {"integration", "visual", "accessibility", "offline", "performance", "review"}
SPECIALIST_AGENTS = {
    "ui-ux-researcher", "ui-art-director", "ui-page-designer", "ui-theme-engineer",
    "ui-implementer", "ui-quality-reviewer", "ui-performance-reviewer",
}


class StudioError(Exception):
    """A failed deterministic check or invalid input."""


def require(condition, message):
    if not condition:
        raise StudioError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return digest_bytes(Path(path).read_bytes())


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_json(path):
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StudioError(f"Cannot read JSON {path}: {exc}") from exc


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def validate_slug(value):
    require(isinstance(value, str) and len(value) <= 64 and SLUG.fullmatch(value),
            "Theme IDs must start with a lowercase letter, contain lowercase letters/digits/hyphens, and be <=64 characters")
    return value


def safe_path(root, relative, *, must_exist=True, allow_dir=False):
    require(isinstance(relative, str) and relative and "\\" not in relative,
            f"Invalid portable relative path: {relative!r}")
    part = PurePosixPath(relative)
    require(not part.is_absolute() and all(p not in (".", "..") for p in part.parts)
            and ":" not in relative and not any(ord(c) < 32 for c in relative),
            f"Unsafe relative path: {relative!r}")
    root = Path(root).resolve()
    path = root.joinpath(*part.parts)
    cursor = root
    for piece in part.parts:
        cursor = cursor / piece
        require(not cursor.is_symlink(), f"Symlink is not permitted: {cursor}")
    require(path.resolve().is_relative_to(root), f"Path escapes its root: {relative}")
    if must_exist:
        require(path.exists(), f"Missing referenced file: {relative}")
        require(path.is_file() or (allow_dir and path.is_dir()), f"Not a regular file: {relative}")
    return path


def config_paths(repo):
    repo = Path(repo).resolve()
    cfg = read_json(repo / "ui-design-studio.json") if (repo / "ui-design-studio.json").exists() else {}
    require(isinstance(cfg, dict), "ui-design-studio.json must be an object")
    paths = cfg.get("paths", {})
    require(isinstance(paths, dict), "Configuration paths must be an object")
    return cfg, safe_path(repo, paths.get("themes", "themes"), must_exist=False, allow_dir=True), safe_path(
        repo, paths.get("runs", "docs/design/runs"), must_exist=False, allow_dir=True)


def flatten_tokens(document):
    require(isinstance(document, dict), "Token document must be an object")
    result = {}

    def walk(obj, parts, inherited_type=None):
        require(isinstance(obj, dict), f"Token/group {'.'.join(parts)} must be an object")
        current_type = obj.get("$type", inherited_type)
        if "$value" in obj:
            require(parts, "Root cannot itself be a token")
            require(current_type in ("color", "dimension", "duration", "number", "fontFamily"),
                    f"Unsupported token type at {'.'.join(parts)}: {current_type!r}")
            require(not any(not k.startswith("$") for k in obj), f"Token contains nested tokens: {'.'.join(parts)}")
            result[".".join(parts)] = {"$type": current_type, "$value": obj["$value"]}
            return
        for key, child in obj.items():
            require(isinstance(key, str), "Token keys must be strings")
            if key.startswith("$"):
                continue
            require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key), f"Unsupported token key: {key!r}")
            walk(child, parts + [key], current_type)

    walk(document, [])
    require(result, "No tokens found")
    css_names = ["--ui-" + key.replace(".", "-") for key in result]
    require(len(css_names) == len(set(css_names)), "Token paths collide when converted to CSS names")
    resolved = {}

    def resolve(key, stack):
        require(key in result, f"Unknown token alias: {key}")
        require(key not in stack, f"Token alias cycle: {' -> '.join(stack + [key])}")
        if key in resolved:
            return resolved[key]
        token = result[key]
        value = token["$value"]
        if isinstance(value, str) and re.fullmatch(r"\{[^{}]+\}", value):
            target = value[1:-1]
            other = resolve(target, stack + [key])
            require(token["$type"] == other["$type"], f"Token alias type mismatch: {key} -> {target}")
            value = other["$value"]
        validate_token_value(key, token["$type"], value)
        resolved[key] = {"$type": token["$type"], "$value": value}
        return resolved[key]

    for key in result:
        resolve(key, [])
    for key, token_type in REQUIRED_TOKENS.items():
        require(key in resolved, f"Missing semantic token: {key}")
        require(resolved[key]["$type"] == token_type, f"Incorrect type for {key}: expected {token_type}")
    return resolved


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_token_value(key, token_type, value):
    if token_type == "color":
        require(isinstance(value, dict) and value.get("colorSpace") == "srgb", f"{key}: use a DTCG srgb color object")
        parts = value.get("components")
        require(isinstance(parts, list) and len(parts) == 3 and all(numeric(v) and 0 <= v <= 1 for v in parts),
                f"{key}: srgb components must be three finite numbers in [0,1]")
        require(numeric(value.get("alpha", 1)) and 0 <= value.get("alpha", 1) <= 1, f"{key}: invalid alpha")
    elif token_type in ("dimension", "duration"):
        units = ("px", "rem") if token_type == "dimension" else ("ms",)
        require(isinstance(value, dict) and numeric(value.get("value")) and value["value"] >= 0 and value.get("unit") in units,
                f"{key}: expected a nonnegative value with unit {units}")
    elif token_type == "number":
        require(numeric(value), f"{key}: expected a finite number")
    elif token_type == "fontFamily":
        require(isinstance(value, list) and value and all(isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9 -]+", item) and item.strip() for item in value),
                f"{key}: fontFamily must be a nonempty array of plain local/system font names")


def fmt(value):
    return format(value, ".8g")


def css_value(key, token):
    kind, value = token["$type"], token["$value"]
    if kind == "color":
        parts = " ".join(fmt(v * 100) + "%" for v in value["components"])
        alpha = value.get("alpha", 1)
        return f"rgb({parts}" + (f" / {fmt(alpha)}" if alpha != 1 else "") + ")"
    if kind in ("dimension", "duration"):
        return fmt(value["value"]) + value["unit"]
    if kind == "number":
        return fmt(value)
    if kind == "fontFamily":
        generic = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "fangsong"}
        return ", ".join(item if item in generic or re.fullmatch(r"[-A-Za-z][A-Za-z0-9-]*", item) else json.dumps(item) for item in value)
    return json.dumps(value, ensure_ascii=True)


def token_css(theme_id, tokens):
    lines = ["/* Generated by UI Design Studio. Edit tokens.json, then run build-theme. */",
             f'[data-ui-theme="{theme_id}"] {{']
    for key in sorted(tokens):
        lines.append(f"  --ui-{key.replace('.', '-')}: {css_value(key, tokens[key])};")
    return "\n".join(lines + ["}", ""])


def luminance(color):
    parts = color["components"]
    converted = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in parts]
    return sum(v * weight for v, weight in zip(converted, (0.2126, 0.7152, 0.0722)))


def contrast(foreground, background):
    require(foreground.get("alpha", 1) == 1 and background.get("alpha", 1) == 1,
            "Declared contrast pairs must be opaque; composite alpha on the actual surface in browser QA")
    values = sorted((luminance(foreground), luminance(background)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def check_svg(path):
    content = path.read_text(encoding="utf-8")
    require(not re.search(r"<!DOCTYPE|<!ENTITY", content, re.I), f"SVG DTD/entity is forbidden: {path.name}")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise StudioError(f"Invalid SVG {path.name}: {exc}") from exc
    allowed = {"svg", "symbol", "g", "defs", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "title", "desc", "use", "clipPath", "mask", "linearGradient", "radialGradient", "stop"}
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        require(tag in allowed, f"SVG element not in passive-vector subset: {tag}")
        for key, value in element.attrib.items():
            local = key.rsplit("}", 1)[-1].lower()
            require(not local.startswith("on") and local != "style", f"Unsafe SVG attribute: {local}")
            if local == "href":
                require(value.startswith("#") and len(value) > 1, "SVG references must be internal fragment IDs")
            if re.search(r"url\s*\(", value, re.I):
                require(re.fullmatch(r"url\(#[A-Za-z_][\w.-]*\)", value), "SVG paint references must be local fragments")
            require(not re.search(r"javascript:|data:|https?:|//", value, re.I), "SVG remote/active content is forbidden")


def check_css(path, theme_id, root):
    content = path.read_text(encoding="utf-8")
    clean = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
    require(not re.search(r"@import\b|@font-face\b|expression\s*\(|(?:^|[;{])\s*(?:-moz-binding|behavior)\s*:|javascript:", clean, re.I),
            f"CSS imports, embedded font rules, or active CSS are forbidden: {path.name}")
    require("\\" not in clean, f"CSS backslash escapes are outside the supported audited subset: {path.name}")
    for match in re.finditer(r"url\s*\(([^)]*)\)", clean, re.I):
        target = match.group(1).strip().strip("\"'")
        css_asset_relative(root, path, target)
    scope = re.compile(r'\[data-ui-theme\s*=\s*[\"\']' + re.escape(theme_id) + r'[\"\']\]')
    # A deliberately restricted static subset; runtime component behavior still needs review.
    for head in re.findall(r"([^{}]+)\{", clean):
        head = head.strip()
        if head.startswith("@"):
            require(re.match(r"@(media|supports|layer)\b", head), f"Unsupported CSS at-rule in {path.name}: {head[:80]}")
            continue
        for selector in head.split(","):
            require(scope.match(selector.strip()), f"Selector must start with the theme root in {path.name}: {selector.strip()[:120]}")
            require(not re.search(r"[+~]", selector), f"Sibling combinators are outside the isolated CSS subset: {path.name}")
            require(not re.search(r":root\b|(?<![\w.-])(?:html|body)(?![\w-])", selector), f"Global root selector in {path.name}")


def css_asset_relative(root, stylesheet, target):
    if target.startswith("#"):
        return None
    require(not re.match(r"(?:[a-z][a-z0-9+.-]*:|//|/)", target, re.I), f"CSS runtime URLs must be relative local files: {target}")
    require("?" not in target and "#" not in target, "CSS file URLs with query/fragment suffixes are outside the supported subset")
    relative = str(PurePosixPath(Path(stylesheet).relative_to(root).as_posix()).parent / target)
    safe_path(root, relative)
    return relative


def load_theme(path):
    root = Path(path)
    require(root.is_dir() and not root.is_symlink(), f"Theme directory not found or is a symlink: {root}")
    root = root.resolve()
    manifest = read_json(safe_path(root, "theme.json"))
    require(isinstance(manifest, dict), "theme.json must be an object")
    require(manifest.get("schemaVersion") == "1.0", "Unsupported theme schemaVersion; expected 1.0")
    theme_id = validate_slug(manifest.get("id"))
    require(isinstance(manifest.get("version"), str) and SEMVER.fullmatch(manifest["version"]), "Theme version must be semantic version e.g. 1.0.0")
    for field in ("name", "description", "author", "license"):
        require(isinstance(manifest.get(field), str) and manifest[field].strip(), f"Missing theme {field}")
    compat = manifest.get("compatibility", {})
    require(isinstance(compat, dict) and compat.get("themeApi") == "1" and isinstance(compat.get("framework"), str),
            "compatibility must declare themeApi=1 and framework")
    require(manifest.get("tokens") == "tokens.json", "v1 token source must be tokens.json")
    styles = manifest.get("styles")
    require(isinstance(styles, list) and styles and styles[0] == "tokens.css" and "theme.css" in styles,
            "styles must start with tokens.css and include theme.css")
    require(all(isinstance(s, str) and s.endswith(".css") for s in styles) and len(styles) == len(set(styles)), "Invalid/duplicate stylesheet paths")
    require(isinstance(manifest.get("icons"), str) and manifest["icons"].endswith(".svg"), "icons must name an SVG sprite")
    require(isinstance(manifest.get("preview"), str) and manifest["preview"].endswith(".html"), "preview must name a local HTML file")
    assets = manifest.get("assets", [])
    require(isinstance(assets, list) and all(isinstance(x, str) for x in assets), "assets must be a list of relative file paths")
    for relative in ["tokens.json", *styles, manifest["icons"], manifest["preview"], *assets, "README.md", "LICENSE.txt", "CHANGELOG.md"]:
        if relative == "tokens.css":
            safe_path(root, relative, must_exist=False)
        else:
            safe_path(root, relative)
    tokens = flatten_tokens(read_json(root / "tokens.json"))
    return root, manifest, tokens


def build_theme(path):
    root, manifest, tokens = load_theme(path)
    output = root / "tokens.css"
    output.write_text(token_css(manifest["id"], tokens), encoding="utf-8")
    return {"status": "PASS", "file": str(output), "tokenCount": len(tokens)}


def theme_files(manifest):
    runtime = ["theme.json", *manifest["styles"], manifest["icons"], *manifest.get("assets", [])]
    source = [*runtime, "tokens.json"]
    package = [*source, manifest["preview"], "README.md", "LICENSE.txt", "CHANGELOG.md"]
    return sorted(set(runtime)), sorted(set(source)), sorted(set(package))


def check_theme(path):
    root, manifest, tokens = load_theme(path)
    expected = token_css(manifest["id"], tokens)
    require(safe_path(root, "tokens.css").read_text(encoding="utf-8") == expected,
            "tokens.css is stale or edited; run build-theme")
    for style in manifest["styles"]:
        check_css(safe_path(root, style), manifest["id"], root)
    check_svg(safe_path(root, manifest["icons"]))
    for asset in manifest.get("assets", []):
        require(Path(asset).suffix.lower() in (".svg", ".woff2", ".png", ".webp", ".avif", ".jpg", ".jpeg"),
                f"Unsupported runtime asset type: {asset}")
        if Path(asset).suffix.lower() == ".svg":
            check_svg(safe_path(root, asset))
    runtime, source, package = theme_files(manifest)
    known = set(runtime)
    for style in manifest["styles"]:
        for target in re.findall(r"url\s*\(([^)]*)\)", safe_path(root, style).read_text(encoding="utf-8"), flags=re.I):
            target = target.strip().strip("\"'")
            relative = css_asset_relative(root, safe_path(root, style), target)
            require(relative is None or relative in known, f"CSS asset must appear in manifest assets: {relative}")
    pairs = manifest.get("contrastPairs")
    require(isinstance(pairs, list), "contrastPairs must be a list")
    declarations = {}
    contrast_results = []
    for pair in pairs:
        require(isinstance(pair, dict), "Invalid contrast pair")
        fg, bg, minimum = pair.get("foreground"), pair.get("background"), pair.get("minimum")
        require(fg in tokens and bg in tokens and tokens[fg]["$type"] == "color" and tokens[bg]["$type"] == "color", "Contrast pair refers to missing/non-color tokens")
        require(numeric(minimum) and minimum >= 3, "Contrast minimum must be >=3")
        ratio = contrast(tokens[fg]["$value"], tokens[bg]["$value"])
        require(ratio + 1e-9 >= minimum, f"Contrast failure {fg} on {bg}: {ratio:.3f}:1 < {minimum}:1")
        declarations[(fg, bg)] = minimum
        contrast_results.append({"foreground": fg, "background": bg, "ratio": round(ratio, 4), "minimum": minimum})
    for fg, bg, minimum in REQUIRED_CONTRASTS:
        require(declarations.get((fg, bg), 0) >= minimum, f"Required contrast declaration missing/too weak: {fg} on {bg} >= {minimum}")
    raw = sum(safe_path(root, file).stat().st_size for file in runtime)
    gz = sum(len(gzip.compress(safe_path(root, file).read_bytes(), compresslevel=9, mtime=0)) for file in runtime)
    budgets = manifest.get("budgets", {})
    require(isinstance(budgets, dict), "budgets must be an object")
    for name, observed in (("maxRawBytes", raw), ("maxGzipBytes", gz)):
        require(isinstance(budgets.get(name), int) and not isinstance(budgets[name], bool) and budgets[name] > 0, f"Invalid budget: {name}")
        require(observed <= budgets[name], f"Theme {name} exceeded: {observed} > {budgets[name]}")
    hashes = {file: sha_file(safe_path(root, file)) for file in source}
    return {"status": "PASS", "themeId": manifest["id"], "version": manifest["version"],
            "themeDigest": digest_bytes(canonical(hashes)), "hashes": hashes,
            "runtimeRawBytes": raw, "runtimeGzipBytes": gz, "tokenCount": len(tokens),
            "contrast": contrast_results,
            "limits": ["Declared opaque token contrasts only; rendered combinations, states, alpha, focus, keyboard, screen-reader and layout checks still required.",
                       "Static CSS/SVG subset checks are not a security sandbox. Install only trusted reviewed themes.",
                       "Gzip sum is a reproducible estimate for individual files, not measured browser transfer size."]}


def file_digest(root, files):
    require(isinstance(files, list) and files and all(isinstance(x, str) for x in files), "Decision inputs must be a nonempty path list")
    return digest_bytes(canonical({file: sha_file(safe_path(root, file)) for file in sorted(set(files))}))


def context_digest(path):
    """Hash the observed context file; this does not resolve its requirements."""
    root = Path(path).resolve()
    run = read_json(safe_path(root, "run.json"))
    context = run.get("projectContext")
    require(isinstance(context, dict), "This run has no projectContext record")
    return {"status": "PASS", "path": context.get("path"),
            "sha256": sha_file(safe_path(root, context.get("path"))),
            "meaning": "Current context-file digest only; no requirements or approvals were resolved."}


def models_digest(path):
    """Hash the observed routing record; do not choose or configure models."""
    root = Path(path).resolve()
    run = read_json(safe_path(root, "run.json"))
    routing = run.get("modelRouting")
    require(isinstance(routing, dict), "This run has no modelRouting record")
    return {"status": "PASS", "path": routing.get("path"),
            "sha256": sha_file(safe_path(root, routing.get("path"))),
            "meaning": "Current routing-file digest only; no model selection or configuration was changed."}


def is_model_identity(value):
    if not isinstance(value, str) or value.startswith("@") or any(c.isspace() or c in "*?," for c in value):
        return False
    provider, separator, model = value.partition("/")
    return bool(provider and separator and model and not model.startswith("@"))


def check_model_routing(root, run, pending):
    if run["schemaVersion"] == "1.0":
        return None
    policy = run.get("modelPolicy")
    require(policy in ("auto-models", "current-model"), "Model policy must be auto-models or current-model")
    routing = run.get("modelRouting")
    require(isinstance(routing, dict), "Run 1.1 must contain modelRouting")
    status = routing.get("status")
    require(status in ("pending", "resolved"), "modelRouting.status must be pending or resolved")
    actual = sha_file(safe_path(root, routing.get("path")))
    if status != "resolved":
        pending.append("Specialist model routing has not been resolved and recorded")
        return {**routing, "actualSha256": actual}
    require(is_model_identity(routing.get("sessionModel")), "modelRouting.sessionModel must be an exact provider/model identity")
    require(isinstance(routing.get("sessionThinking"), str) and routing["sessionThinking"].strip(),
            "modelRouting.sessionThinking must record the active effort or provider-default")
    assignments = routing.get("assignments")
    require(isinstance(assignments, list) and len(assignments) == len(SPECIALIST_AGENTS),
            "modelRouting must record all seven specialist assignments")
    seen = set()
    for assignment in assignments:
        require(isinstance(assignment, dict), "Model assignments must be objects")
        agent = assignment.get("agent")
        require(isinstance(agent, str) and agent in SPECIALIST_AGENTS and agent not in seen,
                f"Unknown or duplicate model-routing agent: {agent}")
        seen.add(agent)
        require(is_model_identity(assignment.get("model")), f"Model assignment for {agent} must use an exact provider/model identity")
        for field in ("thinking", "rationale"):
            require(isinstance(assignment.get(field), str) and assignment[field].strip(), f"Model assignment for {agent} needs {field}")
        if policy == "current-model":
            require(assignment["model"] == routing["sessionModel"] and assignment["thinking"] == routing["sessionThinking"],
                    f"current-model must retain the active session model and thinking for {agent}")
    recorded = routing.get("sha256")
    require(isinstance(recorded, str) and SHA.fullmatch(recorded) and recorded == actual,
            "Model routing changed or has no current sha256; inspect actual assignments and record its digest")
    return {**routing, "actualSha256": actual}


ROUTING_DIRECTORY = ".ui-design-studio/model-routing"
NATIVE_THINKING = {"minimal", "low", "medium", "high", "xhigh", "max", "auto", "off", "inherit", "provider-default"}


def atomic_bytes(path, data, mode):
    """Write a preflighted regular file while preserving its original mode."""
    path = Path(path)
    fd, raw = tempfile.mkstemp(prefix=".ui-model-write-", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def routing_lock(repo):
    try:
        import fcntl
    except ImportError as exc:
        raise StudioError("Model-routing writes require POSIX advisory locking; use the package in Linux, macOS, or WSL") from exc
    directory = safe_path(repo, ROUTING_DIRECTORY, must_exist=False, allow_dir=True)
    directory.mkdir(parents=True, exist_ok=True)
    lock = safe_path(directory, "operation.lock", must_exist=False)
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise StudioError("Model routing is locked by another live operation; retry when it finishes") from exc
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        yield directory
    finally:
        # Keep the inode: removing a lockfile can split concurrent users onto
        # different locks. The kernel releases this lock even after a crash.
        os.close(descriptor)


def routing_plan(repo, run_path):
    repo = Path(repo).resolve()
    require(repo.is_dir(), "Repository directory does not exist")
    run_root = Path(run_path).resolve()
    require(run_root.is_relative_to(repo), "Model routing run must be inside the specified project")
    run_root = safe_path(repo, run_root.relative_to(repo).as_posix(), allow_dir=True)
    run = read_json(safe_path(run_root, "run.json"))
    require(run.get("schemaVersion") == "1.1", "Model routing helpers require a run 1.1 record")
    require(run.get("modelPolicy") in ("auto-models", "current-model"), "Invalid modelPolicy")
    routing = run.get("modelRouting")
    require(isinstance(routing, dict), "Run has no modelRouting record")
    require(is_model_identity(routing.get("sessionModel")), "Record the active exact provider/model before applying routing")
    require(isinstance(routing.get("sessionThinking"), str) and routing["sessionThinking"].strip(), "Record active session thinking before applying routing")
    assignments = routing.get("assignments")
    require(isinstance(assignments, list) and len(assignments) == len(SPECIALIST_AGENTS), "Record all seven specialist assignments before applying routing")
    seen = set()
    for assignment in assignments:
        require(isinstance(assignment, dict), "Model assignments must be objects")
        agent = assignment.get("agent")
        require(isinstance(agent, str) and agent in SPECIALIST_AGENTS and agent not in seen, f"Unknown or duplicate model-routing agent: {agent}")
        seen.add(agent)
        require(is_model_identity(assignment.get("model")), f"Assignment {agent} needs an exact provider/model identity, not a role or pattern")
        require(assignment.get("thinking") in NATIVE_THINKING, f"Unsupported OMP thinking selection for {agent}")
        require(isinstance(assignment.get("rationale"), str) and assignment["rationale"].strip(), f"Assignment {agent} needs a rationale")
        if run["modelPolicy"] == "current-model":
            require(assignment["model"] == routing["sessionModel"] and assignment["thinking"] == routing["sessionThinking"],
                    f"current-model must retain the active session model and thinking for {agent}")
    plan = {"modelPolicy": run["modelPolicy"], "sessionModel": routing["sessionModel"],
            "sessionThinking": routing["sessionThinking"], "assignments": sorted(assignments, key=lambda item: item["agent"])}
    return repo, run_root, plan


def check_native_overrides(repo, assignments):
    executable = shutil.which("omp")
    require(executable is not None, "OMP executable unavailable; cannot check higher-priority agent model overrides")
    result = subprocess.run([executable, "config", "get", "task.agentModelOverrides", "--json"],
                            cwd=repo, capture_output=True, text=True, timeout=20, check=False)
    require(result.returncode == 0, "OMP could not report effective task.agentModelOverrides; inspect native routing before applying")
    try:
        record = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise StudioError("OMP override output was not valid JSON; no agent files were changed") from exc
    require(isinstance(record, dict) and record.get("key") == "task.agentModelOverrides" and isinstance(record.get("value"), dict),
            "OMP override output did not contain the expected key/value object")
    conflicting = [item["agent"] for item in assignments if record["value"].get(item["agent"]) not in (None, "", [])]
    require(not conflicting, "Higher-priority OMP agent overrides exist for: " + ", ".join(conflicting)
            + ". Preserve them and reconcile the native routing explicitly; do not rename agents to bypass them.")


def render_agent_model(data, assignment):
    """Change the shipped agent's model fields, retaining body and other keys."""
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise StudioError("Agent file must be UTF-8") from exc
    lines = text.splitlines(keepends=True)
    require(lines and lines[0].strip() == "---", "Agent file must begin with YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    require(end is not None, "Agent frontmatter has no closing delimiter")
    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    fields = []
    skipping = False
    matched_name = False
    for line in lines[1:end]:
        key = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:", line)
        if key:
            normalized = key.group(1).replace("_", "-")
            skipping = normalized in ("model", "thinking", "thinking-level")
            if normalized == "name":
                value = line[key.end():].strip().strip("\"'")
                require(value == assignment["agent"], "Agent filename and frontmatter name disagree")
                matched_name = True
            if not skipping:
                fields.append(line)
        elif line.lstrip().startswith("<<:") or re.match(r"^['\"](?:model|thinking|thinking[-_]level)['\"]\s*:", line):
            raise StudioError("Agent uses unsupported YAML routing indirection; inspect it before changing models")
        elif skipping and (not line.strip() or line.startswith((" ", "\t", "-")) or line.lstrip().startswith("#")):
            continue
        else:
            fields.append(line)
    require(matched_name, "Agent frontmatter is missing its expected name")
    fields.append("model: " + json.dumps(assignment["model"], ensure_ascii=False) + newline)
    if assignment["thinking"] != "provider-default":
        fields.append("thinking: " + json.dumps(assignment["thinking"]) + newline)
    return (lines[0] + "".join(fields) + "".join(lines[end:])).encode("utf-8")


def routing_transaction(repo, changes):
    """Roll back already-written agent files if a later write fails."""
    applied = []
    try:
        for path, before, before_mode, after, after_mode in changes:
            require(not path.is_symlink() and path.read_bytes() == before and stat.S_IMODE(path.stat().st_mode) == before_mode,
                    f"Agent changed during routing operation: {path.relative_to(repo)}")
            atomic_bytes(path, after, after_mode)
            applied.append((path, before, before_mode, after, after_mode))
    except BaseException:
        for path, before, before_mode, after, after_mode in reversed(applied):
            atomic_bytes(path, before, before_mode)
        raise


def checked_routing_journal(repo, path):
    journal = read_json(path)
    require(isinstance(journal, dict) and journal.get("schemaVersion") == "1.0" and journal.get("projectRoot") == str(repo), "Invalid model-routing journal")
    entries = journal.get("files")
    require(isinstance(entries, list) and len(entries) == len(SPECIALIST_AGENTS), "Invalid model-routing backup entries")
    expected = {f".omp/agents/{name}.md" for name in SPECIALIST_AGENTS}
    seen = set()
    for entry in entries:
        require(isinstance(entry, dict) and isinstance(entry.get("path"), str), "Invalid model-routing backup entry")
        relative = entry["path"]
        require(relative in expected and relative not in seen, "Unexpected or repeated model-routing backup path")
        seen.add(relative)
        try:
            original = base64.b64decode(entry["beforeBase64"], validate=True)
        except (ValueError, TypeError, KeyError) as exc:
            raise StudioError("Invalid model-routing backup bytes") from exc
        require(digest_bytes(original) == entry.get("beforeSha256"), "Model-routing backup hash mismatch")
        require(isinstance(entry.get("mode"), int) and not isinstance(entry["mode"], bool) and 0 <= entry["mode"] <= 0o7777, "Invalid model-routing backup permissions")
        require(isinstance(entry.get("appliedSha256"), str) and SHA.fullmatch(entry["appliedSha256"]), "Invalid applied routing hash")
    return journal


def models_apply(repo, run_path):
    repo, run_root, plan = routing_plan(repo, run_path)
    check_native_overrides(repo, plan["assignments"])
    plan_digest = digest_bytes(canonical(plan))
    with routing_lock(repo) as directory:
        active = safe_path(directory, "active.json", must_exist=False)
        if active.exists():
            owner = read_json(active)
            require(isinstance(owner, dict) and owner.get("run") == str(run_root), "Another run owns active model routing; restore that run before applying this one")
            journal_path = safe_path(directory, owner.get("journal"))
            journal = checked_routing_journal(repo, journal_path)
            require(journal.get("run") == str(run_root) and journal.get("mappingDigest") == plan_digest,
                    "This run's model mapping changed; restore its prior mapping before applying the new one")
            require(journal.get("status") == "applied", "Previous routing operation was interrupted; use models-restore before retrying")
            for entry in journal["files"]:
                path = safe_path(repo, entry["path"])
                require(sha_file(path) == entry["appliedSha256"] and stat.S_IMODE(path.stat().st_mode) == entry["mode"],
                        f"Managed agent changed after routing: {entry['path']}; preserve the edit and reconcile it explicitly")
            return {"status": "PASS", "alreadyApplied": True, "journal": str(journal_path),
                    "meaning": "Local agent mapping is unchanged; actual live routing still requires verification."}
        entries, changes = [], []
        for assignment in plan["assignments"]:
            relative = f".omp/agents/{assignment['agent']}.md"
            path = safe_path(repo, relative)
            before = path.read_bytes()
            mode = stat.S_IMODE(path.stat().st_mode)
            after = render_agent_model(before, assignment)
            entries.append({"path": relative, "beforeBase64": base64.b64encode(before).decode("ascii"),
                            "beforeSha256": digest_bytes(before), "appliedSha256": digest_bytes(after), "mode": mode})
            changes.append((path, before, mode, after, mode))
        filename = digest_bytes(str(run_root).encode())[:16] + "-" + uuid.uuid4().hex + ".json"
        journal_path = safe_path(directory, filename, must_exist=False)
        journal = {"schemaVersion": "1.0", "projectRoot": str(repo), "run": str(run_root),
                   "createdAt": now(), "status": "prepared", "mappingDigest": plan_digest, "files": entries}
        atomic_json(journal_path, journal)
        atomic_json(active, {"run": str(run_root), "journal": filename})
        files_written = False
        try:
            routing_transaction(repo, changes)
            files_written = True
            journal["status"] = "applied"
            atomic_json(journal_path, journal)
        except BaseException:
            if files_written:
                routing_transaction(repo, [(path, after, after_mode, before, before_mode) for path, before, before_mode, after, after_mode in reversed(changes)])
            # Keep the prepared journal for recovery if rollback did not finish.
            if all(path.exists() and path.read_bytes() == before for path, before, _, _, _ in changes):
                active.unlink(missing_ok=True)
                journal["status"] = "rolled-back"
                atomic_json(journal_path, journal)
            raise
        return {"status": "PASS", "alreadyApplied": False, "agents": len(entries), "journal": str(journal_path),
                "meaning": "Local agent frontmatter updated. No session model, global configuration, provider, or approval setting changed. Verify actual native routing before resolving modelRouting."}


def models_restore(repo, run_path):
    repo = Path(repo).resolve()
    run_root = Path(run_path).resolve()
    require(repo.is_dir() and run_root.is_relative_to(repo), "Model routing run must be inside the specified project")
    with routing_lock(repo) as directory:
        active = safe_path(directory, "active.json", must_exist=False)
        if not active.exists():
            matches = []
            prefix = digest_bytes(str(run_root).encode())[:16] + "-"
            for path in directory.glob(prefix + "*.json"):
                journal = checked_routing_journal(repo, safe_path(directory, path.name))
                if journal.get("run") == str(run_root) and journal.get("status") == "restored":
                    matches.append(path)
            require(matches, "No active or previously restored routing journal exists for this run")
            return {"status": "PASS", "alreadyRestored": True, "meaning": "This run's local routing has already been restored."}
        owner = read_json(active)
        require(isinstance(owner, dict) and owner.get("run") == str(run_root), "Another run owns active model routing; leave its mapping unchanged")
        journal_path = safe_path(directory, owner.get("journal"))
        journal = checked_routing_journal(repo, journal_path)
        require(journal.get("run") == str(run_root) and journal.get("status") in ("prepared", "applied"), "Routing journal is not restorable")
        original_journal = dict(journal)
        changes = []
        for entry in journal["files"]:
            path = safe_path(repo, entry["path"])
            current = path.read_bytes()
            mode = stat.S_IMODE(path.stat().st_mode)
            original = base64.b64decode(entry["beforeBase64"], validate=True)
            if current == original and mode == entry["mode"]:
                continue
            require(digest_bytes(current) == entry["appliedSha256"] and mode == entry["mode"],
                    f"Restore refused because an agent changed after routing: {entry['path']}; later edits were preserved")
            changes.append((path, current, mode, original, entry["mode"]))
        routing_transaction(repo, changes)
        try:
            journal.update(status="restored", restoredAt=now())
            atomic_json(journal_path, journal)
            active.unlink()
        except BaseException:
            routing_transaction(repo, [(path, after, after_mode, before, before_mode) for path, before, before_mode, after, after_mode in reversed(changes)])
            atomic_json(journal_path, original_journal)
            raise
        return {"status": "PASS", "alreadyRestored": False, "agents": len(changes), "journal": str(journal_path),
                "meaning": "Original local agent bytes and modes restored; no global configuration changed."}


def check_project_context(root, run, pending):
    """Validate a source-labelled project brief, without guessing its meaning."""
    if run["schemaVersion"] == "1.0":
        require(run.get("profile") in ("generic", "tada"), "Legacy run profile must be generic or tada")
        return run["profile"] == "tada", None
    context = run.get("projectContext")
    require(isinstance(context, dict), "Run 1.1 must contain projectContext")
    status = context.get("status")
    require(status in ("pending", "resolved"), "projectContext.status must be pending or resolved")
    offline = context.get("offline")
    require(offline in ("unknown", "required", "not-required"),
            "projectContext.offline must be unknown, required, or not-required")
    sources = context.get("sources")
    require(isinstance(sources, list) and all(isinstance(x, str) and x.strip() for x in sources),
            "projectContext.sources must list the actual source locations or user-brief references")
    actual = sha_file(safe_path(root, context.get("path")))
    if status != "resolved":
        pending.append("Project requirements have not been resolved from source material")
    if not sources:
        pending.append("Project context has no recorded requirement sources")
    if offline == "unknown":
        pending.append("Project offline requirement has not been determined")
    recorded = context.get("sha256")
    if not isinstance(recorded, str) or not SHA.fullmatch(recorded):
        pending.append("Project context digest has not been recorded")
    else:
        require(recorded == actual, "Project context changed; reread requirements and record its current digest")
    # A missing/unknown requirement never authorizes waiving the offline gate.
    can_waive_offline = status == "resolved" and bool(sources) and offline == "not-required"
    return not can_waive_offline, {**context, "actualSha256": actual}


def check_run(path):
    root = Path(path).resolve()
    run = read_json(safe_path(root, "run.json"))
    coverage = read_json(safe_path(root, "coverage.json"))
    decisions = read_json(safe_path(root, "decisions.json"))
    require(isinstance(run, dict) and run.get("schemaVersion") in ("1.0", "1.1"), "Run must use schemaVersion 1.0 or 1.1")
    require(all(isinstance(doc, dict) and doc.get("schemaVersion") == "1.0" for doc in (coverage, decisions)), "Coverage and decisions must use schemaVersion 1.0")
    require(run.get("mode") in ("guided", "yolo"), "Run mode must be guided or yolo")
    require(run.get("themeAction") in ("new", "modify-default"), "Run themeAction must be new or modify-default")
    validate_slug(run.get("themeId"))
    pending, errors = [], []
    offline_required, project_context = check_project_context(root, run, pending)
    model_routing = check_model_routing(root, run, pending)
    evidence = run.get("evidence", [])
    require(isinstance(evidence, list), "run.evidence must be a list")
    ids, kinds, hashes = {}, set(), {}
    for entry in evidence:
        require(isinstance(entry, dict), "Evidence entries must be objects")
        eid = entry.get("id")
        require(isinstance(eid, str) and eid and eid not in ids, f"Duplicate/missing evidence ID: {eid}")
        ids[eid] = entry
        kind, status = entry.get("kind"), entry.get("status")
        require(isinstance(kind, str) and kind, f"Evidence {eid} has no kind")
        require(isinstance(entry.get("reviewer"), str) and entry["reviewer"].strip(), f"Evidence {eid} has no reviewer")
        require(isinstance(entry.get("recordedAt"), str) and entry["recordedAt"].strip(), f"Evidence {eid} has no recordedAt")
        if status == "not-applicable":
            require(not offline_required and kind == "offline" and isinstance(entry.get("reason"), str) and entry["reason"].strip(),
                    "Only an explicitly non-required offline check may be not-applicable, with a source-backed reason")
            kinds.add(kind)
            hashes[eid] = {"kind": kind, "status": status, "reason": entry["reason"], "reviewer": entry["reviewer"], "recordedAt": entry["recordedAt"]}
            continue
        if status != "passed":
            (errors if status == "failed" else pending).append(f"Evidence {eid} is {status or 'unverified'}")
            continue
        actual = sha_file(safe_path(root, entry.get("path")))
        require(isinstance(entry.get("sha256"), str) and entry["sha256"] == actual, f"Evidence changed or missing sha256: {eid}")
        hashes[eid] = {"path": entry["path"], "sha256": actual, "kind": kind, "reviewer": entry["reviewer"]}
        kinds.add(kind)
    for kind in sorted(REQUIRED_EVIDENCE - kinds):
        pending.append(f"Required evidence missing: {kind}")
    if coverage.get("inventoryComplete") is not True:
        pending.append("Surface inventory is not complete")
    surfaces = coverage.get("surfaces", [])
    require(isinstance(surfaces, list), "coverage.surfaces must be a list")
    if not surfaces:
        pending.append("No page/dialog surfaces inventoried")
    surface_ids, total_cases = set(), 0
    for surface in surfaces:
        require(isinstance(surface, dict), "Coverage surfaces must be objects")
        sid = surface.get("id")
        require(isinstance(sid, str) and sid and sid not in surface_ids, f"Duplicate/missing surface ID: {sid}")
        surface_ids.add(sid)
        require(surface.get("kind") in ("page", "dialog"), f"Surface {sid}: kind must be page or dialog")
        require(isinstance(surface.get("route"), str) and surface["route"].strip(), f"Surface {sid}: route/entry point missing")
        states, viewports = surface.get("states"), surface.get("viewports")
        require(isinstance(states, list) and states and all(isinstance(x, str) and x for x in states) and len(states) == len(set(states)), f"Surface {sid}: states must be unique nonempty strings")
        require(isinstance(viewports, list) and viewports and all(isinstance(x, str) and x for x in viewports) and len(viewports) == len(set(viewports)), f"Surface {sid}: viewports must be unique nonempty strings")
        cases = surface.get("cases", [])
        require(isinstance(cases, list), f"Surface {sid}: cases must be a list")
        expected = {(s, v) for s in states for v in viewports}
        observed = set()
        for case in cases:
            require(isinstance(case, dict), f"Surface {sid}: case must be object")
            key = (case.get("state"), case.get("viewport"))
            require(key in expected and key not in observed, f"Surface {sid}: duplicate/unknown state-viewport case {key}")
            observed.add(key)
            for field in ("mockup", "implementation"):
                if not case.get(field):
                    pending.append(f"{sid}/{key}: missing {field}")
                else:
                    artifact = safe_path(root, case[field])
                    hashes[f"coverage:{sid}:{key}:{field}"] = {"path": case[field], "sha256": sha_file(artifact)}
            qa = case.get("qaEvidence", [])
            if not isinstance(qa, list) or not qa:
                pending.append(f"{sid}/{key}: no QA evidence")
            else:
                for eid in qa:
                    require(eid in ids, f"{sid}/{key}: unknown QA evidence ID {eid}")
                    if ids[eid].get("status") != "passed":
                        pending.append(f"{sid}/{key}: QA evidence {eid} has not passed")
        for key in sorted(expected - observed):
            pending.append(f"{sid}: missing case {key[0]}/{key[1]}")
        total_cases += len(cases)
    theme_digest = run.get("themeDigest")
    if not isinstance(theme_digest, str) or not SHA.fullmatch(theme_digest):
        pending.append("Final themeDigest has not been recorded")
    review_inputs = {"themeDigest": theme_digest, "coverage": coverage, "evidence": hashes,
        "context": {field: run.get(field) for field in ("themeId", "themeAction", "mode", "profile", "implementer")}}
    if run["schemaVersion"] == "1.1":
        review_inputs["context"].pop("profile")
        review_inputs["context"]["projectContext"] = project_context
        review_inputs["context"]["modelPolicy"] = run["modelPolicy"]
        review_inputs["context"]["modelRouting"] = model_routing
    decisions_list = decisions.get("decisions", [])
    require(isinstance(decisions_list, list), "decisions.decisions must be a list")
    approved, latest = set(), {}
    for decision in decisions_list:
        require(isinstance(decision, dict), "Decision entries must be objects")
        stage = decision.get("stage")
        require(stage in ("plan", "design", "finalize"), f"Unknown decision stage: {stage}")
        require(decision.get("actor") in ("user", "agent-yolo", "director"), "Decision actor must be user, agent-yolo, or director")
        require(decision["actor"] != "director" or stage == "finalize", "Director approval is only valid at finalize")
        require(not (run["mode"] == "guided" and decision["actor"] == "agent-yolo"), "Guided runs cannot record agent-yolo approval")
        require(decision.get("outcome") in ("approved", "rejected", "pending", "superseded"), "Decision outcome must be approved, rejected, pending or superseded")
        latest[stage] = decision
    review_inputs["approvals"] = {stage: latest.get(stage) for stage in ("plan", "design")}
    review_digest = digest_bytes(canonical(review_inputs))
    for stage, decision in latest.items():
        if decision.get("outcome") != "approved":
            continue
        require(isinstance(decision.get("rationale"), str) and decision["rationale"].strip(), f"{stage} approval requires rationale")
        if stage == "finalize":
            expected_digest = review_digest
        else:
            expected_digest = file_digest(root, decision.get("inputs"))
            if stage == "design" and latest.get("plan", {}).get("outcome") == "approved":
                require(set(latest["plan"].get("inputs", [])).issubset(set(decision.get("inputs", []))),
                        "Design approval inputs must include all approved Plan input paths to bind upstream changes")
        require(decision.get("inputsDigest") == expected_digest, f"Stale/missing {stage} approval digest; re-review its actual inputs")
        approved.add(stage)
    for stage in ("plan", "design", "finalize"):
        if stage not in approved:
            pending.append(f"Missing approved {stage} decision")
    if run.get("status") != "passed":
        pending.append("run.status is not passed")
    if run.get("phase") != "finalize":
        pending.append("run.phase is not finalize")
    reviewers = {entry["reviewer"] for entry in evidence if entry.get("kind") == "review" and entry.get("status") == "passed"}
    implementer = run.get("implementer")
    if not isinstance(implementer, str) or not implementer.strip():
        pending.append("run.implementer is missing")
    elif not reviewers or implementer in reviewers:
        pending.append("Independent review must name a reviewer distinct from the implementer")
    return {"status": "FAIL" if errors else "BLOCKED" if pending else "PASS", "runId": run.get("id"),
            "themeId": run["themeId"], "themeDigest": theme_digest, "reviewDigest": review_digest,
            "surfaces": len(surfaces), "cases": total_cases, "pending": pending, "errors": errors,
            "limits": ["Evidence files and recorded approvals are checked for completeness and freshness, not for truth. The director must inspect actual logs/screenshots and independently review the application."]}


def registry_read(root):
    path = root / "registry.json"
    if not path.exists():
        return {"schemaVersion": "1.0", "defaultTheme": None, "themes": []}
    data = read_json(safe_path(root, "registry.json"))
    require(isinstance(data, dict) and data.get("schemaVersion") == "1.0" and isinstance(data.get("themes"), list), "Existing theme registry is invalid; repair/import it explicitly")
    ids = [item.get("id") for item in data["themes"] if isinstance(item, dict)]
    require(len(ids) == len(data["themes"]) and len(ids) == len(set(ids)), "Existing registry has malformed/duplicate themes")
    for theme_id in ids:
        validate_slug(theme_id)
    require(data.get("defaultTheme") is None or data.get("defaultTheme") in ids, "Existing default theme is not registered")
    require(not ids or data.get("defaultTheme") in ids, "Nonempty registry must declare a registered default")
    return data


def init_run(repo, mode="guided", profile=None, action="auto", theme_id=None, model_policy=None):
    # Keep the old positional Python signature for callers. Profiles no longer
    # select constraints; the director must read the project's current sources.
    require(mode in ("guided", "yolo"), "Run mode must be guided or yolo")
    require(action in ("auto", "new", "modify-default"), "Invalid theme action")
    validate_slug(theme_id)
    repo = Path(repo).resolve()
    require(repo.is_dir(), "Repository directory does not exist")
    config, themes, runs = config_paths(repo)
    model_policy = model_policy or config.get("modelPolicy", "auto-models")
    require(model_policy in ("auto-models", "current-model"), "Model policy must be auto-models or current-model")
    registry = registry_read(themes)
    default = registry.get("defaultTheme")
    if action == "auto":
        if default:
            require(mode == "yolo", "A default theme exists: guided mode must choose --theme-action modify-default or new")
            action = "new"
        else:
            action = "new"
    if action == "modify-default":
        require(default, "No registered default theme exists; inventory/import any legacy theme before choosing an action")
        require(theme_id == default, "modify-default must use the current default theme ID")
    if action == "new":
        require(theme_id not in {item["id"] for item in registry["themes"]}, "New-theme ID is already registered")
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + theme_id
    root = runs / run_id
    root.mkdir(parents=True, exist_ok=False)
    atomic_json(root / "run.json", {"schemaVersion": "1.1", "id": run_id, "createdAt": now(), "mode": mode,
        "projectContext": {"status": "pending", "path": "project-context.md", "sha256": None, "offline": "unknown", "sources": []},
        "modelPolicy": model_policy,
        "modelRouting": {"status": "pending", "path": "model-routing.md", "sha256": None, "sessionModel": None, "sessionThinking": None, "assignments": []},
        "themeAction": action, "themeId": theme_id, "phase": "assessment", "status": "pending",
        "themeDigest": None, "implementer": None, "evidence": []})
    atomic_json(root / "coverage.json", {"schemaVersion": "1.0", "inventoryComplete": False, "surfaces": []})
    atomic_json(root / "decisions.json", {"schemaVersion": "1.0", "decisions": []})
    (root / "project-context.md").write_text("# Project context\n\nStatus: pending. Read the project's current requirements before resolving this record.\n\n## Sources inspected\n\nList applicable instructions, requirements, current user brief, architecture, implementation, and existing theme contracts with their locations/revisions.\n\n## Required behaviour and constraints\n\nRecord the users/tasks, platforms, accessibility, brand, layout, offline/network, performance, dependencies, Git, and verification requirements. Cite each material constraint and distinguish observed facts, explicit requirements, assumptions, and unresolved conflicts.\n\n## Offline applicability\n\nUnknown. Determine whether offline operation is required from the sources; do not infer it from a project name or an old profile.\n", encoding="utf-8")
    (root / "model-routing.md").write_text("# Model routing\n\nStatus: pending. Discover the active model, available authorized models, supported thinking levels, and existing per-agent routing.\n\n## Active session snapshot\n\nRecord exact provider/model and actual thinking level, or provider-default. The director remains on the selected active session model.\n\n## Specialist assignments\n\nRecord all seven specialist agent names, selected provider/model, actual thinking, rationale, fallback constraints, and observed native routing. In current-model mode every specialist must match the active session snapshot; in auto-models mode choose suitable available models through authorized native routing. Do not enable permissions or providers to make a selection work.\n", encoding="utf-8")
    (root / "report.md").write_text("# UI assessment\n\nStatus: pending. No assessment or verification has been performed.\n\n## Scope and evidence\n\nRecord the inspected commit, pages/dialogs, users/tasks, constraints, evidence, severity, recommendations, confidence, and unverified areas.\n", encoding="utf-8")
    return {"status": "PASS", "run": str(root), "themeAction": action,
            "message": "Run initialized pending. Inventory any existing app theme before treating this as a first theme; no theme or approval has been created."}


def theme_new(repo, theme_id, name):
    validate_slug(theme_id)
    require(isinstance(name, str) and name.strip(), "Theme name cannot be empty")
    _, themes, _ = config_paths(repo)
    target = themes / theme_id
    require(not target.exists() and not target.is_symlink(), f"Theme path already exists: {target}")
    specimen = Path(__file__).resolve().parent.parent / "assets/example-theme"
    require(specimen.is_dir(), "Bundled assets/example-theme is missing; reinstall the complete package")
    for path in specimen.rglob("*"):
        require(not path.is_symlink(), "Bundled theme contains a symlink")
    shutil.copytree(specimen, target)
    manifest = read_json(target / "theme.json")
    old_id = manifest["id"]
    manifest.update(id=theme_id, name=name, version="1.0.0")
    atomic_json(target / "theme.json", manifest)
    for path in target.rglob("*"):
        if path.is_file() and path.suffix in (".css", ".html", ".md"):
            content = path.read_text(encoding="utf-8")
            content = content.replace(f'data-ui-theme="{old_id}"', f'data-ui-theme="{theme_id}"').replace(f"data-ui-theme='{old_id}'", f"data-ui-theme='{theme_id}'")
            path.write_text(content, encoding="utf-8")
    build_theme(target)
    result = check_theme(target)
    return {"status": "PASS", "theme": str(target), "themeDigest": result["themeDigest"],
            "message": "Scaffolded only; app integration and approval are still pending. No default was changed."}


def _design_backend():
    """Load the sibling only on use, including importlib-based Python callers."""
    import importlib.util
    import types
    if not hasattr(_design_backend, "module"):
        path = Path(__file__).with_name("design_server.py")
        spec = importlib.util.spec_from_file_location("ui_design_studio_design_server", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.studio = types.SimpleNamespace(**globals())
        _design_backend.module = module
    return _design_backend.module


def _registered_result(result, run_path):
    try:
        run = read_json(Path(run_path) / "run.json")
        if run.get("mode") == "yolo":
            backend = _design_backend()
            cleanup = backend.cleanup_registered_yolo(backend.studio, run_path)
            if cleanup is not None:
                result["cleanup"] = cleanup
    except (StudioError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        result["cleanup"] = {"status": "FAIL", "error": str(exc)}
    if result.get("cleanup", {}).get("status") == "FAIL":
        result["status"] = "BLOCKED"
        result["message"] = "Registry registration succeeded; automatic design server cleanup remains pending. Retry design-cleanup for this run."
    return result


def register_theme(repo, theme_id, run_path, make_default=False):
    validate_slug(theme_id)
    repo = Path(repo).resolve()
    cfg, themes, _ = config_paths(repo)
    verification = check_theme(themes / theme_id)
    require(verification["themeId"] == theme_id, "Registered theme directory ID must match theme.json id and its CSS scope")
    project_budgets = cfg.get("budgets", {})
    require(isinstance(project_budgets, dict), "Project budgets must be an object")
    for key, observed in (("maxThemeRawBytes", verification["runtimeRawBytes"]), ("maxThemeGzipBytes", verification["runtimeGzipBytes"])):
        if key in project_budgets:
            limit = project_budgets[key]
            require(isinstance(limit, int) and not isinstance(limit, bool) and limit > 0, f"Invalid project budget: {key}")
            require(observed <= limit, f"Project {key} exceeded: {observed} > {limit}")
    run_result = check_run(run_path)
    require(run_result["status"] == "PASS", f"Run is {run_result['status']}: {run_result['pending'] + run_result['errors']}")
    require(run_result["themeId"] == theme_id and run_result["themeDigest"] == verification["themeDigest"], "Run theme ID/digest does not match the current theme")
    lock = safe_path(themes, ".registry.lock", must_exist=False)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise StudioError("Registry is locked by another finalization. Inspect that operation before retrying; do not remove a live lock.") from exc
    try:
        os.write(fd, f"{os.getpid()} {now()}\n".encode())
        registry = registry_read(themes)
        first = len(registry["themes"]) == 0
        run_document = read_json(Path(run_path) / "run.json")
        existing = next((item for item in registry["themes"] if item["id"] == theme_id), None)
        if existing and all(existing.get(key) == value for key, value in (
                ("version", verification["version"]), ("themeDigest", verification["themeDigest"]), ("runId", run_result["runId"]))):
            return _registered_result({"status": "PASS", "registry": str(themes / "registry.json"), "defaultTheme": registry["defaultTheme"],
                    "alreadyRegistered": True, "backup": None,
                    "message": "Identical run/version/digest is already registered; no registry or default change was made."}, run_path)
        if run_document["themeAction"] == "new":
            require(existing is None, "New theme ID is already registered; choose a new ID or explicitly start a modify-default run")
        if run_document["themeAction"] == "modify-default":
            require(registry.get("defaultTheme") == theme_id, "Default changed since the run began; re-evaluate the requested modification")
            require(existing is not None, "Cannot modify a default without an existing registered theme")
            if existing.get("themeDigest") != verification["themeDigest"]:
                require(semver_newer(verification["version"], existing.get("version")),
                        "Changed default theme bytes require a newer semantic version than the registered version")
        # A registry update is metadata, not a claim that the application's adapter has activated it.
        record = {"id": theme_id, "version": verification["version"], "path": theme_id,
                  "themeDigest": verification["themeDigest"], "verifiedAt": now(), "runId": run_result["runId"]}
        registry["themes"] = [item for item in registry["themes"] if item["id"] != theme_id] + [record]
        if first or make_default:
            registry["defaultTheme"] = theme_id
        path = themes / "registry.json"
        backup = None
        if path.exists():
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = safe_path(themes, f".registry-backups/registry-{stamp}.json", must_exist=False)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
        atomic_json(path, registry)
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)
    return _registered_result({"status": "PASS", "registry": str(path), "defaultTheme": registry["defaultTheme"],
            "backup": str(backup) if backup else None,
            "message": "Registry updated atomically. The app's reviewed adapter must consume this registry; this command does not deploy or activate a running application."}, run_path)


def semver_newer(candidate, previous):
    """Compare SemVer precedence without runtime dependencies; build metadata is ignored."""
    require(isinstance(previous, str) and SEMVER.fullmatch(previous), "Existing registered semantic version is invalid")

    def parts(version):
        core, separator, prerelease = version.split("+", 1)[0].partition("-")
        return tuple(int(piece) for piece in core.split(".")), prerelease.split(".") if separator else None

    current_core, current_pre = parts(candidate)
    previous_core, previous_pre = parts(previous)
    if current_core != previous_core:
        return current_core > previous_core
    if current_pre is None or previous_pre is None:
        return previous_pre is not None and current_pre is None
    for current, old in zip(current_pre, previous_pre):
        if current == old:
            continue
        if current.isdigit() and old.isdigit():
            return int(current) > int(old)
        if current.isdigit() != old.isdigit():
            return not current.isdigit()
        return current > old
    return len(current_pre) > len(previous_pre)


def package_theme(path, output):
    result = check_theme(path)
    root, manifest, _ = load_theme(path)
    _, _, files = theme_files(manifest)
    output = Path(output).resolve()
    require(not output.exists(), f"Output already exists; choose a new path: {output}")
    require(not output.is_relative_to(root), "Theme ZIP output must be outside the source theme directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    checksums = "".join(f"{sha_file(safe_path(root, file))}  {file}\n" for file in files).encode()
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as handle:
        temp = Path(handle.name)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, data in [(file, safe_path(root, file).read_bytes()) for file in files] + [("checksums.sha256", checksums)]:
                item = zipfile.ZipInfo(manifest["id"] + "/" + relative, date_time=(1980, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o100644 << 16
                archive.writestr(item, data)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    return {"status": "PASS", "file": str(output), "sha256": sha_file(output), "bytes": output.stat().st_size,
            "themeDigest": result["themeDigest"], "message": "Theme package created; package validity alone does not certify app integration."}


def doctor(repo):
    repo = Path(repo).resolve()
    require(repo.is_dir(), "Repository directory does not exist")
    cfg, themes, runs = config_paths(repo)
    findings = {"python": sys.version.split()[0], "virtualEnvironment": sys.prefix != sys.base_prefix,
                "git": shutil.which("git") is not None, "ompExecutable": shutil.which("omp") is not None,
                "nodeExecutable": shutil.which("node") is not None, "frameworkHints": [],
                "themeDirectory": str(themes), "runDirectory": str(runs), "configPresent": bool(cfg)}
    for relative in ("package.json", "apps/web/package.json", "apps/ui/package.json", "frontend/package.json", "web/package.json"):
        path = repo / relative
        if path.is_file():
            try:
                package = read_json(path)
                deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
                findings["frameworkHints"].append({"file": relative, "packages": [key for key in ("react", "next", "vue", "svelte", "@angular/core", "vite", "@playwright/test", "@axe-core/playwright") if key in deps]})
            except (StudioError, TypeError):
                findings["frameworkHints"].append({"file": relative, "error": "Could not parse dependency metadata"})
    if findings["git"]:
        result = subprocess.run(["git", "-C", str(repo), "status", "--short", "--branch"], capture_output=True, text=True, timeout=10, check=False)
        findings["gitStatus"] = result.stdout.strip() if result.returncode == 0 else "Not a Git working tree"
    findings["uncheckedCapabilities"] = ["Installed OMP task schema and available agent count", "Browser/screenshot/accessibility tooling", "Actual app routes and running frontend", "Project gate commands and representative device performance"]
    findings["status"] = "PASS"
    findings["meaning"] = "Read-only discovery completed. PASS is not a design, usability, browser, or application gate."
    return findings


def parser():
    main = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    main.add_argument("--version", action="version", version=VERSION)
    subs = main.add_subparsers(dest="command", required=True)
    sub = subs.add_parser("doctor", help="Read-only local capability/framework hints; does not run app tests")
    sub.add_argument("--repo", required=True)
    sub = subs.add_parser("init-run", help="Create a pending assessment dossier; never grants approval")
    sub.add_argument("--repo", required=True)
    sub.add_argument("--mode", choices=("guided", "yolo"), default="guided")
    sub.add_argument("--profile", choices=("tada", "generic"), default=None, help=argparse.SUPPRESS)
    sub.add_argument("--models", choices=("auto-models", "current-model"), default=None,
                     help="Model policy; defaults to project modelPolicy or auto-models")
    sub.add_argument("--theme-action", choices=("auto", "modify-default", "new"), default="auto")
    sub.add_argument("--theme-id", required=True)
    sub = subs.add_parser("theme-new", help="Copy bundled specimen into a new unregistered theme")
    sub.add_argument("--repo", required=True)
    sub.add_argument("--id", required=True)
    sub.add_argument("--name", required=True)
    for name, help_text in (("build-theme", "Compile the supported DTCG token subset to scoped CSS"), ("check-theme", "Validate packaging, token subset, declared contrasts, CSS/SVG and budgets"), ("theme-digest", "Return the current validated theme digest"), ("context-digest", "Hash the recorded project-context file without resolving requirements"), ("models-digest", "Hash recorded model-routing evidence without choosing models"), ("check-run", "Check declared coverage, evidence freshness and approvals")):
        sub = subs.add_parser(name, help=help_text)
        sub.add_argument("path")
    sub = subs.add_parser("decision-digest", help="Hash current run-relative Plan/Design approval input files")
    sub.add_argument("path")
    sub.add_argument("--files", required=True, nargs="+")
    sub = subs.add_parser("package", help="Validate and create a deterministic portable theme ZIP")
    sub.add_argument("path")
    sub.add_argument("--output", required=True)
    sub = subs.add_parser("register", help="Register only a verified theme; first finalized theme becomes default")
    sub.add_argument("--repo", required=True)
    sub.add_argument("--theme", required=True)
    sub.add_argument("--run", required=True)
    sub.add_argument("--make-default", action="store_true", help="Explicitly replace the default on a later run")
    for command, description in (("models-apply", "Apply recorded model choices to seven local specialist agents with reversible backups"),
                                  ("models-restore", "Restore this run's original local agent routing while preserving later edits")):
        sub = subs.add_parser(command, help=description)
        sub.add_argument("--repo", required=True)
        sub.add_argument("--run", required=True)
    _design_backend().add_parsers(subs)
    return main


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.repo)
        elif args.command == "init-run":
            if args.profile is not None:
                print("NOTICE: --profile is deprecated and ignored; read requirements from the project.", file=sys.stderr)
            result = init_run(args.repo, args.mode, args.profile, args.theme_action, args.theme_id, args.models)
        elif args.command == "theme-new":
            result = theme_new(args.repo, args.id, args.name)
        elif args.command == "build-theme":
            result = build_theme(args.path)
        elif args.command in ("check-theme", "theme-digest"):
            result = check_theme(args.path)
            if args.command == "theme-digest":
                result = {key: result[key] for key in ("status", "themeId", "themeDigest")}
        elif args.command == "check-run":
            result = check_run(args.path)
        elif args.command == "context-digest":
            result = context_digest(args.path)
        elif args.command == "models-digest":
            result = models_digest(args.path)
        elif args.command == "decision-digest":
            result = {"status": "PASS", "inputs": args.files, "inputsDigest": file_digest(Path(args.path).resolve(), args.files)}
        elif args.command == "package":
            result = package_theme(args.path, args.output)
        elif args.command == "models-apply":
            result = models_apply(args.repo, args.run)
        elif args.command == "models-restore":
            result = models_restore(args.repo, args.run)
        elif args.command in _design_backend().COMMANDS:
            backend = _design_backend()
            result = backend.command(backend.studio, args)
        else:
            result = register_theme(args.repo, args.theme, args.run, args.make_default)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 2 if result["status"] == "BLOCKED" else 1
    except (StudioError, OSError, UnicodeError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
