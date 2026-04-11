"""Minimal square component for rendering captured pieces.

InvisibleSquare is a simplified version of Square tailored for displaying
captured pieces. It only includes essential methods:
- set_piece: place a piece on the square
- clear_piece: remove the piece
- get_piece: retrieve the current piece
- update_size: scale the square for responsive layout

Board-specific features like drag-drop, highlighting, and move validation
are intentionally excluded.
"""

from typing import Optional

import flet as ft

from ui.chess_piece import ChessPiece


class InvisibleSquare(ft.Container):
    """Minimal square for displaying captured pieces.
    
    Represents a non-interactive square designed specifically for the
    captured pieces display. Contains only a piece rendering area with
    no drag-drop, highlighting, or board interaction logic.
    """

    def __init__(self, size: int = 60):
        """Initialize an invisible square.
        
        Args:
            size: Width and height of the square in pixels
        """
        super().__init__(expand=True)
        self.size = size
        self.width = size
        self.height = size
        
        # Visual styling: slightly muted background for captured state
        self.bgcolor = ft.Colors.GREY_700
        self.border_radius = 4
        self.margin = 0
        self.padding = 0
        
        # Piece storage
        self.piece_container: Optional[ChessPiece] = None
        
        # Center alignment container for piece display
        self.stack = ft.Stack(controls=[], expand=True, alignment=ft.Alignment.CENTER)
        self.content = self.stack

    def set_piece(self, piece: ChessPiece) -> None:
        """Place a piece on this square.
        
        Args:
            piece: ChessPiece instance to display
        """
        self.piece_container = piece
        self.stack.controls.clear()
        if piece:
            self.stack.controls.append(piece)
        self._safe_update(self.stack)

    def clear_piece(self) -> None:
        """Remove the piece from this square."""
        self.piece_container = None
        self.stack.controls.clear()
        self._safe_update(self.stack)

    def get_piece(self) -> Optional[ChessPiece]:
        """Get the piece currently on this square.
        
        Returns:
            ChessPiece if one exists, None otherwise
        """
        return self.piece_container

    def update_size(self, size: int) -> None:
        """Update the square's size for responsive layout changes.
        
        Args:
            size: New width and height in pixels
        """
        self.size = size
        self.width = size
        self.height = size
        self._safe_update(self)
        if self.piece_container:
            # Piece may need scaling updates; delegate to piece's update_size if available
            if hasattr(self.piece_container, 'update_size'):
                self.piece_container.update_size(size)

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        """Safely update a control, handling page detach scenarios.
        
        Args:
            control: Flet control to update
        """
        try:
            control.update()
        except RuntimeError:
            # Control may have been detached from page
            pass
