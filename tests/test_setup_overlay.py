"""Tests for ui.setup_overlay — SetupOverlay creation and panel transitions."""

import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from ui.setup_overlay import SetupOverlay


class TestSetupOverlay(unittest.TestCase):
    def setUp(self):
        self.page = MagicMock(spec=ft.Page)
        self.page.width = 800
        self.page.height = 600
        self.page.overlay = []
        self.file_picker = MagicMock(spec=ft.FilePicker)

    def test_creates_computer_mode_with_install_panel(self):
        overlay = SetupOverlay(
            page=self.page,
            file_picker=self.file_picker,
            mode="computer",
            binary_available=False,
        )
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay._mode, "computer")
        self.assertIsNotNone(overlay._stockfish_install_panel)

    def test_creates_computer_mode_with_config_panel(self):
        overlay = SetupOverlay(
            page=self.page,
            file_picker=self.file_picker,
            mode="computer",
            binary_available=True,
        )
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(overlay._stockfish_config_panel)

    def test_creates_online_mode(self):
        overlay = SetupOverlay(
            page=self.page,
            file_picker=self.file_picker,
            mode="online",
        )
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay._mode, "online")
        self.assertIsNotNone(overlay._online_panel)

    def test_open_closes_appends_and_removes_from_overlay(self):
        overlay = SetupOverlay(page=self.page, file_picker=self.file_picker, mode="online")
        overlay.open()
        self.assertIn(overlay, self.page.overlay)
        overlay.close()
        self.assertNotIn(overlay, self.page.overlay)

    def test_close_triggers_on_close_callback(self):
        callback = MagicMock()
        overlay = SetupOverlay(page=self.page, file_picker=self.file_picker, mode="online", on_close=callback)
        overlay.close()
        callback.assert_called_once()

    def test_panel_transition_install_to_config(self):
        overlay = SetupOverlay(
            page=self.page,
            file_picker=self.file_picker,
            mode="computer",
            binary_available=False,
        )
        self.assertIsNotNone(overlay._stockfish_install_panel)
        overlay.show_config_panel()
        self.assertIsNotNone(overlay._stockfish_config_panel)

    def test_panel_transition_config_to_install(self):
        overlay = SetupOverlay(
            page=self.page,
            file_picker=self.file_picker,
            mode="computer",
            binary_available=True,
        )
        self.assertIsNotNone(overlay._stockfish_config_panel)
        overlay.show_install_panel()
        self.assertIsNotNone(overlay._stockfish_install_panel)

    def test_file_picker_stored(self):
        overlay = SetupOverlay(page=self.page, file_picker=self.file_picker, mode="computer")
        self.assertIs(overlay._file_picker, self.file_picker)


if __name__ == "__main__":
    unittest.main()
