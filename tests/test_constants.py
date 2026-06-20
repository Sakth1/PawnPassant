"""Unit tests for utils.constants — essential constants validated."""

import unittest

from utils.constants import (
    BOARD_SIZE,
    CAPTURE_GRID_COLUMNS,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    MAX_CAPTURES,
    MOVE_ANIMATION_DURATIONS,
    MOVE_ANIMATION_OPTIONS,
    PROMOTION_DEFAULT_OPTIONS,
    SYMBOL_MAP,
)


class TestSymbolMap(unittest.TestCase):
    def test_all_12_pieces_present(self):
        self.assertEqual(len(SYMBOL_MAP), 12)

    def test_white_pieces_uppercase(self):
        for sym in "PNBRQK":
            self.assertIn(sym, SYMBOL_MAP)
            self.assertTrue(SYMBOL_MAP[sym].startswith("WHITE_"))

    def test_black_pieces_lowercase(self):
        for sym in "pnbrqk":
            self.assertIn(sym, SYMBOL_MAP)
            self.assertTrue(SYMBOL_MAP[sym].startswith("BLACK_"))


class TestBoardDimensions(unittest.TestCase):
    def test_board_size_is_8(self):
        self.assertEqual(BOARD_SIZE, 8)

    def test_max_captures_is_16(self):
        self.assertEqual(MAX_CAPTURES, 16)

    def test_capture_grid_columns_is_4(self):
        self.assertEqual(CAPTURE_GRID_COLUMNS, 4)


class TestAnimationConstants(unittest.TestCase):
    def test_all_speed_keys_have_valid_durations(self):
        for key, duration in MOVE_ANIMATION_DURATIONS.items():
            self.assertIn(key, MOVE_ANIMATION_OPTIONS)
            self.assertIsInstance(duration, int)
            self.assertGreaterEqual(duration, 0)

    def test_fast_duration_shorter_than_normal(self):
        self.assertLess(
            MOVE_ANIMATION_DURATIONS["fast"],
            MOVE_ANIMATION_DURATIONS["normal"],
        )

    def test_normal_duration_shorter_than_slow(self):
        self.assertLess(
            MOVE_ANIMATION_DURATIONS["normal"],
            MOVE_ANIMATION_DURATIONS["slow"],
        )

    def test_off_is_zero(self):
        self.assertEqual(MOVE_ANIMATION_DURATIONS["off"], 0)


class TestPromotionOptions(unittest.TestCase):
    def test_promotion_default_options_contains_ask(self):
        self.assertIn("ask", PROMOTION_DEFAULT_OPTIONS)

    def test_promotion_default_options_contains_all_pieces(self):
        for piece in ("queen", "rook", "bishop", "knight"):
            self.assertIn(piece, PROMOTION_DEFAULT_OPTIONS)

    def test_promotion_option_count(self):
        self.assertEqual(len(PROMOTION_DEFAULT_OPTIONS), 5)


class TestCategoryLabels(unittest.TestCase):
    def test_category_keys_are_lowercase(self):
        for key in CATEGORY_ORDER:
            self.assertEqual(key, key.lower())

    def test_all_ordered_categories_have_labels(self):
        for key in CATEGORY_ORDER:
            self.assertIn(key, CATEGORY_LABELS)

    def test_label_values_are_capitalized(self):
        for label in CATEGORY_LABELS.values():
            self.assertEqual(label[0].upper(), label[0])

    def test_bullet_blitz_rapid_classical_order(self):
        self.assertEqual(CATEGORY_ORDER, ["bullet", "blitz", "rapid", "classical"])


if __name__ == "__main__":
    unittest.main()
