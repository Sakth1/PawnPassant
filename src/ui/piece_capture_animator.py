"""Coordinator for captured piece animations.

Handles the animation of pieces flowing from the board to the captured pieces UI.
Animation paths and targets vary based on the current layout type.
"""

import asyncio
from typing import Callable, Optional

import flet as ft

from ui.layout_templates import LayoutType


class PieceCaptureAnimator:
    """Coordinates animations when pieces are captured.
    
    Animates a piece from its source square on the board to its destination
    in the captured pieces display. The animation path and target position
    depend on the current layout type (desktop, tablet, mobile).
    """

    CAPTURE_ANIMATION_DURATION_MS = 200  # Slower than standard move (120ms)
    ANIMATION_CURVE = ft.AnimationCurve.EASE_IN_OUT

    def __init__(self):
        """Initialize the animator."""
        self.is_animating = False

    async def animate_captured_piece(
        self,
        piece_control: ft.Control,
        source_position: tuple[float, float],
        target_position: tuple[float, float],
        layout_type: LayoutType = "desktop",
        on_animation_complete: Optional[Callable] = None,
    ) -> None:
        """Animate a piece from board to captured area.

        Args:
            piece_control: The Flet control representing the piece
            source_position: (left, top) position on the board
            target_position: (left, top) position in the captured area
            layout_type: Current layout ("desktop", "tablet", "mobile")
            on_animation_complete: Callback when animation finishes

        The animation uses overlay-based positioning (Stack with absolute positioning).
        """
        self.is_animating = True
        try:
            # Store original position
            original_left = piece_control.left
            original_top = piece_control.top

            # Start at source
            piece_control.left = source_position[0]
            piece_control.top = source_position[1]

            # Configure animation
            piece_control.animate_position = ft.Animation(
                self.CAPTURE_ANIMATION_DURATION_MS,
                curve=self.ANIMATION_CURVE,
            )

            # Move to target
            piece_control.left = target_position[0]
            piece_control.top = target_position[1]

            # Wait for animation to complete
            await asyncio.sleep(self.CAPTURE_ANIMATION_DURATION_MS / 1000.0)

            # Cleanup
            piece_control.animate_position = None

            if on_animation_complete:
                on_animation_complete()

        finally:
            self.is_animating = False

    def calculate_capture_target(
        self,
        board_position: tuple[float, float],
        captured_by: str,
        layout_type: LayoutType,
        viewport_metrics: dict,
    ) -> tuple[float, float]:
        """Calculate target position for a captured piece based on layout.

        Args:
            board_position: Current position of piece on board
            captured_by: Player who captured ("white" or "black")
            layout_type: Current layout type
            viewport_metrics: Dict with positioning info:
                - "board_left", "board_top": board offset
                - "captured_area_left/top": captured pieces area offset
                - "piece_size": size of piece sprite

        Returns:
            Target (left, top) coordinates in viewport coordinates
        """
        if layout_type == "desktop":
            return self._calculate_desktop_target(
                board_position, captured_by, viewport_metrics
            )
        elif layout_type == "tablet":
            return self._calculate_tablet_target(
                board_position, captured_by, viewport_metrics
            )
        elif layout_type == "mobile":
            return self._calculate_mobile_target(
                board_position, captured_by, viewport_metrics
            )
        else:
            raise ValueError(f"Unknown layout type: {layout_type}")

    @staticmethod
    def _calculate_desktop_target(
        board_position: tuple[float, float],
        captured_by: str,
        viewport_metrics: dict,
    ) -> tuple[float, float]:
        """Desktop: captured area is to the left of the board.
        
        Pieces flow from board center-left to captured area on the left side.
        """
        captured_left = viewport_metrics.get("captured_area_left", 20)
        captured_top = viewport_metrics.get("captured_area_top", 20)

        # All pieces target the center of the captured pieces area
        target_left = captured_left + viewport_metrics.get("captured_area_width", 100) / 2
        target_top = captured_top + viewport_metrics.get("captured_area_height", 100) / 2

        return (target_left, target_top)

    @staticmethod
    def _calculate_tablet_target(
        board_position: tuple[float, float],
        captured_by: str,
        viewport_metrics: dict,
    ) -> tuple[float, float]:
        """Tablet: similar to desktop but tighter spacing.
        
        Captured area is to the right of board but closer than desktop layout.
        """
        # Tablet is a refinement of desktop
        return PieceCaptureAnimator._calculate_desktop_target(
            board_position, captured_by, viewport_metrics
        )

    @staticmethod
    def _calculate_mobile_target(
        board_position: tuple[float, float],
        captured_by: str,
        viewport_metrics: dict,
    ) -> tuple[float, float]:
        """Mobile: captured area depends on piece ownership.
        
        Pieces captured by black flow upward (opponent above board).
        Pieces captured by white flow downward (current player below board).
        """
        if captured_by == "white":
            # Current player captures: pieces flow down
            target_left = viewport_metrics.get("board_left", 20)
            target_top = viewport_metrics.get("current_captured_area_top", 300)
        else:
            # Opponent captures: pieces flow up
            target_left = viewport_metrics.get("board_left", 20)
            target_top = viewport_metrics.get("opponent_captured_area_top", 20)

        return (target_left, target_top)

    def get_animation_duration_ms(self) -> int:
        """Get the capture animation duration in milliseconds."""
        return self.CAPTURE_ANIMATION_DURATION_MS
