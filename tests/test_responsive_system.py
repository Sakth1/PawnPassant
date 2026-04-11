"""Integration tests for the new UI responsiveness system."""

import unittest
from src.utils.captured_pieces_model import CapturedPiecesModel
from src.ui.layout_templates import get_layout_template, DesktopLayout, TabletLayout, MobileLayout
from src.ui.layout import AppLayout, resolve_app_layout


class TestCapturedPiecesModel(unittest.TestCase):
    """Test captured pieces state management."""

    def setUp(self):
        self.model = CapturedPiecesModel()

    def test_add_and_retrieve_white_captures(self):
        """Test adding pieces captured by white."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "white")
        
        pieces = self.model.get_captured_pieces("white")
        self.assertEqual(pieces, ["pawn", "knight"])

    def test_ownership_reversal_display(self):
        """Test that captured pieces are displayed on opposite side."""
        self.model.add_captured_piece("pawn", "white")  # White captured pawn
        self.model.add_captured_piece("knight", "black")  # Black captured knight
        
        # White's captures appear on black side
        black_side_display = self.model.get_pieces_to_display_for_side("black")
        self.assertIn("pawn", black_side_display)
        self.assertNotIn("knight", black_side_display)
        
        # Black's captures appear on white side
        white_side_display = self.model.get_pieces_to_display_for_side("white")
        self.assertIn("knight", white_side_display)
        self.assertNotIn("pawn", white_side_display)

    def test_clear_pieces(self):
        """Test clearing all captured pieces."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "black")
        self.model.clear()
        
        self.assertEqual(self.model.white_captured_pieces, [])
        self.assertEqual(self.model.black_captured_pieces, [])

    def test_to_dict_export(self):
        """Test model state export."""
        self.model.add_captured_piece("pawn", "white")
        self.model.add_captured_piece("knight", "black")
        
        state = self.model.to_dict()
        self.assertEqual(state["white_captured_pieces"], ["pawn"])
        self.assertEqual(state["black_captured_pieces"], ["knight"])


class TestLayoutTemplates(unittest.TestCase):
    """Test layout template system."""

    def test_get_layout_template_desktop(self):
        """Test retrieving desktop layout template."""
        template = get_layout_template("desktop")
        self.assertIsInstance(template, DesktopLayout)
        self.assertEqual(template.get_layout_type(), "desktop")

    def test_get_layout_template_tablet(self):
        """Test retrieving tablet layout template."""
        template = get_layout_template("tablet")
        self.assertIsInstance(template, TabletLayout)
        self.assertEqual(template.get_layout_type(), "tablet")

    def test_get_layout_template_mobile(self):
        """Test retrieving mobile layout template."""
        template = get_layout_template("mobile")
        self.assertIsInstance(template, MobileLayout)
        self.assertEqual(template.get_layout_type(), "mobile")

    def test_desktop_config(self):
        """Test desktop layout configuration."""
        template = DesktopLayout()
        config = template.get_config()
        
        self.assertEqual(config.layout_type, "desktop")
        self.assertEqual(config.clock_mode, "combined")
        self.assertEqual(config.captured_pieces_grid_shape, (4, 4))
        self.assertFalse(config.is_stacked)

    def test_mobile_config(self):
        """Test mobile layout configuration."""
        template = MobileLayout()
        config = template.get_config()
        
        self.assertEqual(config.layout_type, "mobile")
        self.assertEqual(config.clock_mode, "split")
        self.assertEqual(config.captured_pieces_grid_shape, (2, 8))
        self.assertTrue(config.is_stacked)


class TestLayoutResolver(unittest.TestCase):
    """Test responsive layout resolution."""

    def test_resolve_mobile_layout(self):
        """Test mobile layout detection."""
        layout = resolve_app_layout(600, 800)
        self.assertEqual(layout.layout_type, "mobile")
        self.assertEqual(layout.breakpoint, "mobile")

    def test_resolve_tablet_layout(self):
        """Test tablet layout detection."""
        layout = resolve_app_layout(900, 800)
        self.assertEqual(layout.layout_type, "tablet")
        self.assertEqual(layout.breakpoint, "tablet")

    def test_resolve_desktop_layout(self):
        """Test desktop layout detection."""
        layout = resolve_app_layout(1400, 800)
        self.assertEqual(layout.layout_type, "desktop")
        self.assertEqual(layout.breakpoint, "desktop")

    def test_layout_template_is_set(self):
        """Test that layout template is included in AppLayout."""
        layout = resolve_app_layout(1400, 800)
        self.assertIsNotNone(layout.layout_template)
        self.assertEqual(layout.layout_template.get_layout_type(), "desktop")


if __name__ == "__main__":
    unittest.main()
