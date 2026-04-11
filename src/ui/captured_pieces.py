import flet as ft

from . import chess_piece
from ui.layout import AppLayout, resolve_app_layout


class PieceDisplay(ft.Container):
    def __init__(self):
        super().__init__()
        self.layout = "" #TODO
        self.black_pieces = ft.Container()
        self.white_pieces = ft.Container()
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

    def apply_layout(self, layout: AppLayout):
        pass #TODO UI responsiveness
