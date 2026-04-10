"""UI tests for tap and drag interaction feedback on the chess board."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.board import ChessBoard


class TestInteractionFeedbackUi(unittest.TestCase):
    """Verify click and drag interactions keep selection feedback consistent."""

    def test_click_selects_piece_and_shows_legal_targets(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["e2"], "e2")

        self.assertEqual(board.selected_square, "e2")
        self.assertEqual(board.highlighted_squares, {"e3", "e4"})
        self.assertTrue(board.square_map["e2"].tap_feedback_active)

    def test_clicking_selected_piece_clears_its_move_hints(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["e2"], "e2")
        board._handle_square_click(board.square_map["e2"], "e2")

        self.assertIsNone(board.selected_square)
        self.assertEqual(board.highlighted_squares, set())
        self.assertTrue(board.square_map["e2"].tap_feedback_active)

    def test_drag_start_shows_same_targets_as_tap_selection(self):
        board = ChessBoard()

        board._handle_piece_drag_start("e2")

        self.assertEqual(board.selected_square, "e2")
        self.assertEqual(board.highlighted_squares, {"e3", "e4"})
        self.assertTrue(board.square_map["e2"].tap_feedback_active)

    def test_cancelled_drag_clears_selection_and_feedback(self):
        board = ChessBoard()

        board._handle_piece_drag_start("e2")
        board._handle_piece_drag_complete("e2")

        self.assertIsNone(board.selected_square)
        self.assertEqual(board.highlighted_squares, set())
        self.assertIsNone(board.active_tap_feedback_square)
        self.assertFalse(board.square_map["e2"].tap_feedback_active)


if __name__ == "__main__":
    unittest.main()
