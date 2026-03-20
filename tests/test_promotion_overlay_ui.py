"""UI tests for promotion overlay placement and fallback behavior."""

import unittest
from pathlib import Path
import sys

from chess import QUEEN, ROOK, BISHOP, KNIGHT, parse_square, Move

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from Ui.board import ChessBoard


class TestPromotionOverlayUi(unittest.TestCase):
    """Verify promotion controls stay aligned with the board state."""

    def test_promotion_option_order_is_queen_to_knight(self):
        self.assertEqual(ChessBoard.PROMOTION_OPTIONS, [QUEEN, ROOK, BISHOP, KNIGHT])

    def test_visual_row_col_for_b8_without_flip(self):
        board = ChessBoard()
        self.assertEqual(board._get_visual_row_col("b8"), (0, 1))

    def test_visual_row_col_for_b8_with_flip(self):
        board = ChessBoard()
        board._flip_board()
        self.assertEqual(board._get_visual_row_col("b8"), (7, 6))

    def test_promotion_left_clamps_inside_board(self):
        board = ChessBoard()
        self.assertEqual(board._get_promotion_left(1), 60)
        self.assertEqual(board._get_promotion_left(7), 240)

    def test_promotion_top_for_b8_is_one_square_above_board(self):
        board = ChessBoard()
        self.assertEqual(board._get_promotion_top(0), 0)

    def test_clicks_are_ignored_when_promotion_overlay_is_visible(self):
        board = ChessBoard()
        board.promotion_overlay.visible = True
        board._handle_square_click(board.square_map["e2"], "e2")
        self.assertEqual(board.highlighted_squares, set())

    def test_promotion_fallback_without_page_promotes_to_queen(self):
        board = ChessBoard()
        board.load_position("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
        board.move_piece("b7", "b8")

        promoted_piece = board.game.piece_at_square(parse_square("b8"))
        self.assertIsNotNone(promoted_piece)
        self.assertEqual(promoted_piece.piece_type, QUEEN)

    def test_overlay_for_b8_is_above_square_with_q_to_n_order(self):
        board = ChessBoard()
        board.load_position("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
        board._safe_page = lambda: object()

        board._show_promotion_dialog(Move(parse_square("b7"), parse_square("b8")))

        self.assertTrue(board.promotion_overlay.visible)
        self.assertEqual(board.promotion_overlay.left, 60)
        self.assertEqual(board.promotion_overlay.top, 0)

        controls = board.promotion_overlay.content.controls
        option_sources = [control.content.src for control in controls]
        self.assertEqual(
            option_sources,
            [
                "pieces/default/WHITE_QUEEN.png",
                "pieces/default/WHITE_ROOK.png",
                "pieces/default/WHITE_BISHOP.png",
                "pieces/default/WHITE_KNIGHT.png",
            ],
        )


if __name__ == "__main__":
    unittest.main()
