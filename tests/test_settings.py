"""Tests for persistent settings and settings-driven UI behavior."""

import asyncio
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

from chess import KNIGHT, parse_square

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.app import ChessApp
from ui.board import ChessBoard
from ui.clockui import ClockUI
from ui.settings_page import SettingsView
from utils.events import ClockTickEvent, GameEndedEvent
from utils.models import ActiveColor, AppSettings
from utils.settings import SettingsController
from utils.signals import bus


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp_settings"


class _SharedPreferences:
    def __init__(self, payload=None):
        self.payload = payload
        self.saved = None

    async def get(self, _key):
        return self.payload

    async def set(self, _key, value):
        self.saved = value


class _FakePage:
    def __init__(self, payload=None, platform=None, support_dir=None):
        self.shared_preferences = _SharedPreferences(payload)
        self.platform = platform
        self.storage_paths = None
        if support_dir is not None:
            self.storage_paths = type(
                "StoragePathsStub",
                (),
                {
                    "get_application_support_directory": (
                        lambda _self: support_dir
                    )
                },
            )()
        self.overlay = []

    def run_task(self, fn, *args):
        return asyncio.run(fn(*args))

    def show_dialog(self, dialog):
        dialog.open = True
        self.overlay.append(dialog)

    def pop_dialog(self):
        if self.overlay:
            dialog = self.overlay.pop()
            dialog.open = False

    def update(self):
        return None


def _make_workspace_tempdir() -> str:
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    temp_dir = TEST_TMP_ROOT / f"settings-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return str(temp_dir)


