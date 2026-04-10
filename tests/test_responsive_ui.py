"""Responsive UI tests for shared layout math and resize application."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chess import Move, parse_square

from ui.app import ChessApp
from ui.board import ChessBoard
from ui.clockui import ClockUI
from ui.layout import MAX_SQUARE_SIZE, MIN_SQUARE_SIZE, resolve_app_layout
from utils.signals import bus


class _FakeWindow:
    def __init__(self):
        self.icon = None


class _FakePadding:
    def __init__(self, left=0, top=0, right=0, bottom=0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class _FakeMedia:
    def __init__(self, padding=None):
        self.padding = padding or _FakePadding()


class _FakePage:
    def __init__(self, width=960, height=800, padding=None):
        self.width = width
        self.height = height
        self.window = _FakeWindow()
        self.media = _FakeMedia(padding=padding)
        self.fonts = {}
        self.title = ""
        self.padding = 0
        self.spacing = 0
        self.scroll = None
        self.on_resize = None
        self.on_media_change = None
        self.controls = []

    def add(self, control):
        self.controls.append(control)


class TestResponsiveLayoutResolver(unittest.TestCase):
    def test_square_size_respects_defined_bounds(self):
        small_layout = resolve_app_layout(320, 480)
        large_layout = resolve_app_layout(4000, 2200)

        self.assertEqual(small_layout.board_square_size, MIN_SQUARE_SIZE)
        self.assertEqual(large_layout.board_square_size, MAX_SQUARE_SIZE)

    def test_mobile_layout_stacks_and_desktop_splits(self):
        mobile = resolve_app_layout(420, 780)
        desktop = resolve_app_layout(1440, 900)

        self.assertTrue(mobile.stacked)
        self.assertEqual(mobile.breakpoint, "mobile")
        self.assertFalse(desktop.stacked)
        self.assertEqual(desktop.breakpoint, "desktop")


class TestResponsiveBoardUi(unittest.TestCase):
    def test_apply_layout_resizes_board_and_squares(self):
        board = ChessBoard()
        layout = resolve_app_layout(420, 780)

        board.apply_layout(layout)

        self.assertEqual(board.square_size, layout.board_square_size)
        self.assertEqual(board.board_frame.width, layout.board_side)
        self.assertEqual(board.board_frame.height, layout.board_side)
        self.assertEqual(board.square_map["e2"].width, layout.board_square_size)
        self.assertEqual(board.move_animation_overlay.width, layout.board_square_size)

    def test_promotion_overlay_scales_after_resize(self):
        board = ChessBoard()
        board.load_position("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
        board._safe_page = lambda: object()
        layout = resolve_app_layout(420, 780)
        board.apply_layout(layout)

        board._show_promotion_dialog(Move(parse_square("b7"), parse_square("b8")))

        self.assertEqual(board.promotion_overlay.width, layout.board_square_size * 4)
        self.assertEqual(board.promotion_overlay.height, layout.board_square_size)
        self.assertEqual(board.promotion_overlay.left, layout.board_square_size)
        self.assertEqual(board.promotion_overlay.top, 0)

    def test_center_pixel_tracks_resized_board(self):
        board = ChessBoard()
        layout = resolve_app_layout(420, 780)

        board.apply_layout(layout)

        self.assertEqual(
            board._get_center_pixel_of_square("a8"),
            (layout.board_square_size / 2, layout.board_square_size * 1.5),
        )


class TestResponsiveClockUi(unittest.TestCase):
    def test_apply_layout_updates_timer_dimensions(self):
        clock_ui = ClockUI()
        layout = resolve_app_layout(420, 780)

        clock_ui.apply_layout(layout)

        self.assertEqual(clock_ui.width, layout.clock_width)
        self.assertEqual(clock_ui.black_timer_main.size, layout.timer_font_size)
        self.assertEqual(clock_ui.black_timer_ms.size, layout.timer_ms_size)
        self.assertEqual(clock_ui.divider.width, layout.divider_extent)


class TestResponsiveAppUi(unittest.TestCase):
    def setUp(self):
        self._original_emit = bus.emit
        bus.emit = lambda _event: None

    def tearDown(self):
        bus.emit = self._original_emit

    def test_narrow_viewport_uses_stacked_layout(self):
        page = _FakePage(width=420, height=780)
        app = ChessApp(page, dev_mode=False)

        self.assertEqual(app.layout.breakpoint, "mobile")
        self.assertEqual(app.board_slot.col, {"xs": 12, "md": 12})
        self.assertEqual(app.clock_slot.col, {"xs": 12, "md": 12})

    def test_wide_viewport_uses_split_layout(self):
        page = _FakePage(width=1400, height=900)
        app = ChessApp(page, dev_mode=False)

        self.assertEqual(app.layout.breakpoint, "desktop")
        self.assertEqual(app.board_slot.col, {"xs": 12, "md": 8})
        self.assertEqual(app.clock_slot.col, {"xs": 12, "md": 4})

    def test_dev_dropdown_stays_within_available_width(self):
        page = _FakePage(width=420, height=780, padding=_FakePadding(left=20, right=20))
        app = ChessApp(page, dev_mode=True)

        available_width = (
            page.width - page.media.padding.left - page.media.padding.right
        )
        self.assertLessEqual(app.position_selector.width, available_width)
