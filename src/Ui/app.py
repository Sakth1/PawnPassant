import flet as ft

from Ui.board import ChessBoard


class ChessApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn Passant"
        self.board_view = ChessBoard()
        self.page.add(self.board_view)


def main(page: ft.Page):
    ChessApp(page)
