"""Unit tests for app — ChessApp construction, draw/resign, dialogs."""

import unittest
from unittest.mock import MagicMock, patch

import chess

from app import ChessApp
from utils.game_state import game_state


class FakePage:
    def __init__(self):
        self.width = 800
        self.height = 600
        self.fonts = {}
        self.title = ""
        self.padding = 0
        self.spacing = 0
        self.scroll = None
        self.window = MagicMock()
        self.navigation_bar = None
        self.on_route_change = None
        self.on_resize = None
        self.on_media_change = None
        self.run_task = MagicMock()
        self.navigate = MagicMock()
        self.push_route = MagicMock()
        self.add = MagicMock()
        self.show_dialog = MagicMock()
        self.pop_dialog = MagicMock()
        self.shared_preferences = None
        self.platform = None
        self.media = None

    def __setattr__(self, name, value):
        super().__setattr__(name, value)


class TestChessAppConstruction(unittest.TestCase):
    def test_creates_with_page(self):
        page = FakePage()
        app = ChessApp(page)
        self.assertIs(app.page, page)

    def test_creates_with_dev_mode_false(self):
        page = FakePage()
        app = ChessApp(page, dev_mode=False)
        self.assertFalse(app.dev_mode)
        self.assertIsNone(app.position_selector)

    def test_creates_with_dev_mode_true(self):
        page = FakePage()
        app = ChessApp(page, dev_mode=True)
        self.assertTrue(app.dev_mode)
        self.assertIsNotNone(app.position_selector)

    def test_has_route_manager(self):
        page = FakePage()
        app = ChessApp(page)
        self.assertIsNotNone(app._route_manager)

    def test_has_settings_controller(self):
        page = FakePage()
        app = ChessApp(page)
        self.assertIsNotNone(app.settings_controller)

    def test_has_board_view(self):
        page = FakePage()
        app = ChessApp(page)
        self.assertIsNotNone(app.board_view)

    def test_has_time_control_ui(self):
        page = FakePage()
        app = ChessApp(page)
        self.assertIsNotNone(app.time_control_UI)


class TestChessAppDrawResign(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.app = ChessApp(self.page)

    def test_draw_action_when_game_over_ignored(self):
        game_state.game_over = True
        self.app._handle_draw_action()
        self.page.show_dialog.assert_not_called()

    def test_resign_action_when_game_over_ignored(self):
        game_state.game_over = True
        self.app._handle_resign_action()
        self.page.show_dialog.assert_not_called()

    def test_draw_emits_agreement_without_confirmation(self):
        game_state.game_over = False
        from utils.models import AppSettings
        self.app.settings_controller.settings = AppSettings(confirm_draw=False)
        with patch.object(self.app, "_emit_draw_agreement") as mock:
            self.app._handle_draw_action()
            mock.assert_called_once()

    def test_resign_emits_without_confirmation(self):
        game_state.game_over = False
        from utils.models import AppSettings
        self.app.settings_controller.settings = AppSettings(confirm_resign=False)
        with patch.object(self.app, "_emit_resignation") as mock:
            self.app._handle_resign_action()
            mock.assert_called_once()

    def test_emit_resignation_determines_winner(self):
        self.app.board_view.game.board.turn = chess.WHITE
        from utils.signals import bus as global_bus
        from utils.events import GameEndedEvent
        received = []
        global_bus.connect(GameEndedEvent, lambda e: received.append(e))
        self.app._emit_resignation()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].winner, "Black")
        self.assertEqual(received[0].reason, "resignation")


class TestChessAppGameEnded(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.app = ChessApp(self.page)

    def test_game_ended_shows_dialog(self):
        from utils.events import GameEndedEvent
        event = GameEndedEvent(winner="White", reason="checkmate", message="White wins.")
        self.app._handle_game_ended(event)
        self.assertEqual(self.app.result_dialog_title.value, "White")
        self.assertEqual(self.app.result_dialog_message.value, "White wins.")

    def test_game_ended_without_winner(self):
        from utils.events import GameEndedEvent
        event = GameEndedEvent(winner=None, reason="stalemate", message="Draw.")
        self.app._handle_game_ended(event)
        self.assertEqual(self.app.result_dialog_title.value, "Game Over")


class TestChessAppPageDimensions(unittest.TestCase):
    def test_resolve_page_dimensions_defaults(self):
        page = FakePage()
        page.width = None
        page.height = None
        app = ChessApp(page)
        w, h = app._resolve_page_dimensions()
        self.assertEqual(w, 500)
        self.assertEqual(h, 700)


if __name__ == "__main__":
    unittest.main()
