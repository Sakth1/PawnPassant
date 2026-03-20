"""UI wrapper for rendering chess pieces as Flet controls."""

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

    def to_control(self) -> ft.Control:
        """Build the Flet control used to display the piece on the board."""

        try:
            symbol = self.piece.symbol()
            piece_name = SYMBOL_MAP.get(symbol)
            piece_src = Path("pieces", "default", f"{piece_name}.png").as_posix()
            return ft.Image(src=piece_src)
        except Exception:
            traceback.print_exc()
            return ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
