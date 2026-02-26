import traceback
from typing import Optional

import flet as ft

from Ui.chess_piece import ChessPiece


class Square(ft.Container):
    def __init__(self, file, rank, coordinate, color, on_square_click=None, size=60):
        super().__init__(expand=True)
        self.file = file
        self.rank = rank
        self.coordinate = coordinate
        self.color = color
        self.on_square_click = on_square_click

        dot_size = size * 0.3
        ring_size = size * 0.8

        self.square_dot = ft.Container(
            width=dot_size,
            height=dot_size,
            border_radius=dot_size / 2,
            bgcolor=ft.Colors.BLACK_45,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.BLACK_45,
                offset=ft.Offset(0, 0),
            ),
        )

        self.square_ring = ft.Container(
            width=ring_size,
            height=ring_size,
            border_radius=ring_size / 2,
            border=ft.Border.all(3, ft.Colors.BLACK_54),
            bgcolor=ft.Colors.TRANSPARENT,
        )

        self.base_bgcolor = (
            ft.Colors.GREEN_100 if self.color == "w" else ft.Colors.GREEN_900
        )
        self.bgcolor = self.base_bgcolor
        self.width = size
        self.height = size
        self.piece_control: Optional[ft.Control] = None
        self.stack = ft.Stack(controls=[], expand=True, alignment=ft.Alignment.CENTER)
        self.content = self.stack
        self.highlighted_metadata: dict[str : bool | str | None] = {
            "highlighted": False,
            "parent_piece_square": None,
        }
        self.has_piece = False
        self.piece_container: Optional[ChessPiece] = None

        self.margin = 0
        self.on_click = self._handle_click
        self.on_hover = self._handle_hover

    def _handle_click(self, e):
        if self.on_square_click is not None:
            self.on_square_click(self, self.coordinate)

    def _handle_hover(self, e):
        # TODO: improve hovering mechanism, making it less hacky and heavy in UI
        if self.highlighted_metadata.get("highlighted"):
            return
        if e.data is True:
            self.bgcolor = ft.Colors.BLUE
        else:
            self.bgcolor = self.base_bgcolor
        self.update()

    def set_highlight(self, highlighted: bool, parent_piece_square=None):
        self.highlighted_metadata["highlighted"] = highlighted
        self.highlighted_metadata["parent_piece_square"] = parent_piece_square
        self._rebuild_stack()
        self.update()

    def update_content(self, piece: Optional[ChessPiece] = None):
        try:
            if piece is None:
                content = None
                self.has_piece = False
                self.piece_container = None
            elif isinstance(piece, ChessPiece):
                content = piece.to_control()
                self.piece_container = piece
                self.has_piece = True
            else:
                content = ft.Text(
                    "ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED
                )
                self.has_piece = False
                self.piece_container = None
        except Exception:
            traceback.print_exc()
            content = ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
        self.piece_control = content
        self._rebuild_stack()

    def _rebuild_stack(self):
        controls: list[ft.Control] = []
        if self.piece_control is not None:
            controls.append(self.piece_control)

        if self.highlighted_metadata.get("highlighted"):
            if self.piece_control is None:
                controls.append(self.square_dot)
            else:
                controls.append(self.square_ring)

        self.stack.controls = controls
