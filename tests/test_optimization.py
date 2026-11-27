from __future__ import annotations

import base64
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("optimization", ROOT / ".omp/skills/ui-design-studio/scripts/optimization.py")
optimization = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(optimization)

class LocalStudio:
    def __init__(self) -> None:
        self.safe_calls = 0

    def safe_path(self, root: Path, relative: str, *, must_exist: bool = True, allow_dir: bool = False) -> Path:
        self.safe_calls += 1
        base = Path(root).resolve()
        candidate = base / relative
        resolved = candidate.resolve(strict=False)
        if base != resolved and base not in resolved.parents:
            raise ValueError("path escapes root")
        if must_exist and not candidate.exists():
            raise FileNotFoundError(candidate)
        if not allow_dir and candidate.exists() and candidate.is_dir():
            raise IsADirectoryError(candidate)
        return candidate

    def read_json(self, path: Path) -> object:
        return json.loads(path.read_text("utf-8"))

    def atomic_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def atomic_bytes(self, path: Path, value: bytes, mode: int = 0o600) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)


def _settings(**overrides: object) -> dict[str, object]:
    value = optimization.DEFAULT_SETTINGS()
    value["tools"] = dict(value["tools"])
    value.update(overrides)
    return value


def _capabilities(*available: str) -> dict[str, object]:
    tools = {
        name: {"available": name in available, "executable": name if name in available else None}
        for name in optimization.TOOL_NAMES
    }
    return {"tools": tools, "compression": {"gzip": True, "brotli": False}}



