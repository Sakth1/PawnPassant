"""Tests for core.difficulty_presets — presets, options, get_preset."""

import unittest

from core.difficulty_presets import DIFFICULTY_PRESETS, get_preset, preset_options


class TestDifficultyPresets(unittest.TestCase):
    def test_all_presets_have_valid_ranges(self):
        for key, preset in DIFFICULTY_PRESETS.items():
            with self.subTest(preset=key):
                self.assertGreaterEqual(preset.elo_min, 0)
                self.assertGreaterEqual(preset.elo_max, preset.elo_min)
                self.assertGreaterEqual(preset.skill_min, 0)
                self.assertGreaterEqual(preset.skill_max, preset.skill_min)
                self.assertGreaterEqual(preset.depth_min, 1)
                self.assertGreaterEqual(preset.depth_max, preset.depth_min)

    def test_beginner_is_lowest(self):
        b = DIFFICULTY_PRESETS["beginner"]
        self.assertEqual(b.name, "Beginner")
        self.assertLess(b.elo_max, 500)

    def test_master_is_highest(self):
        m = DIFFICULTY_PRESETS["master"]
        self.assertEqual(m.name, "Master")
        self.assertGreaterEqual(m.elo_min, 2000)

    def test_get_preset_returns_correct(self):
        p = get_preset("expert")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Expert")

    def test_get_preset_returns_none_for_unknown(self):
        self.assertIsNone(get_preset("unknown"))

    def test_preset_options_returns_ordered_tuples(self):
        options = preset_options()
        self.assertGreater(len(options), 0)
        for key, name in options:
            self.assertIn(key, DIFFICULTY_PRESETS)
            self.assertEqual(DIFFICULTY_PRESETS[key].name, name)

    def test_five_presets_defined(self):
        self.assertEqual(len(DIFFICULTY_PRESETS), 5)


if __name__ == "__main__":
    unittest.main()
