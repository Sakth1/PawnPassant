import flet as ft

from ui.chess_piece import ChessPiece
from ui.layout import AppLayout, resolve_app_layout
from ui.square import InvisibleSquare


class PieceDisplay(ft.Container):
    def __init__(self):
        super().__init__()
        self.layout = resolve_app_layout(960, 800)
        self.black_pieces = ft.Container(
            content=self._create_invisible_squares(),
        )
        self.white_pieces = ft.Container(
            content=self._create_invisible_squares(),
        )
        self.divider = ft.Container(
            height=3,
            bgcolor=ft.Colors.GREY_400,
            width=100,
            margin=ft.margin.Margin(20, 0, 20, 0),
        )
        self.content = ft.Row(
            controls=[self.black_pieces, self.divider, self.white_pieces],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _create_invisible_squares(self) -> list[InvisibleSquare]:
        """Create the board squares in top-to-bottom visual order."""

        self.squares: list[InvisibleSquare] = []
        self.square_map: dict[str, InvisibleSquare] = {}

        for i in range(16):
            coords = f"{i}"
            sq = InvisibleSquare(
                coordinate=coords,
                on_square_drop=self._handle_square_drop,
                on_piece_drag_start=self._handle_piece_drag_start,
                on_piece_drag_complete=self._handle_piece_drag_complete,
                size=60,
            )
            self.squares.append(sq)
            self.square_map[coords] = sq
        return self.squares

    def apply_layout(self, layout: AppLayout):
        pass  # TODO UI responsiveness

    def _handle_piece_drag_start(self, from_cords: str):
        """Show legal moves as soon as a draggable piece starts moving."""

        self._select_square(from_cords)

    def _handle_piece_drag_complete(self, from_cords: str):
        """Clear drag-only selection state when a drag ends without a move."""
        pass

    def _handle_square_drop(self, from_cords: str, to_cords: str):
        """Handle a piece being dropped onto a square."""

        if from_cords == to_cords:
            return

        self.move_piece(from_cords=from_cords, to_cords=to_cords)

    def _select_square(self, square_cords: str):
        """Select a piece square and reveal its current legal move targets."""
        self.selected_square = square_cords

    def _get_legal_targets(self) -> list[str]:
        """Collect legal destination coordinates for a piece on the given square."""
        return [str(i) for i in range(16)]

    def move_piece(self, from_cords: str, to_cords: str):
        """Create a move from board coordinates and dispatch it through the UI flow."""

        from_square = self.square_map[from_cords]
        to_square = self.square_map[to_cords]
        chess_piece = from_square.piece_container
        from_square.update_content(None)
        to_square.update_content(chess_piece)
