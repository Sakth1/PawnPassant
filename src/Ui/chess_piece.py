"""UI wrapper for rendering chess pieces as Flet controls."""

import asyncio
import traceback
from pathlib import Path
import flet as ft
from chess import Piece, Color

from Constants import SYMBOL_MAP


class ChessPiece(ft.Container):
    """Represents a chess piece and knows how to render its image asset."""

    def __init__(self, piece: Piece):
        super().__init__()
        self.piece = piece
        self.color: Color = piece.color
        self.alignment = ft.Alignment.CENTER
        self.animate_scale = ft.Animation(120, curve=ft.AnimationCurve.EASE_OUT)
        self.scale = 1

    def to_control(self) -> ft.Control:
        """Build the Flet control used to display the piece on the board."""

        try:
            symbol = self.piece.symbol()
            piece_name = SYMBOL_MAP.get(symbol)
            piece_src = Path("pieces", "default", f"{piece_name}.png").as_posix()
            self.content = ft.Image(src=piece_src)
            return self
        except Exception:
            traceback.print_exc()
            return ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)

    def _animate_click(self):
        page = self.page
        self.scale = 1.5
        self.update()

        async def reset_scale():
            await asyncio.sleep(0.16)
            self.scale = 1
            self.update()

        page.run_task(reset_scale)
