"""Captured pieces display components.

Supports three layout variants:
- Desktop: Combined 4×4 grid (black top, white bottom)
- Tablet: Inherits from desktop with optimized spacing
- Mobile: Split 2×8 grids (opponent above, current player below)
"""

from abc import ABC, abstractmethod
from typing import Optional

import flet as ft

from ui.chess_piece import ChessPiece
from ui.invisible_square import InvisibleSquare
from ui.layout import AppLayout
from ui.layout_templates import LayoutTemplate
from utils.captured_pieces_model import CapturedPiecesModel


class PieceDisplayBase(ft.Container, ABC):
    """Abstract base class for captured pieces display.
    
    All layout variants inherit from this base to share:
    - State management (CapturedPiecesModel)
    - Event subscription logic
    - Animation coordination
    - Common render patterns
    """

    def __init__(self):
        """Initialize the base captured pieces display."""
        super().__init__()
        
        self.model = CapturedPiecesModel()
        self.layout: Optional[AppLayout] = None
        self.template: Optional[LayoutTemplate] = None
        
        # Piece controls for animation
        self.piece_squares: dict[str, InvisibleSquare] = {}  # Maps piece_id to InvisibleSquare
        
        # Subscribe to relevant events
        self._subscribe_to_events()

    def _subscribe_to_events(self) -> None:
        """Subscribe to game and layout events."""
        from utils.events import (
            GameStartedEvent,
            PieceCapturedEvent,
            CapturedPiecesUpdatedEvent,
        )
        from utils.signals import bus

        bus.connect(GameStartedEvent, self._on_game_started)
        bus.connect(PieceCapturedEvent, self._on_piece_captured)
        bus.connect(CapturedPiecesUpdatedEvent, self._on_captured_pieces_updated)

    def _on_game_started(self, event) -> None:
        """Clear captured pieces when a new game starts."""
        self.model.clear()
        self._render()

    def _on_piece_captured(self, event) -> None:
        """Handle piece capture event."""
        self.model.add_captured_piece(event.piece_type, event.captured_by)
        self._on_captured_pieces_updated(None)

    def _on_captured_pieces_updated(self, event) -> None:
        """Re-render captured pieces display when model updates."""
        self._render()

    def apply_layout(self, layout: AppLayout) -> None:
        """Apply responsive layout metrics.
        
        Args:
            layout: Resolved AppLayout with current metrics
        """
        self.layout = layout
        self.template = layout.layout_template
        self._render()

    def _render(self) -> None:
        """Render the appropriate layout based on current template.
        
        Templated method that delegates to subclass implementation.
        """
        if self.template is None or self.layout is None:
            return
        
        try:
            self._render_layout()
            self._safe_update(self)
        except Exception as e:
            print(f"Error rendering captured pieces: {e}")

    @abstractmethod
    def _render_layout(self) -> None:
        """Render components for this layout variant.
        
        Subclasses implement this to arrange captured pieces according
        to their layout strategy.
        """
        pass

    def _create_piece_grid(
        self,
        pieces: list[str],
        side: str,
        rows: int,
        cols: int,
        square_size: int,
    ) -> ft.Container:
        """Create a grid of captured pieces.
        
        Args:
            pieces: List of piece type strings
            side: Which side to display on ("white" or "black")
            rows: Number of rows in the grid
            cols: Number of columns in the grid
            square_size: Size of each square in pixels
            
        Returns:
            Flet Container with piece grid
        """
        # Create grid layout with appropriate size
        grid_controls = []
        
        # Limit pieces to grid capacity
        max_pieces = rows * cols
        displayed_pieces = pieces[:max_pieces]
        
        # Create squares for each piece
        for i, piece_type in enumerate(displayed_pieces):
            square = InvisibleSquare(size=square_size)
            
            # Create and show the piece
            piece = ChessPiece(piece_type, side, square_size)
            square.set_piece(piece)
            
            grid_controls.append(square)
        
        # Fill remaining squares as empty
        for i in range(len(displayed_pieces), max_pieces):
            square = InvisibleSquare(size=square_size)
            grid_controls.append(square)
        
        # Wrap in a scrollable container if needed
        wrap = ft.Wrap(
            controls=grid_controls,
            spacing=4,
            run_spacing=4,
        )
        
        return ft.Container(
            content=wrap,
            padding=8,
            border_radius=6,
            bgcolor=ft.Colors.GREY_800,
        )

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        """Safely update a control, handling page detach scenarios."""
        try:
            control.update()
        except RuntimeError:
            pass