class TestSettingsModel(unittest.TestCase):
    def test_defaults_match_expected_app_preferences(self):
        settings = AppSettings()

        self.assertTrue(settings.show_legal_moves)
        self.assertTrue(settings.show_coordinates)
        self.assertEqual(settings.move_animation, "normal")
        self.assertEqual(settings.promotion_default, "queen")
        self.assertTrue(settings.confirm_resign)

    def test_from_dict_uses_valid_partial_values_and_ignores_bad_values(self):
        settings = AppSettings.from_dict(
            {
                "show_legal_moves": False,
                "move_animation": "wild",
                "promotion_default": "knight",
                "critical_time_seconds": 80,
            }
        )

        self.assertFalse(settings.show_legal_moves)
        self.assertEqual(settings.move_animation, "normal")
        self.assertEqual(settings.promotion_default, "knight")
        self.assertEqual(settings.critical_time_seconds, 10)

    def test_controller_load_save_and_reset(self):
        page = _FakePage(
            {"show_coordinates": False, "move_animation": "fast"},
            platform="android",
        )
        controller = SettingsController(page)

        loaded = asyncio.run(controller.load())
        self.assertFalse(loaded.show_coordinates)
        self.assertEqual(loaded.move_animation, "fast")

        controller.update(show_coordinates=True)
        saved_payload = json.loads(page.shared_preferences.saved)
        self.assertTrue(saved_payload["show_coordinates"])

        controller.reset_defaults()
        self.assertEqual(
            json.loads(page.shared_preferences.saved),
            AppSettings().to_dict(),
        )

    def test_windows_uses_local_json_file_storage(self):
        temp_dir = _make_workspace_tempdir()
        try:
            page = _FakePage(
                platform="windows",
                support_dir=temp_dir,
            )
            controller = SettingsController(page)

            controller.update(show_coordinates=False, move_animation="fast")
            settings_file = (
                Path(temp_dir) / "pawnpassant" / SettingsController.FILE_NAME
            )
            saved_payload = json.loads(settings_file.read_text(encoding="utf-8"))
            self.assertFalse(saved_payload["show_coordinates"])
            self.assertEqual(saved_payload["move_animation"], "fast")

            reloaded_controller = SettingsController(page)
            loaded = asyncio.run(reloaded_controller.load())
            self.assertFalse(loaded.show_coordinates)
            self.assertEqual(loaded.move_animation, "fast")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_windows_migrates_legacy_shared_preferences_to_file(self):
        temp_dir = _make_workspace_tempdir()
        try:
            page = _FakePage(
                {"confirm_moves": True, "show_coordinates": False},
                platform="windows",
                support_dir=temp_dir,
            )
            controller = SettingsController(page)

            loaded = asyncio.run(controller.load())
            settings_file = (
                Path(temp_dir) / "pawnpassant" / SettingsController.FILE_NAME
            )

            self.assertTrue(loaded.confirm_moves)
            self.assertFalse(loaded.show_coordinates)
            self.assertTrue(settings_file.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_android_prefers_shared_preferences_storage(self):
        temp_dir = _make_workspace_tempdir()
        try:
            page = _FakePage(
                platform="android",
                support_dir=temp_dir,
            )
            controller = SettingsController(page)

            controller.update(show_coordinates=False)

            self.assertIsNotNone(page.shared_preferences.saved)
            settings_file = (
                Path(temp_dir) / "pawnpassant" / SettingsController.FILE_NAME
            )
            self.assertFalse(settings_file.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSettingsView(unittest.TestCase):
    def test_settings_page_builds_grouped_controls_and_updates_controller(self):
        controller = SettingsController()
        settings_view = SettingsView(controller)

        self.assertGreaterEqual(len(settings_view.board_section.controls), 5)
        self.assertGreaterEqual(len(settings_view.gameplay_section.controls), 3)
        self.assertGreaterEqual(len(settings_view.clock_section.controls), 5)

        settings_view._update_setting("show_legal_moves", False)

        self.assertFalse(controller.settings.show_legal_moves)
        self.assertFalse(settings_view.settings.show_legal_moves)


class TestSettingsDrivenBoard(unittest.TestCase):
    def test_legal_moves_disabled_suppresses_hints_but_move_still_works(self):
        board = ChessBoard()
        board.apply_settings(
            AppSettings(show_legal_moves=False, move_animation="off")
        )

        board._handle_square_click(board.square_map["e2"], "e2")

        self.assertEqual(board.highlighted_squares, set())
        self.assertEqual(board.selected_square, "e2")

        board._handle_square_click(board.square_map["e4"], "e4")

        self.assertIsNone(board.game.piece_at_square(parse_square("e2")))
        self.assertIsNotNone(board.game.piece_at_square(parse_square("e4")))

    def test_auto_flip_disabled_keeps_white_on_bottom(self):
        board = ChessBoard()
        board.apply_settings(AppSettings(auto_flip_board=False))

        board.move_piece("e2", "e4")

        self.assertFalse(board.is_flipped)

    def test_coordinates_render_and_follow_resize_settings(self):
        board = ChessBoard()
        board.apply_settings(AppSettings(show_coordinates=True))

        self.assertTrue(board.square_map["a1"].show_coordinates)
        self.assertTrue(board.square_map["a1"].stack.controls)

        board.apply_settings(AppSettings(show_coordinates=False))

        self.assertFalse(board.square_map["a1"].show_coordinates)

    def test_promotion_default_bypasses_picker(self):
        board = ChessBoard()
        board.apply_settings(AppSettings(promotion_default="knight"))
        board.load_position("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")

        board.move_piece("b7", "b8")

        promoted_piece = board.game.piece_at_square(parse_square("b8"))
        self.assertIsNotNone(promoted_piece)
        self.assertEqual(promoted_piece.piece_type, KNIGHT)
        self.assertFalse(board.promotion_overlay.visible)


class TestSettingsDrivenClockAndActions(unittest.TestCase):
    def setUp(self):
        self._original_listeners = {
            event_type: listeners.copy()
            for event_type, listeners in bus._listeners.items()
        }
        bus._listeners = {}
        self.ended_events = []
        bus.connect(GameEndedEvent, self.ended_events.append)

    def tearDown(self):
        bus._listeners = {
            event_type: listeners.copy()
            for event_type, listeners in self._original_listeners.items()
        }

    def test_clock_settings_update_threshold_and_hide_milliseconds(self):
        clock_ui = ClockUI()
        clock_ui.apply_settings(
            AppSettings(
                critical_time_seconds=3,
                show_milliseconds_in_critical=False,
            )
        )

        self.assertEqual(clock_ui.clock.critical_threshold_seconds, 3)
        clock_ui.update = lambda: None

        clock_ui._update_ui(
            ClockTickEvent(
                color=ActiveColor.WHITE,
                minutes=0,
                seconds=2,
                milliseconds=870,
                is_critical=True,
            )
        )

        self.assertEqual(clock_ui.white_timer_main.value, "00:02")
        self.assertEqual(clock_ui.white_timer_ms.value, "")

    def test_resign_confirmation_gates_terminal_event(self):
        app = ChessApp.__new__(ChessApp)
        app.board_view = ChessBoard()
        app.settings_controller = SettingsController(
            settings=AppSettings(confirm_resign=True)
        )
        app.page = _FakePage()
        app.pending_terminal_action = None
        app.confirm_action_title = type("Text", (), {"value": ""})()
        app.confirm_action_message = type("Text", (), {"value": ""})()
        app.confirm_action_dialog = type("Dialog", (), {"open": False})()

        app._handle_resign_action()

        self.assertEqual(self.ended_events, [])
        self.assertEqual(app.pending_terminal_action, "resign")

        app._handle_action_confirm()

        self.assertEqual(len(self.ended_events), 1)
        self.assertEqual(self.ended_events[0].reason, "resignation")


if __name__ == "__main__":
    unittest.main()
