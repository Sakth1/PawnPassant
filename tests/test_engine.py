"""Direct unit tests for core.game.GameManager — 7 terminal conditions, all move types."""

import unittest

from chess import (
    Board,
    Move,
    parse_square,
    QUEEN,
    ROOK,
    BISHOP,
    KNIGHT,
    PAWN,
)

from core.game import GameManager
from core.movetype import MoveType


class TestGameInit(unittest.TestCase):
    def test_init_creates_standard_board(self):
        game = GameManager()
        self.assertEqual(game.fen(), Board().fen())

    def test_reset_board_restores_standard_position(self):
        game = GameManager()
        game.load_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        game.reset_board()
        self.assertEqual(game.fen(), Board().fen())

    def test_set_board_fen_loads_position(self):
        game = GameManager()
        fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        game.load_fen(fen)
        self.assertEqual(game.fen(), Board(fen).fen())

    def test_get_board_fen_roundtrip(self):
        game = GameManager()
        fen = "8/8/8/4k3/4K3/8/8/8 w - - 0 1"
        game.load_fen(fen)
        self.assertEqual(game.fen(), fen)


class TestGameActiveColor(unittest.TestCase):
    def test_initial_active_color_is_white(self):
        game = GameManager()
        self.assertTrue(game.active_color())

    def test_after_move_active_color_switches(self):
        game = GameManager()
        game.push_move(Move(parse_square("e2"), parse_square("e4")))
        self.assertFalse(game.active_color())


