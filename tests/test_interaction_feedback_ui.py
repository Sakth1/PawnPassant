"""UI tests for tap and drag interaction feedback on the chess board."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from Ui.board import ChessBoard


class TestInteractionFeedbackUi(unittest.TestCase):
    """Verify click and drag interactions keep selection feedback consistent."""

    @staticmethod
    def _active_drop_targets(board: ChessBoard) -> set[str]:
        return {
            coord
            for coord, square in board.square_map.items()
            if square.drop_target_metadata["active"]
        }

    def test_click_selects_piece_and_shows_legal_targets(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["e2"], "e2")

        self.assertEqual(board.selected_square, "e2")
        self.assertEqual(board.highlighted_squares, {"e3", "e4"})
        self.assertEqual(self._active_drop_targets(board), {"e3", "e4"})
        self.assertTrue(board.square_map["e2"].tap_feedback_active)

    def test_clicking_selected_piece_clears_its_move_hints(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["e2"], "e2")
        board._handle_square_click(board.square_map["e2"], "e2")

        self.assertIsNone(board.selected_square)
        self.assertEqual(board.highlighted_squares, set())
        self.assertEqual(self._active_drop_targets(board), set())
        self.assertTrue(board.square_map["e2"].tap_feedback_active)

    def test_drag_start_shows_same_targets_as_tap_selection(self):
        board = ChessBoard()

        board._handle_piece_drag_start("e2")

        self.assertEqual(board.selected_square, "e2")
        self.assertEqual(board.highlighted_squares, {"e3", "e4"})
        self.assertEqual(self._active_drop_targets(board), {"e3", "e4"})
        self.assertTrue(board.square_map["e2"].tap_feedback_active)

    def test_cancelled_drag_clears_selection_and_feedback(self):
        board = ChessBoard()

        board._handle_piece_drag_start("e2")
        board._handle_piece_drag_complete("e2")

        self.assertIsNone(board.selected_square)
        self.assertEqual(board.highlighted_squares, set())
        self.assertEqual(self._active_drop_targets(board), set())
        self.assertIsNone(board.active_tap_feedback_square)
        self.assertFalse(board.square_map["e2"].tap_feedback_active)

    def test_only_legal_targets_are_enabled_for_selected_piece(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["g1"], "g1")

        self.assertEqual(board.highlighted_squares, {"f3", "h3"})
        self.assertEqual(self._active_drop_targets(board), {"f3", "h3"})
        self.assertFalse(board.square_map["e2"].drop_target_metadata["active"])
        self.assertEqual(board.square_map["f3"].drop_target_metadata["source_square"], "g1")

    def test_reselecting_another_piece_replaces_target_state_without_stale_targets(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["e2"], "e2")
        board._handle_square_click(board.square_map["g1"], "g1")

        self.assertEqual(board.selected_square, "g1")
        self.assertEqual(board.highlighted_squares, {"f3", "h3"})
        self.assertEqual(self._active_drop_targets(board), {"f3", "h3"})
        self.assertFalse(board.square_map["e3"].drop_target_metadata["active"])
        self.assertFalse(board.square_map["e4"].drop_target_metadata["active"])

    def test_clearing_interaction_state_is_idempotent(self):
        board = ChessBoard()

        board._handle_square_click(board.square_map["e2"], "e2")
        board._clear_interaction_state(clear_tap_feedback=True)
        board._clear_interaction_state(clear_tap_feedback=True)

        self.assertIsNone(board.selected_square)
        self.assertEqual(board.highlighted_squares, set())
        self.assertEqual(self._active_drop_targets(board), set())
        self.assertIsNone(board.active_tap_feedback_square)


if __name__ == "__main__":
    unittest.main()
