"""Unit tests for core.movetype.MoveType — all 6 values, StrEnum behavior."""

import unittest

from core.movetype import MoveType


class TestMoveType(unittest.TestCase):
    def test_all_members_present(self):
        expected = {
            "NORMAL",
            "CAPTURE",
            "EN_PASSANT",
            "KING_SIDE_CASTLING",
            "QUEEN_SIDE_CASTLING",
            "PROMOTION",
        }
        actual = {m.name for m in MoveType}
        self.assertEqual(actual, expected)

    def test_str_values_match_names_lowercase(self):
        for member in MoveType:
            self.assertEqual(member.value, member.name.lower())

    def test_repr_includes_name(self):
        self.assertIn("NORMAL", repr(MoveType.NORMAL))
        self.assertIn("CAPTURE", repr(MoveType.CAPTURE))

    def test_dot_name_access(self):
        self.assertEqual(MoveType.NORMAL.name, "NORMAL")
        self.assertEqual(MoveType.CAPTURE.name, "CAPTURE")
        self.assertEqual(MoveType.PROMOTION.name, "PROMOTION")
        self.assertEqual(MoveType.KING_SIDE_CASTLING.name, "KING_SIDE_CASTLING")
        self.assertEqual(MoveType.QUEEN_SIDE_CASTLING.name, "QUEEN_SIDE_CASTLING")


if __name__ == "__main__":
    unittest.main()