class DesktopCapturedPiecesDisplay(PieceDisplayBase):
    """Desktop layout: combined 4×4 grid display.
    
    Layout:
    - Left side component: black pieces (top), white pieces (bottom)
    - Horizontal arrangement in ResponsiveRow
    - Non-scrollable fixed grid
    
    Ownership:
    - Black's captured pieces (white's pieces) displayed on white side
    - White's captured pieces (black's pieces) displayed on black side
    """

    def __init__(self):
        """Initialize desktop captured pieces display."""
        super().__init__()
        self.square_size = 60
        self.black_display_container: Optional[ft.Container] = None
        self.white_display_container: Optional[ft.Container] = None

    def _render_layout(self) -> None:
        """Render desktop layout: combined vertical stack."""
        if not self.layout:
            return
        
        # Use board square size to scale piece display
        self.square_size = max(20, int(self.layout.board_square_size * 0.5))
        
        # Get pieces to display on each side
        # Note: ownership is reversed (black's captured pieces on white's side)
        white_side_pieces = self.model.get_pieces_to_display_for_side("white")
        black_side_pieces = self.model.get_pieces_to_display_for_side("black")
        
        # Create grids
        black_grid = self._create_piece_grid(
            black_side_pieces,
            "black",
            rows=4,
            cols=4,
            square_size=self.square_size,
        )
        
        white_grid = self._create_piece_grid(
            white_side_pieces,
            "white",
            rows=4,
            cols=4,
            square_size=self.square_size,
        )
        
        # Create divider
        divider = ft.Container(
            height=2,
            bgcolor=ft.Colors.GREY_600,
            width=self.square_size * 4 + 16,
            margin=ft.margin.Margin(0, 8, 0, 8),
        )
        
        # Vertical stack: black (top) - divider - white (bottom)
        self.content = ft.Column(
            controls=[black_grid, divider, white_grid],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            tight=True,
        )


class TabletCapturedPiecesDisplay(DesktopCapturedPiecesDisplay):
    """Tablet layout: inherits from desktop with optimized spacing.
    
    Tablet uses the same UI structure as desktop (combined grid) but with
    slightly adjusted metrics for medium-sized screens.
    """

    def _render_layout(self) -> None:
        """Render tablet layout with optimized spacing."""
        # Slightly more compact than desktop
        if not self.layout:
            return
        
        self.square_size = max(18, int(self.layout.board_square_size * 0.45))
        
        # Otherwise identical to desktop
        super()._render_layout()


class MobileCapturedPiecesDisplay(PieceDisplayBase):
    """Mobile layout: split captured pieces display.
    
    Layout:
    - Opponent's captured pieces above the board (2×8 grid, scrollable)
    - Current player's captured pieces below the board (2×8 grid, scrollable)
    - Clock split into corners (handled separately in ClockUI)
    
    Board is the primary focus and fills most of the viewport.
    """

    def __init__(self):
        """Initialize mobile captured pieces display."""
        super().__init__()
        self.square_size = 40
        self.opponent_container: Optional[ft.Container] = None
        self.current_player_container: Optional[ft.Container] = None

    def _render_layout(self) -> None:
        """Render mobile layout: split vertical sections."""
        if not self.layout:
            return
        
        self.square_size = max(15, int(self.layout.board_square_size * 0.3))
        
        # On mobile, we don't have a direct way to know "current player"
        # So we display both sides: opponent pieces above, white pieces below
        # This will be refined once board state is integrated
        opponent_pieces = self.model.get_pieces_to_display_for_side("black")
        current_pieces = self.model.get_pieces_to_display_for_side("white")
        
        # Create grids: 2 rows x 8 cols each
        opponent_grid = self._create_piece_grid(
            opponent_pieces,
            "black",
            rows=2,
            cols=8,
            square_size=self.square_size,
        )
        
        current_grid = self._create_piece_grid(
            current_pieces,
            "white",
            rows=2,
            cols=8,
            square_size=self.square_size,
        )
        
        # Wrapping in scrollable containers for very small screens
        opponent_section = ft.Container(
            content=opponent_grid,
            height=self.square_size * 2 + 16,
            margin=ft.margin.Margin(0, 4, 0, 4),
        )
        
        current_section = ft.Container(
            content=current_grid,
            height=self.square_size * 2 + 16,
            margin=ft.margin.Margin(0, 4, 0, 4),
        )
        
        # Note: actual board positioning is handled by main app layout
        # These containers are for reference; main app will compose the full layout
        self.opponent_container = opponent_section
        self.current_player_container = current_section
        
        # Show only a label for now; actual layout integration in app.py
        self.content = ft.Column(
            controls=[opponent_section, current_section],
            spacing=4,
        )


# Factory function for layout-agnostic instantiation
def create_captured_pieces_display(layout_type: str) -> PieceDisplayBase:
    """Create appropriate captured pieces display for layout type.
    
    Args:
        layout_type: One of "desktop", "tablet", "mobile"
        
    Returns:
        Appropriate PieceDisplayBase subclass instance
    """
    if layout_type == "desktop":
        return DesktopCapturedPiecesDisplay()
    elif layout_type == "tablet":
        return TabletCapturedPiecesDisplay()
    elif layout_type == "mobile":
        return MobileCapturedPiecesDisplay()
    else:
        raise ValueError(f"Unknown layout type: {layout_type}")


# Legacy wrapper for backward compatibility during transition
class PieceDisplay(DesktopCapturedPiecesDisplay):
    """Legacy class name for backward compatibility."""
    pass
