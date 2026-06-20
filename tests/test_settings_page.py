"""Unit tests for ui.settings_page — SettingsView construction, sections."""

import unittest

from ui.settings_page import SettingsView
from utils.settings import SettingsController


class TestSettingsViewConstruction(unittest.TestCase):
    def test_creates_with_default_controller(self):
        view = SettingsView()
        self.assertIsInstance(view.controller, SettingsController)

    def test_creates_with_sections(self):
        view = SettingsView()
        self.assertIsNotNone(view.board_section)
        self.assertIsNotNone(view.gameplay_section)
        self.assertIsNotNone(view.clock_section)

    def test_has_reset_button(self):
        view = SettingsView()
        self.assertIsNotNone(view.reset_button)

    def test_has_status_text(self):
        view = SettingsView()
        self.assertIsNotNone(view.status_text)

    def test_syncs_settings_from_controller(self):
        controller = SettingsController()
        view = SettingsView(controller)
        self.assertIs(view.settings, controller.settings)


class TestSettingsViewSections(unittest.TestCase):
    def test_board_section_has_controls(self):
        view = SettingsView()
        view._rebuild_sections()
        self.assertGreater(len(view.board_section.controls), 0)

    def test_gameplay_section_has_controls(self):
        view = SettingsView()
        view._rebuild_sections()
        self.assertGreater(len(view.gameplay_section.controls), 0)

    def test_clock_section_has_controls(self):
        view = SettingsView()
        view._rebuild_sections()
        self.assertGreater(len(view.clock_section.controls), 0)

    def test_status_text_after_rebuild(self):
        view = SettingsView()
        view._rebuild_sections()
        self.assertEqual(view.status_text.value, "Preferences saved locally")


if __name__ == "__main__":
    unittest.main()
