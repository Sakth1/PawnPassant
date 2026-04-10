"""Regression tests for invalid UI move attempts."""

import asyncio
import sys
import unittest
from pathlib import Path

from chess import parse_square

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.board import ChessBoard


class _ImmediatePage:
    """Minimal page stub that runs board animation tasks immediately."""

    def run_task(self, coroutine_fn):
        asyncio.run(coroutine_fn())


class TestInvalidMoveUi(unittest.TestCase):
    """Verify invalid drag/drop attempts do not mutate visible or game state."""

    def test_invalid_animated_drop_keeps_piece_on_source_square(self):
        board = ChessBoard()
        board._safe_page = lambda: _ImmediatePage()

        source_before = board.square_map["e2"].piece_container
        self.assertIsNotNone(source_before)
        self.assertIsNone(board.square_map["e5"].piece_container)

        board._animate_piece_and_move("e2", "e5")

        self.assertIs(board.square_map["e2"].piece_container, source_before)
        self.assertIsNone(board.square_map["e5"].piece_container)
        self.assertIsNotNone(board.game.piece_at_square(parse_square("e2")))
        self.assertIsNone(board.game.piece_at_square(parse_square("e5")))


if __name__ == "__main__":
    unittest.main()
