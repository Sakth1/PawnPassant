"""Tests for StockfishGameConfig and DifficultyPreset dataclasses."""

import unittest

from utils.models import DifficultyPreset, StockfishGameConfig, EngineConfig


class TestStockfishGameConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = StockfishGameConfig()
        self.assertTrue(cfg.use_preset)
        self.assertEqual(cfg.preset_name, "intermediate")
        self.assertEqual(cfg.elo, 1350)
        self.assertIsNone(cfg.skill_level)
        self.assertEqual(cfg.depth, 15)
        self.assertEqual(cfg.threads, 1)
        self.assertEqual(cfg.hash_mb, 256)

    def test_custom_config(self):
        cfg = StockfishGameConfig(
            use_preset=False,
            elo=2000,
            skill_level=16,
            depth=20,
            threads=4,
            hash_mb=512,
        )
        self.assertFalse(cfg.use_preset)
        self.assertEqual(cfg.elo, 2000)
        self.assertEqual(cfg.skill_level, 16)
        self.assertEqual(cfg.depth, 20)
        self.assertEqual(cfg.threads, 4)
        self.assertEqual(cfg.hash_mb, 512)

    def test_mutable_default(self):
        cfg = StockfishGameConfig()
        cfg.elo = 1800
        self.assertEqual(cfg.elo, 1800)

    def test_conversion_to_engine_config(self):
        sg = StockfishGameConfig(
            elo=1500,
            skill_level=12,
            depth=10,
            threads=2,
            hash_mb=128,
        )
        ec = EngineConfig(
            depth=sg.depth,
            elo=sg.elo,
            skill_level=sg.skill_level,
            threads=sg.threads,
            hash_mb=sg.hash_mb,
        )
        self.assertEqual(ec.depth, 10)
        self.assertEqual(ec.elo, 1500)
        self.assertEqual(ec.skill_level, 12)
        self.assertEqual(ec.threads, 2)
        self.assertEqual(ec.hash_mb, 128)


class TestDifficultyPreset(unittest.TestCase):
    def test_preset_values(self):
        p = DifficultyPreset(
            name="Test",
            description="Test preset",
            elo_min=100,
            elo_max=300,
            skill_min=0,
            skill_max=2,
            depth_min=1,
            depth_max=5,
        )
        self.assertEqual(p.name, "Test")
        self.assertLess(p.elo_min, p.elo_max)
        self.assertLess(p.skill_min, p.skill_max)
        self.assertLess(p.depth_min, p.depth_max)


if __name__ == "__main__":
    unittest.main()
