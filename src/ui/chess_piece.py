"""UI wrapper for rendering chess pieces as Flet controls.

The game state stores python-chess pieces, while the board needs Flet controls
with image assets, sizing, and small interaction animations. ``ChessPiece`` is
the adapter between those two worlds.
"""

import asyncio
import traceback
from pathlib import Path

import flet as ft
from chess import Color, Piece

from utils.constants import SYMBOL_MAP


class ChessPiece(ft.Container):
    """Represent a chess piece and know how to render its image asset."""

    def __init__(self, piece: Piece):
        super().__init__()
        #: Immutable python-chess piece identity carried by this UI wrapper.
        self.piece = piece
        #: Piece color cached for callers that need quick color checks.
        self.color: Color = piece.color
        self.alignment = ft.Alignment.CENTER
        #: Scale animation used by click feedback.
        self.animate_scale = ft.Animation(120, curve=ft.AnimationCurve.EASE_OUT)
        #: Current Flet scale value for transient piece feedback.
        self.scale = 1
        #: Board square size used to derive the rendered image dimensions.
        self.square_size = 60

    def to_control(self) -> ft.Control:
        """Build the Flet control used to display the piece on the board.

        Returns:
            This container with an image content, or a visible error text if the
            asset mapping cannot be resolved.
        """

        try:
            symbol = self.piece.symbol()
            piece_name = SYMBOL_MAP.get(symbol)
            # Flet asset paths are relative to the app asset directory, not the
            # Python module path.
            piece_src = Path("pieces", "default", f"{piece_name}.png").as_posix()
            image_size = max(20, int(self.square_size * 0.94))
            self.width = self.square_size
            self.height = self.square_size
            self.content = ft.Image(
                src=piece_src,
                width=image_size,
                height=image_size,
                gapless_playback=True,
            )
            return self
        except Exception:
            traceback.print_exc()
            return ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)

    def set_square_size(self, square_size: int):
        """Update piece rendering dimensions for responsive board layouts."""

        self.square_size = square_size
        if isinstance(self.content, ft.Image):
            image_size = max(20, int(self.square_size * 0.94))
            self.width = self.square_size
            self.height = self.square_size
            self.content.width = image_size
            self.content.height = image_size

    def _animate_click(self):
        """Temporarily enlarge the piece to acknowledge a direct click."""

        page = self.page
        self.scale = 1.5
        self.update()

        async def reset_scale():
            await asyncio.sleep(0.16)
            self.scale = 1
            self.update()

        page.run_task(reset_scale)
