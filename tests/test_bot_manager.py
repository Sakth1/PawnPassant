"""Unit tests for core.bot_manager — BotManager construction, event wiring."""

import unittest
from unittest.mock import patch

from core.bot_manager import BotManager
from utils.events import PieceMovedEvent
from utils.models import EngineConfig, StockfishGameConfig
from utils.signals import bus


class TestBotManagerConstruction(unittest.TestCase):
    @patch("core.bot_manager.Stockfish")
    def test_creates_stockfish(self, mock_stockfish):
        bm = BotManager(engine_path="/mock/stockfish")
        mock_stockfish.assert_called_once_with(
            path="/mock/stockfish", depth=10, parameters=None
        )

    @patch("core.bot_manager.Stockfish")
    def test_accepts_stockfish_game_config(self, mock_stockfish):
        config = StockfishGameConfig(
            elo=1500,
            skill_level=12,
            depth=12,
            threads=2,
            hash_mb=128,
        )
        bm = BotManager(engine_path="/mock/stockfish", config=config)
        self.assertEqual(bm._config.elo, 1500)
        self.assertEqual(bm._config.depth, 12)

    @patch("core.bot_manager.Stockfish")
    def test_accepts_engine_config(self, mock_stockfish):
        config = EngineConfig(
            elo=2000,
            depth=20,
            threads=4,
        )
        bm = BotManager(engine_path="/mock/stockfish", config=config)
        self.assertEqual(bm._config.elo, 2000)
        self.assertEqual(bm._config.depth, 20)
        self.assertEqual(bm._config.threads, 4)


class TestBotManagerEventHandler(unittest.TestCase):
    @patch("core.bot_manager.Stockfish")
    def test_handles_piece_moved_event(self, mock_stockfish):
        """BotManager subscribes to PieceMovedEvent without error."""
        bm = BotManager(engine_path="/mock/stockfish")
        bus.emit(PieceMovedEvent("fen_string", "white"))

    @patch("core.bot_manager.Stockfish")
    def test_multiple_events_do_not_crash(self, mock_stockfish):
        bm = BotManager(engine_path="/mock/stockfish")
        for _ in range(5):
            bus.emit(PieceMovedEvent("fen_string", "black"))


if __name__ == "__main__":
    unittest.main()
