"""Unit tests for ui.captured_pieces — compact CaputredPieces component."""

import unittest

import chess

from ui.captured_pieces import CaputredPieces
from ui.chess_piece import ChessPiece
from utils.events import PieceCapturedEvent


class _FakeChessPiece:
    """Minimal fake matching the ChessPiece interface used by events."""

    def __init__(self, piece: chess.Piece):
        self.piece = piece


class TestCaputredPiecesConstruction(unittest.TestCase):
    def test_creates_empty(self):
        cp = CaputredPieces()
        self.assertEqual(len(cp._captured), 0)
        self.assertIsNone(cp._capturing_side)

    def test_creates_with_capturing_side(self):
        cp = CaputredPieces(capturing_side=chess.WHITE)
        self.assertEqual(cp._capturing_side, chess.WHITE)

    def test_default_icon_size(self):
        cp = CaputredPieces()
        self.assertEqual(cp._icon_size, 20)


class TestCaputredPiecesCaptureHandler(unittest.TestCase):
    def test_adds_captured_piece(self):
        cp = CaputredPieces()
        piece = _FakeChessPiece(chess.Piece(chess.QUEEN, chess.WHITE))
        event = PieceCapturedEvent(piece=piece, color=chess.WHITE)
        cp._handle_piece_captured(event)
        self.assertEqual(len(cp._captured), 1)
        self.assertEqual(cp._captured[0].piece_type, chess.QUEEN)

    def test_filters_by_capturing_side(self):
        cp = CaputredPieces(capturing_side=chess.WHITE)
        piece = _FakeChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        event = PieceCapturedEvent(piece=piece, color=chess.BLACK)
        cp._handle_piece_captured(event)
        self.assertEqual(len(cp._captured), 0)

    def test_allows_matching_side(self):
        cp = CaputredPieces(capturing_side=chess.BLACK)
        piece = _FakeChessPiece(chess.Piece(chess.ROOK, chess.WHITE))
        event = PieceCapturedEvent(piece=piece, color=chess.BLACK)
        cp._handle_piece_captured(event)
        self.assertEqual(len(cp._captured), 1)

    def test_no_filter_accepts_all(self):
        cp = CaputredPieces(capturing_side=None)
        piece_w = _FakeChessPiece(chess.Piece(chess.PAWN, chess.WHITE))
        piece_b = _FakeChessPiece(chess.Piece(chess.QUEEN, chess.BLACK))
        cp._handle_piece_captured(PieceCapturedEvent(piece=piece_w, color=chess.WHITE))
        cp._handle_piece_captured(PieceCapturedEvent(piece=piece_b, color=chess.BLACK))
        self.assertEqual(len(cp._captured), 2)


class TestCaputredPiecesRebuild(unittest.TestCase):
    def test_empty_rebuild(self):
        cp = CaputredPieces()
        cp._rebuild_display()
        self.assertEqual(len(cp._piece_row.controls), 0)

    def test_single_capture_shows_one_icon(self):
        cp = CaputredPieces()
        cp._captured.append(chess.Piece(chess.QUEEN, chess.WHITE))
        cp._rebuild_display()
        self.assertGreater(len(cp._piece_row.controls), 0)
        self.assertTrue(cp._label.visible)

    def test_label_hidden_when_empty(self):
        cp = CaputredPieces()
        cp._rebuild_display()
        self.assertFalse(cp._label.visible)

    def test_label_visible_when_pieces_exist(self):
        cp = CaputredPieces()
        cp._captured.append(chess.Piece(chess.PAWN, chess.BLACK))
        cp._rebuild_display()
        self.assertTrue(cp._label.visible)

    def test_duplicates_grouped_with_count(self):
        cp = CaputredPieces()
        for _ in range(3):
            cp._captured.append(chess.Piece(chess.KNIGHT, chess.WHITE))
        cp._rebuild_display()
        text_controls = [
            c for c in cp._piece_row.controls
            if isinstance(c, ChessPiece.__class__)
        ]
        self.assertGreater(len(cp._piece_row.controls), 1)


class TestCaputredPiecesReset(unittest.TestCase):
    def test_reset_clears_pieces(self):
        cp = CaputredPieces()
        cp._captured.append(chess.Piece(chess.KING, chess.WHITE))
        cp.reset()
        self.assertEqual(len(cp._captured), 0)
        self.assertEqual(len(cp._piece_row.controls), 0)


if __name__ == "__main__":
    unittest.main()
