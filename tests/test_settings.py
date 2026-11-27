from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ui_design_studio.settings import GlobalSettings, SettingsError, config_path, load_settings, save_settings


class GlobalSettingsTests(unittest.TestCase):
    def test_absent_settings_enable_automatic_lan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_settings(home=directory), GlobalSettings(True, None))
            self.assertEqual(config_path(home=directory), Path(directory) / ".config/ui-design-studio/config.json")

    def test_save_and_reload_explicit_interface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = GlobalSettings(False, None)
            save_settings(settings, home=directory)
            self.assertEqual(load_settings(home=directory), settings)
            saved = json.loads(config_path(home=directory).read_text())
            self.assertEqual(saved, {"schemaVersion": 1, "lanEnabled": False, "lanAddress": None})

            settings = GlobalSettings(True, "192.168.1.20")
            save_settings(settings, home=directory)
            self.assertEqual(load_settings(home=directory), settings)

    def test_invalid_settings_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = config_path(home=directory)
            path.parent.mkdir(parents=True)
            path.write_text('{"schemaVersion": 1, "lanEnabled": true, "lanAddress": "not-an-ip"}\n')
            with self.assertRaises(SettingsError):
                load_settings(home=directory)


if __name__ == "__main__":
    unittest.main()
