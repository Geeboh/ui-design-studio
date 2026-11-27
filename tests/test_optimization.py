from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("optimization", ROOT / ".omp/skills/ui-design-studio/scripts/optimization.py")
optimization = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(optimization)


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

    def test_examples_cover_resource_types(self) -> None:
        names = {item["sourceName"] for item in optimization._example_sources()}
        self.assertEqual(names, {"sample.png", "sample.svg", "sample.html", "sample.css", "sample.js", "sample.json", "sample.txt", "sample.pdf"})


if __name__ == "__main__":
    unittest.main()
