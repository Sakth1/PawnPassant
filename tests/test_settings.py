"""Unit tests for utils.settings — backends, controller, migration."""

import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

from utils.settings import (
    JsonFileSettingsBackend,
    SharedPreferencesSettingsBackend,
    SettingsController,
)
from utils.models import AppSettings


class TestSharedPreferencesSettingsBackend(unittest.TestCase):
    def test_decode_payload_dict(self):
        result = SharedPreferencesSettingsBackend._decode_payload(
            {"show_legal_moves": False}
        )
        self.assertEqual(result, {"show_legal_moves": False})

    def test_decode_payload_json_string(self):
        result = SharedPreferencesSettingsBackend._decode_payload(
            '{"show_legal_moves": true}'
        )
        self.assertEqual(result, {"show_legal_moves": True})

    def test_decode_payload_invalid_json_returns_none(self):
        result = SharedPreferencesSettingsBackend._decode_payload("not json")
        self.assertIsNone(result)

    def test_decode_payload_none_returns_none(self):
        result = SharedPreferencesSettingsBackend._decode_payload(None)
        self.assertIsNone(result)

    def test_decode_payload_empty_string_returns_none(self):
        result = SharedPreferencesSettingsBackend._decode_payload("")
        self.assertIsNone(result)


class TestJsonFileSettingsBackend(unittest.TestCase):
    def test_load_nonexistent_file_returns_none(self):
        backend = JsonFileSettingsBackend(Path("/nonexistent/settings.json"))
        result = asyncio.run(backend.load())
        self.assertIsNone(result)

    def test_save_and_load_roundtrip(self):
        async def _run():
            with TemporaryDirectory() as tmp:
                path = Path(tmp) / "settings.json"
                backend = JsonFileSettingsBackend(path)
                data = {"show_legal_moves": False, "move_animation": "fast"}
                await backend.save(data)
                loaded = await backend.load()
                self.assertEqual(loaded, data)
        asyncio.run(_run())

    def test_load_invalid_json_returns_none(self):
        async def _run():
            with TemporaryDirectory() as tmp:
                path = Path(tmp) / "bad.json"
                path.write_text("not json", encoding="utf-8")
                backend = JsonFileSettingsBackend(path)
                result = await backend.load()
                self.assertIsNone(result)
        asyncio.run(_run())


class TestSettingsController(unittest.TestCase):
    def test_default_settings(self):
        ctrl = SettingsController()
        self.assertIsInstance(ctrl.settings, AppSettings)

    def test_update_returns_new_settings(self):
        ctrl = SettingsController()
        new_settings = ctrl.update(show_legal_moves=False)
        self.assertFalse(new_settings.show_legal_moves)

    def test_update_does_not_mutate_original(self):
        ctrl = SettingsController()
        original = ctrl.settings
        ctrl.update(show_legal_moves=False)
        self.assertTrue(original.show_legal_moves)

    def test_reset_defaults_restores(self):
        ctrl = SettingsController()
        ctrl.update(show_legal_moves=False)
        ctrl.reset_defaults()
        self.assertTrue(ctrl.settings.show_legal_moves)

    def test_reset_defaults_notifies(self):
        from utils.signals import bus
        from utils.events import SettingsChangedEvent
        ctrl = SettingsController()
        received = []
        bus.connect(SettingsChangedEvent, lambda e: received.append(e))
        ctrl.reset_defaults()
        self.assertEqual(len(received), 1)

    def test_no_page_does_not_schedule_save(self):
        ctrl = SettingsController()
        # Should not raise — _schedule_save checks for page
        ctrl.update(show_legal_moves=False)


class TestSettingsControllerBackendSelection(unittest.TestCase):
    def test_no_page_returns_none_backend(self):
        ctrl = SettingsController()
        result = asyncio.run(ctrl._get_backend())
        self.assertIsNone(result)

    def test_platform_name_empty_without_page(self):
        ctrl = SettingsController()
        self.assertEqual(ctrl._platform_name(), "")


if __name__ == "__main__":
    unittest.main()
