"""Tests for winner disclosure via checkmate and flag fall."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.board import ChessBoard
from ui.app import ChessApp
from ui.clockui import ClockUI
from utils.events import ClockStateEvent, GameEndedEvent
from utils.models import ActiveColor
from utils.signals import bus


class TestGameEndings(unittest.TestCase):
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

    def test_checkmate_move_emits_winner_event(self):
        board = ChessBoard()
        board.load_position("k7/8/1K1R4/8/8/8/8/8 w - - 0 1")

        board.move_piece("d6", "d8")

        self.assertEqual(len(self.ended_events), 1)
        self.assertEqual(self.ended_events[0].winner, "White")
        self.assertEqual(self.ended_events[0].reason, "checkmate")
        self.assertEqual(self.ended_events[0].message, "White wins by checkmate.")

    def test_flagged_clock_emits_time_winner(self):
        clock_ui = ClockUI()

        clock_ui._handle_clock_state(
            ClockStateEvent(state="flagged", active_color=ActiveColor.BLACK)
        )

        self.assertEqual(len(self.ended_events), 1)
        self.assertEqual(self.ended_events[0].winner, "White")
        self.assertEqual(self.ended_events[0].reason, "time")
        self.assertEqual(self.ended_events[0].message, "White wins on time.")

    def test_clock_draw_action_emits_agreed_draw(self):
        clock_ui = ClockUI(on_draw=lambda _event: bus.emit(
            GameEndedEvent(winner="Draw", reason="agreement", message="Draw by agreement.")
        ))

        clock_ui._handle_draw_click(None)

        self.assertEqual(len(self.ended_events), 1)
        self.assertEqual(self.ended_events[0].winner, "Draw")
        self.assertEqual(self.ended_events[0].reason, "agreement")

    def test_resign_action_awards_game_to_opponent(self):
        app = ChessApp.__new__(ChessApp)
        app.board_view = ChessBoard()

        app._handle_resign_action()

        self.assertEqual(len(self.ended_events), 1)
        self.assertEqual(self.ended_events[0].winner, "Black")
        self.assertEqual(self.ended_events[0].reason, "resignation")
