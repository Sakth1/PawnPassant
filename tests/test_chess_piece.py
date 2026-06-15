"""Unit tests for ui.chess_piece.ChessPiece — construction, rendering, resize."""

import unittest
from unittest.mock import MagicMock, patch

import chess

from ui.chess_piece import ChessPiece
from utils.constants import DEFAULT_SQUARE_SIZE, PIECE_CLICK_SCALE


PIECE_CLASSES = [chess.PAWN, chess.KNIGHT, chess.BISHOP,
                 chess.ROOK, chess.QUEEN, chess.KING]


class TestChessPieceConstruction(unittest.TestCase):
    def test_creates_with_pawn(self):
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        self.assertEqual(p.piece.piece_type, chess.PAWN)
        self.assertTrue(p.color)

    def test_creates_with_black_king(self):
        p = ChessPiece(chess.Piece(chess.KING, chess.BLACK))
        self.assertEqual(p.piece.piece_type, chess.KING)
        self.assertFalse(p.color)

    def test_each_piece_type_creates_successfully(self):
        for pt in PIECE_CLASSES:
            for col in (chess.WHITE, chess.BLACK):
                p = ChessPiece(chess.Piece(pt, col))
                self.assertEqual(p.piece.piece_type, pt)
                self.assertEqual(p.color, col)

    def test_default_scale_is_1(self):
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        self.assertEqual(p.scale, 1)

    def test_default_square_size_is_default(self):
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        self.assertEqual(p.square_size, DEFAULT_SQUARE_SIZE)


class TestChessPieceToControl(unittest.TestCase):
    def test_to_control_returns_self(self):
        p = ChessPiece(chess.Piece(chess.QUEEN, chess.BLACK))
        result = p.to_control()
        self.assertIs(result, p)

    def test_to_control_sets_width_and_height(self):
        p = ChessPiece(chess.Piece(chess.KNIGHT, chess.WHITE))
        p.to_control()
        self.assertEqual(p.width, DEFAULT_SQUARE_SIZE)
        self.assertEqual(p.height, DEFAULT_SQUARE_SIZE)

    def test_to_control_sets_content_to_image(self):
        from flet import Image
        p = ChessPiece(chess.Piece(chess.ROOK, chess.BLACK))
        p.to_control()
        self.assertIsInstance(p.content, Image)


class TestChessPieceSetSquareSize(unittest.TestCase):
    def test_updates_square_size(self):
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        p.to_control()
        p.set_square_size(80)
        self.assertEqual(p.square_size, 80)

    def test_resizes_width_and_height(self):
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        p.to_control()
        p.set_square_size(50)
        self.assertEqual(p.width, 50)
        self.assertEqual(p.height, 50)

    def test_minimum_image_size_20(self):
        from flet import Image
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        p.to_control()
        p.set_square_size(10)
        img = p.content
        self.assertIsInstance(img, Image)
        self.assertGreaterEqual(img.width, 20)
        self.assertGreaterEqual(img.height, 20)


class TestChessPieceAnimateClick(unittest.TestCase):
    def test_animate_click_sets_scale(self):
        p = ChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        # Patch page property so _animate_click doesn't raise RuntimeError
        with patch.object(ChessPiece, 'page', new_callable=MagicMock):
            p._animate_click()
        self.assertEqual(p.scale, PIECE_CLICK_SCALE)


if __name__ == "__main__":
    unittest.main()
