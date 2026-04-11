"""Unit tests for captured pieces model."""

import unittest
from src.utils.captured_pieces_model import CapturedPiecesModel


class TestCapturedPiecesModel(unittest.TestCase):
    """Test suite for CapturedPiecesModel."""

    def setUp(self):
        """Set up test fixtures."""
        self.model = CapturedPiecesModel()

    def test_initialization(self):
        """Test model initializes with empty lists."""
        self.assertEqual(self.model.black_captured_pieces, [])
        self.assertEqual(self.model.white_captured_pieces, [])

    def test_add_captured_piece_white(self):
        """Test adding pieces captured by white."""
        self.model.add_captured_piece("pawn", "white")
        self.assertEqual(self.model.white_captured_pieces, ["pawn"])
        self.assertEqual(self.model.black_captured_pieces, [])

    def test_add_captured_piece_black(self):
        """Test adding pieces captured by black."""
        self.model.add_captured_piece("knight", "black")
        self.assertEqual(self.model.black_captured_pieces, ["knight"])
        self.assertEqual(self.model.white_captured_pieces, [])

    def test_add_multiple_pieces(self):
        """Test adding multiple pieces."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "white")
        
        self.assertEqual(self.model.white_captured_pieces, ["pawn", "pawn", "knight"])

    def test_get_captured_pieces_white(self):
        """Test retrieving pieces captured by white."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "white")
        
        pieces = self.model.get_captured_pieces("white")
        self.assertEqual(pieces, ["pawn", "knight"])

    def test_get_captured_pieces_black(self):
        """Test retrieving pieces captured by black."""
        self.model.add_captured_piece("rook", "black")
        
        pieces = self.model.get_captured_pieces("black")
        self.assertEqual(pieces, ["rook"])

    def test_ownership_reversal_white_side(self):
        """Test that black's captured pieces display on white's side."""
        self.model.add_captured_piece("pawn", "black")  # Black captured pawn
        
        # Pieces captured BY black should appear on WHITE's side
        pieces = self.model.get_pieces_to_display_for_side("white")
        self.assertIn("pawn", pieces)
        
        # Should NOT appear on black's side
        pieces = self.model.get_pieces_to_display_for_side("black")
        self.assertNotIn("pawn", pieces)

    def test_ownership_reversal_black_side(self):
        """Test that white's captured pieces display on black's side."""
        self.model.add_captured_piece("knight", "white")  # White captured knight
        
        # Pieces captured BY white should appear on BLACK's side
        pieces = self.model.get_pieces_to_display_for_side("black")
        self.assertIn("knight", pieces)
        
        # Should NOT appear on white's side
        pieces = self.model.get_pieces_to_display_for_side("white")
        self.assertNotIn("knight", pieces)

    def test_mixed_captures(self):
        """Test with captures from both players."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "black")
        
        # White's side displays black's captures
        white_side = self.model.get_pieces_to_display_for_side("white")
        self.assertEqual(white_side, ["knight"])
        
        # Black's side displays white's captures
        black_side = self.model.get_pieces_to_display_for_side("black")
        self.assertEqual(black_side, ["pawn", "pawn"])

    def test_clear_all_pieces(self):
        """Test clearing all captured pieces."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "black")
        
        self.model.clear()
        
        self.assertEqual(self.model.white_captured_pieces, [])
        self.assertEqual(self.model.black_captured_pieces, [])
        self.assertEqual(self.model.get_captured_pieces("white"), [])
        self.assertEqual(self.model.get_captured_pieces("black"), [])

    def test_to_dict_export(self):
        """Test exporting model state as dictionary."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "white")
        self.model.add_captured_piece("rook", "black")
        
        state = self.model.to_dict()
        
        self.assertEqual(state["white_captured_pieces"], ["pawn", "knight"])
        self.assertEqual(state["black_captured_pieces"], ["rook"])

    def test_invalid_player_error(self):
        """Test that invalid player raises ValueError."""
        with self.assertRaises(ValueError):
            self.model.add_captured_piece("pawn", "invalid")

    def test_invalid_side_in_display(self):
        """Test that invalid side in display method raises ValueError."""
        with self.assertRaises(ValueError):
            self.model.get_pieces_to_display_for_side("invalid")

    def test_piece_order_preserved(self):
        """Test that piece order is preserved."""
        pieces = ["pawn", "knight", "bishop", "rook", "queen"]
        for piece in pieces:
            self.model.add_captured_piece(piece, "white")
        
        captured = self.model.get_captured_pieces("white")
        self.assertEqual(captured, pieces)


if __name__ == "__main__":
    unittest.main()
