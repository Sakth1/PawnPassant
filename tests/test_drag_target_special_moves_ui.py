"""Regression tests for drag-target cleanup around special moves."""

import sys
import unittest
from pathlib import Path

from chess import parse_square

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from Ui.board import ChessBoard


class TestDragTargetSpecialMovesUi(unittest.TestCase):
    """Ensure special moves do not leave stale interaction state behind."""

    def test_en_passant_move_clears_interaction_state(self):
        board = ChessBoard()
        board.load_position("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        board._handle_piece_drag_start("e5")

        self.assertIn("d6", board.enabled_drop_targets)

        board.move_piece("e5", "d6")

        self.assertEqual(board.enabled_drop_targets, set())
        self.assertEqual(board.highlighted_squares, set())
        self.assertIsNone(board.selected_square)
        self.assertIsNotNone(board.game.piece_at_square(parse_square("d6")))
        self.assertIsNone(board.game.piece_at_square(parse_square("d5")))

    def test_castling_move_clears_interaction_state(self):
        board = ChessBoard()
        board.load_position("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        board._handle_piece_drag_start("e1")

        self.assertIn("g1", board.enabled_drop_targets)

        board.move_piece("e1", "g1")

        self.assertEqual(board.enabled_drop_targets, set())
        self.assertEqual(board.highlighted_squares, set())
        self.assertIsNone(board.selected_square)
        self.assertIsNotNone(board.game.piece_at_square(parse_square("g1")))
        self.assertIsNotNone(board.game.piece_at_square(parse_square("f1")))


if __name__ == "__main__":
    unittest.main()
