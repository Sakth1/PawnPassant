"""Unit tests for ui.layout — AppLayout, resolve_app_layout, breakpoints."""

import unittest

from ui.layout import (
    AppLayout,
    MOBILE_BREAKPOINT,
    TABLET_BREAKPOINT,
    resolve_app_layout,
)


class TestResolveAppLayout(unittest.TestCase):
    def test_mobile_breakpoint(self):
        layout = resolve_app_layout(MOBILE_BREAKPOINT - 1, 600)
        self.assertEqual(layout.breakpoint, "mobile")
        self.assertTrue(layout.stacked)
        self.assertTrue(layout.compact)

    def test_tablet_breakpoint(self):
        layout = resolve_app_layout(MOBILE_BREAKPOINT + 50, 700)
        self.assertEqual(layout.breakpoint, "tablet")
        self.assertFalse(layout.stacked)
        self.assertFalse(layout.compact)

    def test_desktop_breakpoint(self):
        layout = resolve_app_layout(TABLET_BREAKPOINT + 100, 900)
        self.assertEqual(layout.breakpoint, "desktop")
        self.assertFalse(layout.stacked)
        self.assertFalse(layout.compact)

    def test_minimum_width_floor(self):
        layout = resolve_app_layout(0, 600)
        self.assertGreaterEqual(layout.width, 300)

    def test_minimum_height_floor(self):
        layout = resolve_app_layout(800, 0)
        self.assertGreaterEqual(layout.height, 400)

    def test_board_square_size_within_bounds(self):
        layout = resolve_app_layout(800, 600)
        self.assertGreaterEqual(layout.board_square_size, 30)
        self.assertLessEqual(layout.board_square_size, 80)

    def test_board_side_is_multiple_of_8(self):
        layout = resolve_app_layout(800, 600)
        self.assertEqual(layout.board_side % 8, 0)
        self.assertEqual(layout.board_side, layout.board_square_size * 8)

    def test_timer_font_size_scales_with_board(self):
        layout = resolve_app_layout(800, 600)
        self.assertGreaterEqual(layout.timer_font_size, 24)

    def test_mobile_columns_all_12(self):
        layout = resolve_app_layout(360, 640)
        self.assertEqual(layout.piece_col, 12)
        self.assertEqual(layout.board_col, 12)
        self.assertEqual(layout.clock_col, 12)

    def test_desktop_columns_split(self):
        layout = resolve_app_layout(1400, 900)
        self.assertEqual(layout.piece_col, 3)
        self.assertEqual(layout.board_col, 7)
        self.assertEqual(layout.clock_col, 2)

    def test_spacing_scale_computed(self):
        layout = resolve_app_layout(800, 600)
        self.assertAlmostEqual(
            layout.spacing_scale,
            layout.board_square_size / 60,
        )


class TestAppLayoutDataclass(unittest.TestCase):
    def test_is_frozen(self):
        layout = resolve_app_layout(800, 600)
        with self.assertRaises(Exception):
            layout.width = 999


if __name__ == "__main__":
    unittest.main()
