"""Unit tests for ui.board — ChessBoard construction, squares, move helpers."""

import unittest

import chess

from ui.board import ChessBoard
from utils.constants import BOARD_SIZE


class TestChessBoardConstruction(unittest.TestCase):
    def test_creates_game(self):
        board = ChessBoard()
        self.assertIsNotNone(board.game_manager)

    def test_creates_64_squares(self):
        board = ChessBoard()
        self.assertEqual(len(board.squares), BOARD_SIZE * BOARD_SIZE)

    def test_square_map_has_all_coordinates(self):
        board = ChessBoard()
        for file in chess.FILE_NAMES:
            for rank in chess.RANK_NAMES:
                coord = f"{file}{rank}"
                self.assertIn(coord, board.square_map)

    def test_promotion_options_4_pieces(self):
        self.assertEqual(len(ChessBoard.PROMOTION_OPTIONS), 4)

    def test_promotion_name_to_piece(self):
        mapping = ChessBoard.PROMOTION_NAME_TO_PIECE
        self.assertEqual(mapping["queen"], chess.QUEEN)
        self.assertEqual(mapping["rook"], chess.ROOK)
        self.assertEqual(mapping["bishop"], chess.BISHOP)
        self.assertEqual(mapping["knight"], chess.KNIGHT)

    def test_is_flipped_default_false(self):
        board = ChessBoard()
        self.assertFalse(board.is_flipped)

    def test_test_positions_count(self):
        self.assertEqual(len(ChessBoard.TEST_POSITIONS), 5)


class TestChessBoardSelectable(unittest.TestCase):
    def test_is_selectable_square_white_piece_start(self):
        board = ChessBoard()
        is_sel = board._is_selectable_square("e2")
        self.assertTrue(is_sel)

    def test_is_selectable_square_black_piece_false_on_white_turn(self):
        board = ChessBoard()
        is_sel = board._is_selectable_square("e7")
        self.assertFalse(is_sel)

    def test_is_selectable_square_empty_square(self):
        board = ChessBoard()
        board.game_manager.reset_board()
        is_sel = board._is_selectable_square("e4")
        self.assertFalse(is_sel)


class TestChessBoardLegalTargets(unittest.TestCase):
    def test_get_legal_targets_for_e2_pawn(self):
        board = ChessBoard()
        targets = board._get_legal_targets("e2")
        self.assertIn("e3", targets)
        self.assertIn("e4", targets)

    def test_get_legal_targets_for_empty_square(self):
        board = ChessBoard()
        targets = board._get_legal_targets("e4")
        self.assertEqual(targets, [])


class TestChessBoardIsLegalMove(unittest.TestCase):
    def test_e2e4_is_legal(self):
        board = ChessBoard()
        move = chess.Move.from_uci("e2e4")
        self.assertTrue(board._is_legal_move(move))

    def test_e2e5_is_illegal(self):
        board = ChessBoard()
        move = chess.Move.from_uci("e2e5")
        self.assertFalse(board._is_legal_move(move))


class TestChessBoardGetVisualRowCol(unittest.TestCase):
    def test_a1_visual_rank7_col0(self):
        board = ChessBoard()
        row, col = board._get_visual_row_col("a1")
        self.assertEqual(row, 7)
        self.assertEqual(col, 0)

    def test_a8_visual_rank0_col0(self):
        board = ChessBoard()
        row, col = board._get_visual_row_col("a8")
        self.assertEqual(row, 0)
        self.assertEqual(col, 0)

    def test_h1_visual_rank7_col7(self):
        board = ChessBoard()
        row, col = board._get_visual_row_col("h1")
        self.assertEqual(row, 7)
        self.assertEqual(col, 7)


class TestChessBoardGetCenterPixel(unittest.TestCase):
    def test_a1_center_x_y(self):
        board = ChessBoard()
        cx, cy = board._get_center_pixel_of_square("a1")
        self.assertEqual(cx, board.square_size / 2)
        self.assertEqual(
            cy,
            board.promotion_lane_px + (7 * board.square_size) + (board.square_size / 2),
        )


class TestChessBoardPromotionPosition(unittest.TestCase):
    def test_get_promotion_left_zero_for_first_col(self):
        board = ChessBoard()
        left = board._get_promotion_left(0)
        self.assertEqual(left, 0)

    def test_get_promotion_top(self):
        board = ChessBoard()
        top = board._get_promotion_top(0)
        self.assertEqual(top, board.promotion_lane_px - board.square_size)


class TestChessBoardFlip(unittest.TestCase):
    def test_flip_board_changes_is_flipped(self):
        board = ChessBoard()
        board._flip_board()
        self.assertTrue(board.is_flipped)

    def test_flip_board_twice_restores(self):
        board = ChessBoard()
        board._flip_board()
        board._flip_board()
        self.assertFalse(board.is_flipped)


class TestChessBoardAnimationDuration(unittest.TestCase):
    def test_default_animation_duration(self):
        board = ChessBoard()
        self.assertEqual(
            board._animation_duration_ms(),
            board.MOVE_ANIMATION_DURATIONS["normal"],
        )


if __name__ == "__main__":
    unittest.main()