class TestGameMoveType(unittest.TestCase):
    def _make_game(self, fen: str) -> GameManager:
        game = GameManager()
        game.load_fen(fen)
        return game

    def test_normal_move(self):
        game = self._make_game("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        move = Move(parse_square("e1"), parse_square("e2"))
        self.assertEqual(game.move_type(move), MoveType.NORMAL)

    def test_capture_move(self):
        game = self._make_game("4k3/8/8/8/4p3/8/4P3/4K3 w - - 0 1")
        move = Move(parse_square("e2"), parse_square("e4"))
        self.assertEqual(game.move_type(move), MoveType.CAPTURE)

    def test_en_passant_move(self):
        game = self._make_game("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        move = Move(parse_square("e5"), parse_square("d6"))
        self.assertEqual(game.move_type(move), MoveType.EN_PASSANT)

    def test_king_side_castling_move(self):
        game = self._make_game("4k2r/8/8/8/8/8/8/R3K3 w Qk - 0 1")
        move = Move(parse_square("e1"), parse_square("g1"))
        self.assertEqual(game.move_type(move), MoveType.KING_SIDE_CASTLING)

    def test_queen_side_castling_move(self):
        game = self._make_game("r3k3/8/8/8/8/8/8/4K3 w q - 0 1")
        game.load_fen("r3k3/8/8/8/8/8/8/R3K3 w Qq - 0 1")
        move = Move(parse_square("e1"), parse_square("c1"))
        self.assertEqual(game.move_type(move), MoveType.QUEEN_SIDE_CASTLING)

    def test_promotion_move(self):
        game = self._make_game("4k3/4P3/8/8/8/8/8/4K3 w - - 0 1")
        move = Move(parse_square("e7"), parse_square("e8"))
        self.assertEqual(game.move_type(move), MoveType.PROMOTION)

    def test_is_promotion_move_true_for_pawn_on_back_rank(self):
        game = self._make_game("4k3/4P3/8/8/8/8/8/4K3 w - - 0 1")
        move = Move(parse_square("e7"), parse_square("e8"))
        self.assertTrue(game._is_promotion_move(move))

    def test_is_promotion_move_false_for_non_pawn(self):
        game = self._make_game("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        move = Move(parse_square("e1"), parse_square("e2"))
        self.assertFalse(game._is_promotion_move(move))


class TestGameMoveAndSan(unittest.TestCase):
    def test_move_updates_board(self):
        game = GameManager()
        move = Move(parse_square("e2"), parse_square("e4"))
        game.push_move(move)
        self.assertIsNone(game.piece_at(parse_square("e2")))
        self.assertIsNotNone(game.piece_at(parse_square("e4")))

    def test_get_move_san_returns_algebraic(self):
        game = GameManager()
        move = Move(parse_square("e2"), parse_square("e4"))
        self.assertEqual(game.move_san(move), "e4")

    def test_get_last_move_returns_pushed_move(self):
        game = GameManager()
        m1 = Move(parse_square("e2"), parse_square("e4"))
        m2 = Move(parse_square("e7"), parse_square("e5"))
        game.push_move(m1)
        game.push_move(m2)
        self.assertEqual(game.last_move(), m2)


class TestGamePieces(unittest.TestCase):
    def test_piece_at_square_returns_piece(self):
        game = GameManager()
        piece = game.piece_at(parse_square("e2"))
        self.assertIsNotNone(piece)
        self.assertEqual(piece.piece_type, PAWN)

    def test_piece_at_square_returns_none_for_empty(self):
        game = GameManager()
        self.assertIsNone(game.piece_at(parse_square("e4")))

    def test_color_of_piece_at_square_returns_color(self):
        game = GameManager()
        self.assertTrue(game.color_at(parse_square("e2")))
        self.assertFalse(game.color_at(parse_square("e7")))

    def test_color_of_piece_at_square_returns_none_for_empty(self):
        game = GameManager()
        self.assertIsNone(game.color_at(parse_square("e4")))


class TestGameTerminalConditions(unittest.TestCase):
    def test_is_game_over_false_at_start(self):
        game = GameManager()
        self.assertFalse(game.is_game_over())

    def test_checkmate_detected(self):
        game = GameManager()
        game.load_fen("k7/8/1K1R4/8/8/8/8/8 w - - 0 1")
        game.push_move(Move(parse_square("d6"), parse_square("d7")))
        self.assertTrue(game.is_game_over())

    def test_stalemate_detected(self):
        game = GameManager()
        game.load_fen("7k/7P/7K/8/8/8/8/8 b - - 0 1")
        self.assertTrue(game.is_game_over())

    def test_insufficient_material_detected(self):
        game = GameManager()
        game.load_fen("8/8/8/8/8/8/4k3/4K3 w - - 0 1")
        self.assertTrue(game.is_game_over())

    def test_seventyfive_move_detected(self):
        game = GameManager()
        game.load_fen("4k3/8/8/8/8/8/8/4K3 w - - 75 100")
        self.assertTrue(game.is_game_over())

    def test_fivefold_repetition_detected(self):
        game = GameManager()
        game.load_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        for _ in range(5):
            game.push_move(Move(parse_square("e1"), parse_square("e2")))
            game.push_move(Move(parse_square("e8"), parse_square("e7")))
            game.push_move(Move(parse_square("e2"), parse_square("e1")))
            game.push_move(Move(parse_square("e7"), parse_square("e8")))
        self.assertTrue(game.is_game_over())


class TestGameWinner(unittest.TestCase):
    def test_winner_checkmate_returns_winning_color(self):
        game = GameManager()
        game.load_fen("k7/8/1K1R4/8/8/8/8/8 w - - 0 1")
        game.push_move(Move(parse_square("d6"), parse_square("d7")))
        winner = game.get_winner()
        self.assertEqual(winner, "White")

    def test_winner_stalemate_returns_draw(self):
        game = GameManager()
        game.load_fen("7k/7P/7K/8/8/8/8/8 b - - 0 1")
        self.assertEqual(game.get_winner(), "Draw")

    def test_winner_insufficient_material_returns_draw(self):
        game = GameManager()
        game.load_fen("8/8/8/8/8/8/4k3/4K3 w - - 0 1")
        self.assertEqual(game.get_winner(), "Draw")

    def test_winner_none_when_game_ongoing(self):
        game = GameManager()
        self.assertIsNone(game.get_winner())


class TestGameResultSummary(unittest.TestCase):
    def test_checkmate_summary(self):
        game = GameManager()
        game.load_fen("k7/8/1K1R4/8/8/8/8/8 w - - 0 1")
        game.push_move(Move(parse_square("d6"), parse_square("d7")))
        winner, reason, message = game.result_summary()
        self.assertEqual(winner, "White")
        self.assertEqual(reason, "checkmate")
        self.assertIn("checkmate", message)

    def test_stalemate_summary(self):
        game = GameManager()
        game.load_fen("7k/7P/7K/8/8/8/8/8 b - - 0 1")
        winner, reason, message = game.result_summary()
        self.assertEqual(winner, "Draw")
        self.assertEqual(reason, "stalemate")
        self.assertIn("stalemate", message)

    def test_insufficient_material_summary(self):
        game = GameManager()
        game.load_fen("8/8/8/8/8/8/4k3/4K3 w - - 0 1")
        winner, reason, message = game.result_summary()
        self.assertEqual(winner, "Draw")
        self.assertEqual(reason, "insufficient_material")

    def test_seventyfive_moves_summary(self):
        game = GameManager()
        game.load_fen("4k3/8/8/8/8/8/8/4K3 w - - 75 100")
        winner, reason, message = game.result_summary()
        self.assertEqual(winner, "Draw")
        self.assertEqual(reason, "seventyfive_moves")

    def test_fivefold_repetition_summary(self):
        game = GameManager()
        game.load_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        for _ in range(5):
            game.push_move(Move(parse_square("e1"), parse_square("e2")))
            game.push_move(Move(parse_square("e8"), parse_square("e7")))
            game.push_move(Move(parse_square("e2"), parse_square("e1")))
            game.push_move(Move(parse_square("e7"), parse_square("e8")))
        _, reason, _ = game.result_summary()
        self.assertEqual(reason, "fivefold_repetition")

    def test_ongoing_summary(self):
        game = GameManager()
        winner, reason, message = game.result_summary()
        self.assertIsNone(winner)
        self.assertEqual(reason, "ongoing")
        self.assertEqual(message, "")


if __name__ == "__main__":
    unittest.main()
