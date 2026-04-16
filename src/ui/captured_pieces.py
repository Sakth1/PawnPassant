import flet as ft
import random
from chess import PAWN, Piece

from ui.chess_piece import ChessPiece
from ui.layout import AppLayout, resolve_app_layout
from ui.square import InvisibleSquare
from utils.events import PieceCapturedEvent
from utils.models import ActiveColor
from utils.signals import bus


class CaputredPieces(ft.Container):
    def __init__(self):
        super().__init__()
        self.layout = resolve_app_layout(960, 800)
        self.bgcolor = "#1F1F1F"
        self.border_radius = 16
        self.padding = 12
        self.alignment = ft.Alignment.CENTER

        self.black_squares: list[InvisibleSquare] = self._create_invisible_squares("b")
        self.white_squares: list[InvisibleSquare] = self._create_invisible_squares("w")
        self.available_white_squares: list[int] = list(range(16))
        self.available_black_squares: list[int] = list(range(16))
        self.black_grid: ft.GridView = self._build_square_grid(self.black_squares)
        self.white_grid: ft.GridView = self._build_square_grid(self.white_squares)
        self.divider = ft.Container(
            height=1,
            bgcolor=ft.Colors.WHITE_24,
        )
        self.content = ft.Column(
            controls=[
                self.black_grid,
                self.divider,
                self.white_grid,
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )
        bus.connect(
            PieceCapturedEvent, lambda event: self._handle_piece_captured(event)
        )
        self.apply_layout(self.layout)

    def _create_invisible_squares(self, prefix: str) -> list[InvisibleSquare]:
        squares: list[InvisibleSquare] = []
        for i in range(16):
            squares.append(
                InvisibleSquare(
                    coordinate=f"{prefix}{i}",
                    on_square_drop=self._handle_square_drop,
                    on_piece_drag_start=self._handle_piece_drag_start,
                    on_piece_drag_complete=self._handle_piece_drag_complete,
                    size=60,
                )
            )
        return squares

    def _build_square_grid(self, squares: list[InvisibleSquare]) -> ft.GridView:
        for sq in squares:
            sq.update_content(f"{sq.coordinate}")

        return ft.GridView(
            runs_count=4,
            controls=squares,
            expand=False,
            spacing=4,
            run_spacing=4,
            padding=4,
        )

        """for row_start in range(0, len(squares), 8):
            rows.append(
                ft.Row(
                    controls=squares[row_start : row_start + 8],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return ft.Column(
            controls=rows,
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        )"""

    def apply_layout(self, layout: AppLayout):
        self.layout = layout
        self.width = layout.piece_panel_width
        self.padding = max(8, int(layout.gap * 0.75))
        self.border_radius = max(12, int(layout.timer_radius * 0.8))

        # Use same square size as main board
        capture_square_size = layout.board_square_size * 0.97
        for square in self.black_squares + self.white_squares:
            square.apply_size(capture_square_size)

        # Use 4x4 grid layout for captured pieces
        grid_spacing = max(4, int(layout.gap * 0.35))
        runs_count = 4

        for grid in (self.black_grid, self.white_grid):
            grid.runs_count = runs_count
            grid.spacing = grid_spacing
            grid.run_spacing = grid_spacing

        self.divider.width = max(80, int(layout.piece_panel_width * 0.72))
        self.content.spacing = max(10, int(layout.gap * 0.65))
        self._safe_update(self)

    def _get_random_available_position(self, is_white_capture: ActiveColor):
        available_squares: list[int] = (
            self.available_white_squares
            if is_white_capture
            else self.available_black_squares
        )
        return random.choice(available_squares)

    def _handle_piece_captured(self, event: PieceCapturedEvent):
        is_white_capture: ActiveColor = event.color
        random_available_pos: int = self._get_random_available_position(
            is_white_capture
        )
        if is_white_capture:
            self.white_squares[random_available_pos].update_content(event.piece)
        else:
            self.black_squares[random_available_pos].update_content(event.piece)

        self._safe_update(self)

    def _handle_piece_drag_start(self, _from_cords: str):
        pass

    def _handle_piece_drag_complete(self, _from_cords: str):
        pass

    def _handle_square_drop(self, from_cords: str, to_cords: str):
        if from_cords == to_cords:
            return
        self.move_piece(from_cords=from_cords, to_cords=to_cords)

    def move_piece(self, from_cords: str, to_cords: str):
        source_square = self._find_square(from_cords)
        target_square = self._find_square(to_cords)
        if source_square is None or target_square is None:
            return

        chess_piece = source_square.piece_container
        source_square.update_content(None)
        target_square.update_content(chess_piece)

    def _find_square(self, coordinate: str) -> InvisibleSquare | None:
        for square in self.black_squares + self.white_squares:
            if square.coordinate == coordinate:
                return square
        return None

    @staticmethod
    def _safe_update(control: ft.Control):
        try:
            control.update()
        except RuntimeError:
            pass
