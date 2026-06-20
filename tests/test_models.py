"""Unit tests for utils.models — TimeControl, ActiveColor, AppSettings."""

import unittest

from utils.models import ActiveColor, AppSettings, TimeControl
from utils.constants import MOVE_ANIMATION_OPTIONS, PROMOTION_DEFAULT_OPTIONS


class TestTimeControl(unittest.TestCase):
    def test_presets_are_tuples(self):
        for field_name in dir(TimeControl):
            if field_name.startswith("_"):
                continue
            val = getattr(TimeControl, field_name)
            if isinstance(val, tuple) and len(val) == 2:
                self.assertIsInstance(val[0], int)
                self.assertIsInstance(val[1], int)

    def test_all_presets_have_non_negative_values(self):
        for field_name in dir(TimeControl):
            if field_name.startswith("_"):
                continue
            val = getattr(TimeControl, field_name)
            if isinstance(val, tuple) and len(val) == 2:
                self.assertGreaterEqual(val[0], 0)
                self.assertGreaterEqual(val[1], 0)

    def test_three_plus_two_is_default(self):
        self.assertEqual(TimeControl.THREE_PLUS_TWO, (3, 2))

    def test_bullet_presets_under_3_minutes(self):
        for preset in [TimeControl.ONE_PLUS_ZERO, TimeControl.ONE_PLUS_ONE]:
            self.assertLess(preset[0], 3)


class TestActiveColor(unittest.TestCase):
    def test_white_is_true(self):
        self.assertTrue(ActiveColor.WHITE)

    def test_black_is_false(self):
        self.assertFalse(ActiveColor.BLACK)


class TestAppSettingsDefaults(unittest.TestCase):
    def setUp(self):
        self.settings = AppSettings()

    def test_show_legal_moves_default(self):
        self.assertTrue(self.settings.show_legal_moves)

    def test_show_tap_feedback_default(self):
        self.assertTrue(self.settings.show_tap_feedback)

    def test_auto_flip_board_default(self):
        self.assertTrue(self.settings.auto_flip_board)

    def test_show_coordinates_default(self):
        self.assertTrue(self.settings.show_coordinates)

    def test_move_animation_default(self):
        self.assertEqual(self.settings.move_animation, "normal")

    def test_promotion_default_value(self):
        self.assertEqual(self.settings.promotion_default, "queen")

    def test_critical_time_seconds_default(self):
        self.assertEqual(self.settings.critical_time_seconds, 10)

    def test_show_milliseconds_in_critical_default(self):
        self.assertTrue(self.settings.show_milliseconds_in_critical)

    def test_confirm_resign_default(self):
        self.assertTrue(self.settings.confirm_resign)

    def test_confirm_draw_default(self):
        self.assertTrue(self.settings.confirm_draw)

    def test_stockfish_binary_path_default(self):
        self.assertEqual(self.settings.stockfish_binary_path, "")

    def test_stockfish_difficulty_default(self):
        self.assertEqual(self.settings.stockfish_difficulty, "intermediate")


class TestAppSettingsFromDict(unittest.TestCase):
    def test_empty_dict_returns_defaults(self):
        settings = AppSettings.from_dict({})
        self.assertEqual(settings, AppSettings())

    def test_none_returns_defaults(self):
        settings = AppSettings.from_dict(None)
        self.assertEqual(settings, AppSettings())

    def test_partial_update(self):
        settings = AppSettings.from_dict({"show_legal_moves": False})
        self.assertFalse(settings.show_legal_moves)
        self.assertTrue(settings.show_coordinates)

    def test_unknown_key_ignored(self):
        settings = AppSettings.from_dict({"nonexistent": True})
        self.assertEqual(settings, AppSettings())

    def test_bad_animation_key_falls_back(self):
        settings = AppSettings.from_dict({"move_animation": "turbo"})
        self.assertEqual(settings.move_animation, "normal")

    def test_bad_promotion_key_falls_back(self):
        settings = AppSettings.from_dict({"promotion_default": "archbishop"})
        self.assertEqual(settings.promotion_default, "queen")

    def test_critical_time_clamped(self):
        settings = AppSettings.from_dict({"critical_time_seconds": 999})
        self.assertEqual(settings.critical_time_seconds, 10)

    def test_negative_critical_time_clamped(self):
        settings = AppSettings.from_dict({"critical_time_seconds": -5})
        self.assertEqual(settings.critical_time_seconds, 10)

    def test_valid_critical_time_accepted(self):
        settings = AppSettings.from_dict({"critical_time_seconds": 30})
        self.assertEqual(settings.critical_time_seconds, 30)

    def test_bool_field_rejects_non_bool(self):
        settings = AppSettings.from_dict({"show_legal_moves": "yes"})
        self.assertTrue(settings.show_legal_moves)


class TestAppSettingsToDict(unittest.TestCase):
    def test_roundtrip(self):
        original = AppSettings(show_legal_moves=False, move_animation="fast")
        d = original.to_dict()
        restored = AppSettings.from_dict(d)
        self.assertEqual(original, restored)

    def test_contains_all_fields(self):
        d = AppSettings().to_dict()
        expected_keys = {
            "show_legal_moves",
            "show_tap_feedback",
            "auto_flip_board",
            "show_coordinates",
            "move_animation",
            "confirm_moves",
            "promotion_default",
            "critical_time_seconds",
            "show_milliseconds_in_critical",
            "confirm_resign",
            "confirm_draw",
            "stockfish_binary_path",
            "stockfish_difficulty",
        }
        self.assertEqual(set(d.keys()), expected_keys)


class TestAppSettingsUpdated(unittest.TestCase):
    def test_updated_returns_new_instance(self):
        original = AppSettings()
        modified = original.updated(show_legal_moves=False)
        self.assertIsNot(original, modified)

    def test_updated_does_not_mutate_original(self):
        original = AppSettings(show_legal_moves=True)
        original.updated(show_legal_moves=False)
        self.assertTrue(original.show_legal_moves)

    def test_updated_validates_changes(self):
        modified = AppSettings().updated(critical_time_seconds=99)
        self.assertEqual(modified.critical_time_seconds, 10)


if __name__ == "__main__":
    unittest.main()