class OptimizationTests(unittest.TestCase):
    def test_settings_and_recommendations_are_bounded(self) -> None:
        settings = optimization.validate_settings({"preset": "maximum", "quality": 65, "level": 9, "minify": True, "compress": True, "tools": dict(optimization.DEFAULT_TOOLS), "recommendationMode": "aggressive"})
        self.assertEqual(settings["preset"], "maximum")
        self.assertTrue(any("Aggressive" in item for item in optimization.recommendations(settings)))
        with self.assertRaises(ValueError):
            optimization.validate_settings({"unknown": True})

    def test_real_before_after_transforms_and_compression(self) -> None:
        settings = optimization.DEFAULT_SETTINGS()
        sources = {
            "sample.html": b"<!-- remove -->\n<html> <body>  <h1>Real output</h1> </body> </html>\n",
            "sample.css": b"/* remove */\n.card { color: #3366ff; padding: 8px 8px; }\n",
            "sample.json": b'{\n  "items": [1, 2, 3],\n  "title": "Real output"\n}\n',
            "sample.svg": b'<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"><symbol id="x"><rect width="10" height="10"/></symbol></svg>',
            "sample.txt": b"one\n\n\n two\n",
        }
        for name, source in sources.items():
            with self.subTest(name=name):
                after, operations, measurements, artifacts = optimization.optimize_bytes(name, source, settings)
                self.assertTrue(after)
                self.assertNotEqual(after, source, name)
                self.assertEqual(measurements["inputSha256"], optimization._digest(source))
                self.assertTrue(operations)
                self.assertIn("gzip", artifacts)

        names = {item["sourceName"] for item in optimization._example_sources()}
        self.assertEqual(names, {"sample.png", "sample.jpeg", "sample.svg", "sample.html", "sample.css", "sample.js", "sample.json", "sample.txt", "sample.pdf"})


    def test_after_keeps_media_bytes_and_transport_variants(self) -> None:
        html = b"<!-- comment -->\n<html><body><h1>hello</h1></body></html>"
        with tempfile.TemporaryDirectory() as temporary:
            studio = LocalStudio()
            root = Path(temporary)
            payload = {
                "source": {"sourceName": "page.html", "data": base64.b64encode(html).decode("ascii")},
                "settings": _settings(),
            }
            result = optimization.run_optimization(studio, root, payload)
            record = result["results"][0]
            _, after, content_type = optimization.read_content(studio, root, record["id"], "after")
            self.assertEqual(content_type, "text/html")
            gzip_bytes = optimization.read_content(studio, root, record["id"], "gzip")[1]
            self.assertNotEqual(after, gzip_bytes)
            self.assertEqual(after, gzip.decompress(gzip_bytes))
            gzip_meta = record["variants"]["gzip"]
            self.assertEqual(gzip_meta["contentEncoding"], "gzip")
            if "brotli" in record["variants"]:
                import brotli  # type: ignore
                brotli_bytes = optimization.read_content(studio, root, record["id"], "brotli")[1]
                self.assertEqual(after, brotli.decompress(brotli_bytes))
                self.assertEqual(record["variants"]["brotli"]["headers"]["Content-Encoding"], "br")
            self.assertEqual(gzip_meta["headers"]["Content-Type"], "text/html")
            self.assertEqual(record["variants"]["after"]["sha256"], optimization._digest(after))
            for name, source, mime in (
                ("image.png", b"\x89PNG\r\n\x1a\nsource", "image/png"),
                ("document.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf"),
            ):
                transformed, _, _, artifacts = optimization.optimize_bytes(name, source, _settings(), _capabilities())
                self.assertEqual(transformed, source)
                self.assertEqual(artifacts, {})
                self.assertEqual(optimization._content_type(name), mime)

    def test_js_and_css_transforms_preserve_semantics(self) -> None:
        javascript = 'return\n{ok:true};\nconst url = /https?:\\/\\/example\\.test/; // remove\n'
        transformed_js = optimization.minify_js(javascript)
        self.assertIn("return\n{ok:true}", transformed_js)
        self.assertIn("/https?:\\/\\/example\\.test/", transformed_js)
        self.assertNotIn("// remove", transformed_js)
        css = '/* remove */ .card { width: calc(100% - 1rem); background: url("https://example.test/a b.png"); }'
        transformed_css = optimization.minify_css(css)
        self.assertIn("calc(100% - 1rem)", transformed_css)
        self.assertIn('url("https://example.test/a b.png")', transformed_css)
        self.assertNotIn("/* remove */", transformed_css)

    def test_svg_sanitizes_before_external_optimizer(self) -> None:
        source = (
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>'
            b'<path onclick="bad()" href="https://evil.test/x" style="fill:url(https://evil.test/f)"/></svg>'
        )
        captured: dict[str, bytes] = {}

        def run(command: list[str], **_: object) -> object:
            source_path = Path(command[command.index("--input") + 1])
            output_path = Path(command[command.index("--output") + 1])
            captured["source"] = source_path.read_bytes()
            output_path.write_bytes(captured["source"])
            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        with mock.patch.object(optimization.subprocess, "run", side_effect=run):
            after, _, _, _ = optimization.optimize_bytes(
                "unsafe.svg",
                source,
                _settings(),
                _capabilities("svgomg"),
            )
        self.assertNotIn(b"<script", captured["source"])
        self.assertNotIn(b"onclick", captured["source"])
        self.assertNotIn(b"evil.test", captured["source"])
        self.assertNotIn(b"onclick", after)

    def test_settings_controls_are_applied_or_recorded(self) -> None:
        source = b"<!-- comment -->\n<html><body>hello</body></html>"
        disabled = _settings(compress=False)
        disabled["tools"]["htmlMinify"] = False
        after, operations, _, artifacts = optimization.optimize_bytes("page.html", source, disabled, _capabilities())
        self.assertEqual(after, source)
        self.assertEqual(artifacts, {})
        self.assertTrue(any(item["status"] == "skipped" and item["tool"] == "htmlMinify" for item in operations))
        jpeg_commands: list[list[str]] = []

        def run_jpeg(command: list[str], **_: object) -> object:
            jpeg_commands.append(command)
            source_path = Path(command[-1])
            output_directory = Path(command[command.index("--dest") + 1])
            output_directory.joinpath(source_path.name).write_bytes(b"x")
            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        with mock.patch.object(optimization.subprocess, "run", side_effect=run_jpeg):
            optimization.optimize_bytes(
                "photo.jpeg",
                b"\xff\xd8" + b"x" * 100,
                _settings(quality=42, compress=False),
                _capabilities("jpegoptim"),
            )
        self.assertIn("--max=42", jpeg_commands[0])

    def test_retention_digest_and_quota_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            studio = LocalStudio()
            root = Path(temporary)
            settings = _settings(compress=False)
            capabilities = _capabilities()
            for index in range(129):
                optimization._write_result(
                    studio,
                    root,
                    {"sourceName": f"source-{index}.txt", "data": f"source-{index}".encode("ascii")},
                    settings,
                    capabilities,
                )
            records = optimization.result_records(studio, root)
            self.assertEqual(len(records), 128)
            self.assertNotIn("source-0.txt", {record["sourceName"] for record in records})
            self.assertIn("source-128.txt", {record["sourceName"] for record in records})
            latest = records[-1]
            after_path = studio.safe_path(root, latest["afterPath"])
            after_path.write_bytes(b"tampered")
            self.assertNotIn(latest["id"], {record["id"] for record in optimization.result_records(studio, root)})
            too_many = {"paths": [f"file-{index}.txt" for index in range(optimization.MAX_SOURCES + 1)]}
            before_calls = studio.safe_calls
            with self.assertRaises(ValueError):
                optimization.run_optimization(studio, root, too_many)
            self.assertEqual(studio.safe_calls, before_calls)

if __name__ == "__main__":
    unittest.main()
