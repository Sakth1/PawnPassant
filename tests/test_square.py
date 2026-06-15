"""Unit tests for ui.square — Square and InvisibleSquare construction, state."""

import unittest

import chess

from ui.square import InvisibleSquare, Square
from utils.constants import (
    BOARD_DRAG_GROUP,
    DEFAULT_SQUARE_SIZE,
    INVISIBLE_SQUARE_BG,
)


class TestSquareConstruction(unittest.TestCase):
    def test_creates_with_coordinates(self):
        sq = Square(file=4, rank=3, coordinate="e4",
                    color=chess.WHITE)
        self.assertEqual(sq.coordinate, "e4")
        self.assertEqual(sq.file, 4)
        self.assertEqual(sq.rank, 3)

    def test_default_has_no_piece(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        self.assertFalse(sq.has_piece)
        self.assertIsNone(sq.piece_container)

    def test_size_default(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        self.assertEqual(sq.size, DEFAULT_SQUARE_SIZE)

    def test_drag_group_matches_board(self):
        self.assertEqual(Square.DRAG_GROUP, BOARD_DRAG_GROUP)

    def test_highlight_metadata_default(self):
        sq = Square(file=2, rank=2, coordinate="c3",
                    color=chess.BLACK)
        self.assertFalse(sq.highlighted_metadata["highlighted"])
        self.assertIsNone(sq.highlighted_metadata["parent_piece_square"])

    def test_show_coordinates_default_true(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        self.assertTrue(sq.show_coordinates)

    def test_is_flipped_default_false(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        self.assertFalse(sq.is_flipped)


class TestSquareHighlight(unittest.TestCase):
    def test_set_highlight_updates_metadata(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_highlight(True, "e4", refresh=False)
        self.assertTrue(sq.highlighted_metadata["highlighted"])
        self.assertEqual(
            sq.highlighted_metadata["parent_piece_square"], "e4"
        )

    def test_clear_highlight(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_highlight(True, "e4", refresh=False)
        sq.set_highlight(False, refresh=False)
        self.assertFalse(sq.highlighted_metadata["highlighted"])

    def test_highlight_then_no_parent(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_highlight(True, "e4", refresh=False)
        sq.set_highlight(False, refresh=False)
        self.assertIsNone(sq.highlighted_metadata["parent_piece_square"])


class TestSquareApplySize(unittest.TestCase):
    def test_apply_size_updates(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.apply_size(80)
        self.assertEqual(sq.size, 80)
        self.assertEqual(sq.width, 80)
        self.assertEqual(sq.height, 80)


class TestSquareTapFeedback(unittest.TestCase):
    def test_set_tap_feedback_on(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_tap_feedback(True, refresh=False)
        self.assertTrue(sq.tap_feedback_active)

    def test_set_tap_feedback_off(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_tap_feedback(True, refresh=False)
        sq.set_tap_feedback(False, refresh=False)
        self.assertFalse(sq.tap_feedback_active)

    def test_set_tap_feedback_twice_noop(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_tap_feedback(True, refresh=False)
        sq.set_tap_feedback(True, refresh=False)  # should not error


class TestSquareSetCoordinatesVisible(unittest.TestCase):
    def test_coordinates_visible(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_coordinates_visible(True, is_flipped=False, refresh=False)

    def test_coordinates_hidden(self):
        sq = Square(file=0, rank=0, coordinate="a1",
                    color=chess.WHITE)
        sq.set_coordinates_visible(False, refresh=False)
        self.assertFalse(sq.show_coordinates)

    def test_flipped_coordinates(self):
        sq = Square(file=7, rank=7, coordinate="h8",
                    color=chess.BLACK)
        sq.set_coordinates_visible(True, is_flipped=True, refresh=False)
        self.assertTrue(sq.is_flipped)


class TestInvisibleSquare(unittest.TestCase):
    def test_creates_with_color(self):
        inv = InvisibleSquare(coordinate=0, color=chess.WHITE,
                              drag_drop_group="test-group")
        self.assertEqual(inv.color, chess.WHITE)
        self.assertEqual(inv.coordinate, 0)

    def test_default_has_no_piece(self):
        inv = InvisibleSquare(coordinate=1, color=chess.BLACK,
                              drag_drop_group="test-group")
        self.assertFalse(inv.has_piece)
        self.assertIsNone(inv.piece_container)

    def test_background_is_invisible(self):
        inv = InvisibleSquare(coordinate=2, color=chess.WHITE,
                              drag_drop_group="test-group")
        self.assertEqual(inv.bgcolor, INVISIBLE_SQUARE_BG)

    def test_parse_drag_data_valid(self):
        color, coord = InvisibleSquare.parse_drag_data("1:5")
        self.assertEqual(color, 1)
        self.assertEqual(coord, "5")

    def test_parse_drag_data_no_colon(self):
        color, coord = InvisibleSquare.parse_drag_data("abc")
        self.assertIsNone(color)
        self.assertEqual(coord, "abc")

    def test_parse_drag_data_bad_int(self):
        color, coord = InvisibleSquare.parse_drag_data("abc:5")
        self.assertIsNone(color)
        self.assertEqual(coord, "5")

    def test_drag_data_encoding(self):
        inv = InvisibleSquare(coordinate=3, color=chess.WHITE,
                              drag_drop_group="test-group")
        data = inv._drag_data()
        color_val, coord = InvisibleSquare.parse_drag_data(data)
        self.assertEqual(color_val, 1)
        self.assertEqual(coord, "3")

    def test_apply_size(self):
        inv = InvisibleSquare(coordinate=0, color=chess.WHITE,
                              drag_drop_group="test-group")
        inv.apply_size(64)
        self.assertEqual(inv.size, 64)
        self.assertEqual(inv.width, 64)
        self.assertEqual(inv.height, 64)


if __name__ == "__main__":
    unittest.main()
