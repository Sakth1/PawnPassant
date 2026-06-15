"""Unit tests for core.bot_manager — BotManager construction, event wiring."""

import unittest
from unittest.mock import patch

from core.bot_manager import BotManager
from utils.events import PieceMovedEvent
from utils.signals import bus


class TestBotManagerConstruction(unittest.TestCase):
    @patch("core.bot_manager.Stockfish")
    def test_creates_stockfish(self, mock_stockfish):
        bm = BotManager()
        mock_stockfish.assert_called_once()


class TestBotManagerEventHandler(unittest.TestCase):
    @patch("core.bot_manager.Stockfish")
    def test_handles_piece_moved_event(self, mock_stockfish):
        """BotManager subscribes to PieceMovedEvent without error."""
        bm = BotManager()
        bus.emit(PieceMovedEvent("fen_string", "white"))

    @patch("core.bot_manager.Stockfish")
    def test_multiple_events_do_not_crash(self, mock_stockfish):
        bm = BotManager()
        for _ in range(5):
            bus.emit(PieceMovedEvent("fen_string", "black"))


if __name__ == "__main__":
    unittest.main()
