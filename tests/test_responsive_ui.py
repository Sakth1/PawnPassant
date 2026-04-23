"""Responsive UI tests for shared layout math and resize application."""

import asyncio
import sys
import unittest
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chess import Move, parse_square

from ui.app import ChessApp
from ui.board import ChessBoard
from ui.captured_pieces import CaputredPieces
from ui.clockui import ClockUI
from ui.home_page import HomeView
from ui.layout import MAX_SQUARE_SIZE, MIN_SQUARE_SIZE, resolve_app_layout
from utils.events import GameEndedEvent
from utils.models import TimeControl
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
        self.overlay = []
        self.on_resize = None
        self.on_media_change = None
        self.controls = []
        self.route = "/home"
        self.navigation_bar = None

    def add(self, control):
        self.controls.append(control)

    def update(self):
        return None

    def show_dialog(self, dialog):
        dialog.open = True
        self.overlay.append(dialog)

    def pop_dialog(self):
        if not self.overlay:
            return None
        dialog = self.overlay.pop()
        dialog.open = False
        return dialog

    def run_task(self, fn, *args):
        return asyncio.run(fn(*args))

    async def push_route(self, route):
        self.route = route
        if self.on_route_change is not None:
            self.on_route_change(type("RouteEvent", (), {"route": route})())

    def go(self, route):
        self.route = route
        if self.on_route_change is not None:
            self.on_route_change(type("RouteEvent", (), {"route": route})())


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


class TestResponsivePieceDisplayUi(unittest.TestCase):
    def test_apply_layout_updates_sidebar_dimensions(self):
        piece_display = CaputredPieces()
        layout = resolve_app_layout(1400, 900)

        piece_display.apply_layout(layout)

        self.assertEqual(piece_display.width, layout.piece_panel_width)
        self.assertEqual(
            piece_display.black_squares[0].width,
            layout.board_square_size * 0.97,
        )
        self.assertEqual(
            piece_display.divider.width, max(80, int(layout.piece_panel_width * 0.72))
        )


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
        self.assertEqual(app.piece_display_slot.col, {"xs": 12, "md": 12})
        self.assertEqual(app.board_slot.col, {"xs": 12, "md": 12})
        self.assertEqual(app.clock_slot.col, {"xs": 12, "md": 12})

    def test_wide_viewport_uses_split_layout(self):
        page = _FakePage(width=1400, height=900)
        app = ChessApp(page, dev_mode=False)

        self.assertEqual(app.layout.breakpoint, "desktop")
        self.assertEqual(app.piece_display_slot.col, {"xs": 12, "md": 3})
        self.assertEqual(app.board_slot.col, {"xs": 12, "md": 7})
        self.assertEqual(app.clock_slot.col, {"xs": 12, "md": 2})

    def test_dev_dropdown_stays_within_available_width(self):
        page = _FakePage(width=420, height=780, padding=_FakePadding(left=20, right=20))
        app = ChessApp(page, dev_mode=True)

        available_width = (
            page.width - page.media.padding.left - page.media.padding.right
        )
        self.assertLessEqual(app.position_selector.width, available_width)

    def test_game_end_event_opens_result_modal(self):
        page = _FakePage(width=960, height=800)
        app = ChessApp(page, dev_mode=False)

        app._handle_game_ended(
            GameEndedEvent(
                winner="White",
                reason="checkmate",
                message="White wins by checkmate.",
            )
        )

        self.assertTrue(app.result_dialog.open)
        self.assertEqual(app.result_dialog_title.value, "White")
        self.assertEqual(app.result_dialog_message.value, "White wins by checkmate.")
        self.assertIn(app.result_dialog, page.overlay)

    def test_closing_result_modal_resets_board(self):
        page = _FakePage(width=960, height=800)
        app = ChessApp(page, dev_mode=True)
        app.board_view.load_position("k7/8/1K1R4/8/8/8/8/8 w - - 0 1")

        app._handle_result_dialog_close()

        self.assertFalse(app.result_dialog.open)
        self.assertEqual(page.overlay, [])
        self.assertEqual(app.position_selector.value, "Start Position")
        self.assertEqual(
            app.board_view.game.get_board_fen(), ChessBoard().game.get_board_fen()
        )

    def test_home_selection_updates_clock_and_routes_to_game(self):
        page = _FakePage(width=960, height=800)
        app = ChessApp(page, dev_mode=False)

        app._start_game_with_time_control((10, 5))

        self.assertEqual(app.time_control_view.time_control, (10, 5))
        self.assertEqual(app.view_container.content, app.game_page_view)
        self.assertEqual(page.route, "/game")


class TestHomeView(unittest.TestCase):
    def test_presets_are_generated_from_time_control_model(self):
        home_view = HomeView()

        expected_keys = {field.name for field in fields(TimeControl)}
        actual_keys = {str(preset["key"]) for preset in home_view.presets}

        self.assertEqual(actual_keys, expected_keys)

    def test_presets_include_tooltips_for_grid_tiles(self):
        home_view = HomeView()
        first_tile = home_view.grid.controls[0]

        self.assertIn("increment", first_tile.tooltip)

    def test_tile_click_updates_selected_preset(self):
        home_view = HomeView()
        selected_preset = next(
            preset for preset in home_view.presets if preset["value"] == (10, 5)
        )

        home_view._select_preset(str(selected_preset["key"]))

        self.assertEqual(home_view.selected_preset["value"], (10, 5))

    def test_primary_action_returns_selected_time_control(self):
        captured = []
        home_view = HomeView(on_time_control_selected=captured.append)
        selected_preset = next(
            preset for preset in home_view.presets if preset["value"] == (10, 5)
        )

        home_view._select_preset(str(selected_preset["key"]))
        home_view._handle_primary_action()

        self.assertEqual(captured, [(10, 5)])

    def test_custom_apply_updates_selected_time_control(self):
        home_view = HomeView()

        home_view.minutes_input.value = "7"
        home_view.increment_input.value = "3"
        home_view._handle_custom_apply()

        self.assertEqual(home_view.selected_time_control, (7, 3))
        self.assertEqual(home_view.selection_text.value, "Selected: Custom 7+3")

    def test_primary_action_uses_custom_time_control(self):
        captured = []
        home_view = HomeView(on_time_control_selected=captured.append)

        home_view.minutes_input.value = "12"
        home_view.increment_input.value = "5"
        home_view._handle_primary_action()

        self.assertEqual(captured, [(12, 5)])

    def test_custom_time_requires_positive_minutes(self):
        home_view = HomeView()

        home_view.minutes_input.value = "0"
        home_view.increment_input.value = "5"
        home_view._handle_custom_apply()

        self.assertEqual(home_view.minutes_input.error_text, "Enter minutes")

    def test_apply_layout_updates_homepage_responsiveness(self):
        home_view = HomeView()
        mobile_layout = resolve_app_layout(420, 780)

        home_view.apply_layout(mobile_layout)

        self.assertEqual(home_view.content.padding.left, mobile_layout.padding)
        self.assertEqual(home_view.grid.controls[0].col, {"xs": 4, "sm": 4, "md": 4})
