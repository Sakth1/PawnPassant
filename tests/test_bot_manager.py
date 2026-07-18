"""Tests for core.bot_manager — BotManager with EngineManager."""

import unittest
from unittest.mock import MagicMock, patch

from core.bot_manager import BotManager
from utils.models import StockfishGameConfig


class TestBotManager(unittest.TestCase):
    @patch("core.bot_manager.EngineManager")
    def test_creates_engine_manager(self, mock_engine_cls):
        bm = BotManager(engine_path="/mock/stockfish")
        mock_engine_cls.assert_called_once()
        call_kwargs = mock_engine_cls.call_args[1]
        self.assertEqual(call_kwargs["engine_path"], "/mock/stockfish")

    @patch("core.bot_manager.EngineManager")
    def test_start_starts_engine(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        bm = BotManager(engine_path="/mock/stockfish")
        result = bm.start()
        mock_engine.start.assert_called_once()
        self.assertTrue(result)

    @patch("core.bot_manager.EngineManager")
    def test_start_configures_stockfish(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        mock_engine.start.return_value = True
        config = StockfishGameConfig(elo=1800, threads=4, hash_mb=512)
        bm = BotManager(engine_path="/mock/stockfish", config=config)
        bm.start()
        mock_engine.configure_stockfish.assert_called_once_with(
            elo=1800, threads=4, hash_mb=512,
        )

    @patch("core.bot_manager.EngineManager")
    def test_stop_stops_engine(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        bm = BotManager(engine_path="/mock/stockfish")
        bm.start()
        bm.stop()
        mock_engine.stop.assert_called_once()

    @patch("core.bot_manager.EngineManager")
    def test_accepts_stockfish_game_config(self, mock_engine_cls):
        config = StockfishGameConfig(elo=2100, threads=4)
        bm = BotManager(engine_path="/mock/stockfish", config=config)
        self.assertEqual(bm._config.elo, 2100)
        self.assertEqual(bm._config.threads, 4)

    @patch("core.bot_manager.EngineManager")
    def test_set_config_updates_uci_options(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        bm = BotManager(engine_path="/mock/stockfish")
        new_config = StockfishGameConfig(elo=2500, threads=4, hash_mb=1024)
        bm.set_config(new_config)
        mock_engine.configure_stockfish.assert_called_once_with(
            elo=2500, threads=4, hash_mb=1024,
        )


if __name__ == "__main__":
    unittest.main()
