"""Unit tests for ui.home_page — HomeView construction, presets, categorization."""

import unittest

from ui.home_page import HomeView
from utils.models import TimeControl


class TestHomeViewConstruction(unittest.TestCase):
    def test_creates_without_callback(self):
        view = HomeView()
        self.assertIsNone(view.on_time_control_selected)

    def test_default_selected_preset_key_three_plus_two(self):
        view = HomeView()
        self.assertEqual(view.selected_preset["value"], TimeControl.THREE_PLUS_TWO)

    def test_default_custom_time_control_none(self):
        view = HomeView()
        self.assertIsNone(view.selected_custom_time_control)

    def test_selected_time_control_defaults_to_preset(self):
        view = HomeView()
        self.assertEqual(view.selected_time_control, TimeControl.THREE_PLUS_TWO)

    def test_creates_presets(self):
        view = HomeView()
        self.assertGreater(len(view.presets), 0)


class TestHomeViewCategorization(unittest.TestCase):
    def test_bullet_2_min_or_less(self):
        self.assertEqual(HomeView._categorize_time_control(1), "bullet")
        self.assertEqual(HomeView._categorize_time_control(2), "bullet")

    def test_blitz_3_to_5_min(self):
        self.assertEqual(HomeView._categorize_time_control(3), "blitz")
        self.assertEqual(HomeView._categorize_time_control(5), "blitz")

    def test_rapid_6_to_20_min(self):
        self.assertEqual(HomeView._categorize_time_control(10), "rapid")
        self.assertEqual(HomeView._categorize_time_control(20), "rapid")

    def test_classical_over_20_min(self):
        self.assertEqual(HomeView._categorize_time_control(25), "classical")
        self.assertEqual(HomeView._categorize_time_control(60), "classical")


class TestHomeViewPresetSelection(unittest.TestCase):
    def test_select_preset_clears_custom(self):
        view = HomeView()
        view.selected_custom_time_control = (5, 3)
        view._select_preset(view.presets[0]["key"])
        self.assertIsNone(view.selected_custom_time_control)

    def test_select_preset_updates_selected_key(self):
        view = HomeView()
        first_key = view.presets[0]["key"]
        view._select_preset(first_key)
        self.assertEqual(view.selected_preset_key, first_key)


class TestHomeViewCustomTimeControl(unittest.TestCase):
    def test_parse_custom_empty_returns_none(self):
        view = HomeView()
        view.minutes_input.value = ""
        view.increment_input.value = ""
        result = view._parse_custom_time_control()
        self.assertIsNone(result)

    def test_parse_custom_zero_minutes_shows_error(self):
        view = HomeView()
        view.minutes_input.value = "0"
        view.increment_input.value = "0"
        result = view._parse_custom_time_control()
        self.assertIsNone(result)
        self.assertEqual(view.minutes_input.error_text, "Enter minutes")

    def test_parse_custom_valid(self):
        view = HomeView()
        view.minutes_input.value = "10"
        view.increment_input.value = "5"
        result = view._parse_custom_time_control()
        self.assertEqual(result, (10, 5))

    def test_custom_apply_stores_value(self):
        view = HomeView()
        view.minutes_input.value = "15"
        view.increment_input.value = "10"
        view._handle_custom_apply()
        self.assertEqual(view.selected_custom_time_control, (15, 10))

    def test_selection_label_custom(self):
        view = HomeView()
        view.selected_custom_time_control = (7, 3)
        label = view._selection_label()
        self.assertIn("Custom", label)
        self.assertIn("7", label)


class TestHomeViewSelectionLabel(unittest.TestCase):
    def test_selection_label_preset(self):
        view = HomeView()
        label = view._selection_label()
        self.assertIn("Selected:", label)


if __name__ == "__main__":
    unittest.main()
