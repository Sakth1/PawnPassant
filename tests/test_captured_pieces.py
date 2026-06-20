"""Unit tests for ui.captured_pieces — CaputredPieces construction, drag/drop helpers."""

import unittest

import chess

from ui.captured_pieces import CaputredPieces
from utils.constants import CAPTURED_PANEL_BG, MAX_CAPTURES


class TestCaputredPiecesConstruction(unittest.TestCase):
    def test_creates_with_squares(self):
        cp = CaputredPieces()
        self.assertEqual(len(cp.black_squares), MAX_CAPTURES)
        self.assertEqual(len(cp.white_squares), MAX_CAPTURES)

    def test_available_squares_match_count(self):
        cp = CaputredPieces()
        self.assertEqual(len(cp.available_white_squares), MAX_CAPTURES)
        self.assertEqual(len(cp.available_black_squares), MAX_CAPTURES)

    def test_bgcolor_is_captured_panel_bg(self):
        cp = CaputredPieces()
        self.assertEqual(cp.bgcolor, CAPTURED_PANEL_BG)

    def test_has_grids(self):
        cp = CaputredPieces()
        self.assertIsNotNone(cp.black_grid)
        self.assertIsNotNone(cp.white_grid)

    def test_grids_have_4_columns(self):
        cp = CaputredPieces()
        self.assertEqual(cp.black_grid.runs_count, 4)
        self.assertEqual(cp.white_grid.runs_count, 4)

    def test_divider_present(self):
        cp = CaputredPieces()
        self.assertIsNotNone(cp.divider)


class TestCaputredPiecesGetRandomAvailable(unittest.TestCase):
    def test_random_available_returns_valid_index_white(self):
        cp = CaputredPieces()
        pos = cp._get_random_available_position(chess.WHITE)
        self.assertIn(pos, range(MAX_CAPTURES))

    def test_random_available_returns_valid_index_black(self):
        cp = CaputredPieces()
        pos = cp._get_random_available_position(chess.BLACK)
        self.assertIn(pos, range(MAX_CAPTURES))

    def test_no_available_slots_fallback(self):
        cp = CaputredPieces()
        cp.available_white_squares.clear()
        pos = cp._get_random_available_position(chess.WHITE)
        self.assertEqual(pos, MAX_CAPTURES + 1)

    def test_no_available_black_slots_fallback(self):
        cp = CaputredPieces()
        cp.available_black_squares.clear()
        pos = cp._get_random_available_position(chess.BLACK)
        self.assertEqual(pos, MAX_CAPTURES + 1)


class TestCaputredPiecesFindSquare(unittest.TestCase):
    def test_find_white_square(self):
        cp = CaputredPieces()
        sq = cp._find_square("0", color=chess.WHITE)
        self.assertIsNotNone(sq)
        self.assertEqual(sq.coordinate, "0")

    def test_find_black_square(self):
        cp = CaputredPieces()
        sq = cp._find_square("0", color=chess.BLACK)
        self.assertIsNotNone(sq)
        self.assertEqual(sq.coordinate, "0")

    def test_find_any_square(self):
        cp = CaputredPieces()
        sq = cp._find_square("5")
        self.assertIsNotNone(sq)
        self.assertEqual(sq.coordinate, "5")

    def test_find_nonexistent_square(self):
        cp = CaputredPieces()
        sq = cp._find_square("999")
        self.assertIsNone(sq)


class TestCaputredPiecesMovePiece(unittest.TestCase):
    def test_move_piece_empty_source_returns_false(self):
        cp = CaputredPieces()
        result = cp.move_piece("0", "1", source_color=chess.WHITE)
        self.assertFalse(result)

    def test_move_piece_same_coords_ignored(self):
        with self.assertLogs("ui.captured_pieces", level="DEBUG"):
            cp = CaputredPieces()
            result = cp.move_piece("0", "0", source_color=chess.WHITE)
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
