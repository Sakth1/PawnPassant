"""Regression tests for captured-pieces panel interactions."""

import sys
import unittest
from pathlib import Path

from chess import Piece, WHITE

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.captured_pieces import CaputredPieces
from ui.chess_piece import ChessPiece
from ui.square import InvisibleSquare


class TestCapturedPieces(unittest.TestCase):
    def test_move_piece_uses_source_color_when_coordinates_overlap(self):
        captured_pieces = CaputredPieces()
        white_piece = ChessPiece(Piece.from_symbol("P"))
        black_piece = ChessPiece(Piece.from_symbol("p"))
        captured_pieces.white_squares[0].update_content(white_piece)
        captured_pieces.black_squares[0].update_content(black_piece)

        moved = captured_pieces.move_piece("0", "1", source_color=WHITE)

        self.assertTrue(moved)
        self.assertIsNone(captured_pieces.white_squares[0].piece_container)
        self.assertIs(captured_pieces.white_squares[1].piece_container, white_piece)
        self.assertIs(captured_pieces.black_squares[0].piece_container, black_piece)

    def test_handle_square_drop_uses_encoded_drag_source_color(self):
        captured_pieces = CaputredPieces()
        white_piece = ChessPiece(Piece.from_symbol("P"))
        black_piece = ChessPiece(Piece.from_symbol("p"))
        captured_pieces.white_squares[0].update_content(white_piece)
        captured_pieces.black_squares[0].update_content(black_piece)
        captured_pieces.available_white_squares = [1, 2, 3]

        captured_pieces._handle_square_drop("1:0", "1", WHITE, source_color=WHITE)

        self.assertIn(0, captured_pieces.available_white_squares)
        self.assertNotIn(1, captured_pieces.available_white_squares)
        self.assertIsNone(captured_pieces.white_squares[0].piece_container)
        self.assertIs(captured_pieces.white_squares[1].piece_container, white_piece)
        self.assertIs(captured_pieces.black_squares[0].piece_container, black_piece)

    def test_parse_drag_data_preserves_color_and_coordinate(self):
        source_color, source_coordinate = InvisibleSquare.parse_drag_data("1:7")

        self.assertEqual(source_color, WHITE)
        self.assertEqual(source_coordinate, "7")


if __name__ == "__main__":
    unittest.main()
