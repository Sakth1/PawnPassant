"""Unit tests for utils.dialogs — safe_update, safe_pop_dialog, show_alert_dialog."""

import unittest
from unittest.mock import Mock

from utils.dialogs import safe_pop_dialog, safe_update


class TestSafeUpdate(unittest.TestCase):
    def test_safe_update_calls_update(self):
        page = Mock()
        safe_update(page)
        page.update.assert_called_once()

    def test_safe_update_swallows_exception(self):
        page = Mock()
        page.update.side_effect = RuntimeError("update failed")
        safe_update(page)

    def test_safe_update_with_unbound_control(self):
        safe_update(Mock())


class TestSafePopDialog(unittest.TestCase):
    def test_safe_pop_dialog_calls_pop_dialog(self):
        page = Mock()
        page.overlay = [object()]
        safe_pop_dialog(page)
        page.pop_dialog.assert_called_once()

    def test_safe_pop_dialog_swallows_exception(self):
        page = Mock()
        page.pop_dialog.side_effect = IndexError("empty overlay")
        safe_pop_dialog(page)

    def test_safe_pop_dialog_with_empty_overlay(self):
        page = Mock()
        page.overlay = []
        safe_pop_dialog(page)


class TestShowAlertDialog(unittest.TestCase):
    def test_show_alert_calls_page_show_dialog(self):
        from utils.dialogs import show_alert_dialog

        page = Mock()
        page.overlay = []

        show_alert_dialog(page, "Test Title", "Test Message")

        page.show_dialog.assert_called_once()

    def test_show_alert_dialog_passes_title_and_message(self):
        from utils.dialogs import show_alert_dialog

        page = Mock()
        page.overlay = []

        show_alert_dialog(page, "Title", "Msg")

        args = page.show_dialog.call_args
        dialog = args[0][0]
        self.assertEqual(dialog.title.value, "Title")
        self.assertEqual(dialog.content.value, "Msg")


if __name__ == "__main__":
    unittest.main()
