"""Unit tests for ui.clockui — ClockUI construction, time control, layout, helpers."""

import unittest

from ui.clockui import ClockUI, time_control_to_string
from utils.constants import TIMER_BG


class TestTimeControlToString(unittest.TestCase):
    def test_three_plus_two(self):
        self.assertEqual(time_control_to_string((3, 2)), "03:00")

    def test_one_plus_zero(self):
        self.assertEqual(time_control_to_string((1, 0)), "01:00")

    def test_ten_plus_zero(self):
        self.assertEqual(time_control_to_string((10, 0)), "10:00")


class TestClockUIConstruction(unittest.TestCase):
    def test_creates_with_default_time_control(self):
        cui = ClockUI()
        self.assertEqual(cui.time_control, (3, 2))
        self.assertEqual(cui.black_timer_main.value, "03:00")
        self.assertEqual(cui.white_timer_main.value, "03:00")

    def test_creates_with_custom_time_control(self):
        cui = ClockUI(time_control=(10, 5))
        self.assertEqual(cui.time_control, (10, 5))

    def test_bgcolor_is_timer_bg(self):
        cui = ClockUI()
        self.assertEqual(cui.bgcolor, TIMER_BG)


class TestClockUISetTimeControl(unittest.TestCase):
    def test_set_time_control_updates_display(self):
        cui = ClockUI()
        cui.set_time_control((1, 0))
        self.assertEqual(cui.black_timer_main.value, "01:00")
        self.assertEqual(cui.white_timer_main.value, "01:00")

    def test_set_time_control_resets_game_over(self):
        cui = ClockUI()
        from utils.game_state import game_state
        game_state.game_over = True
        cui.set_time_control((5, 3))
        self.assertFalse(game_state.game_over)

    def test_set_time_control_restores_timer_order(self):
        cui = ClockUI()
        cui.content.controls.reverse()
        self.assertEqual(cui.content.controls[0], cui.white_timer)
        cui.set_time_control((3, 2))
        self.assertEqual(cui.content.controls[0], cui.black_timer)


class TestClockUIActionButtons(unittest.TestCase):
    def test_draw_button_has_tooltip(self):
        cui = ClockUI()
        self.assertEqual(cui.draw_button.tooltip, "Offer draw")

    def test_resign_button_has_tooltip(self):
        cui = ClockUI()
        self.assertEqual(cui.resign_button.tooltip, "Resign")


if __name__ == "__main__":
    unittest.main()
