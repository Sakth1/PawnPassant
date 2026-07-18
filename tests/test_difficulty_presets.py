"""Tests for core.difficulty_presets — Stockfish Elo presets."""

import unittest

from core.stockfish_config import (
    STOCKFISH_ELO_PRESETS,
    ELO_MIN,
    ELO_MAX,
    elo_label,
    preset_name_for_elo,
    preset_elo,
    preset_options,
)


class TestStockfishEloPresets(unittest.TestCase):
    def test_all_presets_within_range(self):
        for name, elo in STOCKFISH_ELO_PRESETS.items():
            with self.subTest(preset=name):
                self.assertGreaterEqual(elo, ELO_MIN)
                self.assertLessEqual(elo, ELO_MAX)

    def test_beginner_is_lowest(self):
        self.assertEqual(STOCKFISH_ELO_PRESETS["beginner"], 1320)

    def test_grandmaster_is_highest(self):
        self.assertEqual(STOCKFISH_ELO_PRESETS["grandmaster"], 3190)

    def test_preset_name_for_elo(self):
        self.assertEqual(preset_name_for_elo(1320), "beginner")
        self.assertEqual(preset_name_for_elo(1800), "intermediate")
        self.assertEqual(preset_name_for_elo(3190), "grandmaster")

    def test_preset_elo_returns_correct(self):
        self.assertEqual(preset_elo("expert"), 2500)

    def test_preset_elo_returns_none_for_unknown(self):
        self.assertIsNone(preset_elo("unknown"))

    def test_preset_options_return_ordered(self):
        options = preset_options()
        self.assertGreater(len(options), 0)
        for name, _ in options:
            self.assertIn(name, STOCKFISH_ELO_PRESETS)
        elos = [STOCKFISH_ELO_PRESETS[n] for n, _ in options if n in STOCKFISH_ELO_PRESETS]
        self.assertEqual(elos, sorted(elos))

    def test_seven_presets_defined(self):
        self.assertEqual(len(STOCKFISH_ELO_PRESETS), 7)

    def test_elo_label_mapping(self):
        self.assertEqual(elo_label(1320), "Beginner")
        self.assertEqual(elo_label(1500), "Casual")
        self.assertEqual(elo_label(1800), "Intermediate")
        self.assertEqual(elo_label(2100), "Advanced")
        self.assertEqual(elo_label(2500), "Expert")
        self.assertEqual(elo_label(2800), "Master")
        self.assertEqual(elo_label(3190), "Grandmaster")


if __name__ == "__main__":
    unittest.main()
