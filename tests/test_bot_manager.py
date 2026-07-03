"""Tests for core.bot_manager — BotManager with EngineManager."""

import unittest
from unittest.mock import MagicMock, patch

from core.bot_manager import BotManager
from utils.models import Lc0GameConfig


class TestBotManager(unittest.TestCase):
    @patch("core.bot_manager.EngineManager")
    def test_creates_engine_manager(self, mock_engine_cls):
        bm = BotManager(engine_path="/mock/lc0")
        mock_engine_cls.assert_called_once()
        call_kwargs = mock_engine_cls.call_args[1]
        self.assertEqual(call_kwargs["engine_path"], "/mock/lc0")

    @patch("core.bot_manager.EngineManager")
    def test_start_starts_engine(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        bm = BotManager(engine_path="/mock/lc0")
        result = bm.start()
        mock_engine.start.assert_called_once()
        self.assertTrue(result)

    @patch("core.bot_manager.EngineManager")
    def test_stop_stops_engine(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        bm = BotManager(engine_path="/mock/lc0")
        bm.start()
        bm.stop()
        mock_engine.stop.assert_called_once()

    @patch("core.bot_manager.EngineManager")
    def test_accepts_lc0_game_config(self, mock_engine_cls):
        config = Lc0GameConfig(
            network_name="T1-256x10-distilled",
            network_path="/weights/t1.pb.gz",
            backend="blas",
            threads=4,
            temperature=0.5,
        )
        bm = BotManager(engine_path="/mock/lc0", config=config)
        self.assertEqual(bm._config.network_name, "T1-256x10-distilled")
        self.assertEqual(bm._config.backend, "blas")

    @patch("core.bot_manager.EngineManager")
    def test_set_config_updates_uci_options(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        bm = BotManager(engine_path="/mock/lc0")
        new_config = Lc0GameConfig(
            network_name="BT4-it332",
            network_path="/weights/bt4.pb.gz",
            backend="cuda",
            threads=4,
        )
        bm.set_config(new_config)
        mock_engine.configure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
