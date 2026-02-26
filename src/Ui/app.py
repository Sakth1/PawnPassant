import os
import flet as ft

from Ui.board import ChessBoard


class ChessApp:
    def __init__(self, page: ft.Page, dev_mode: bool = False):
        self.page = page
        self.page.title = "Pawn Passant"
        self.board_view = ChessBoard()
        self.dev_mode = dev_mode

        if self.dev_mode:
            self.position_selector = ft.Dropdown(
                label="Board setup",
                width=280,
                value="Start Position",
                options=[
                    ft.dropdown.Option(position_name)
                    for position_name in ChessBoard.TEST_POSITIONS.keys()
                ],
                on_select=self._handle_position_change,
            )
            self.page.add(ft.Row([self.position_selector]), self.board_view)
        else:
            self.page.add(self.board_view)

    def _handle_position_change(self, e: ft.ControlEvent):
        selected_name = e.control.value
        selected_fen = ChessBoard.TEST_POSITIONS.get(selected_name)
        self.board_view.load_position(selected_fen)


def main(page: ft.Page):
    dev_mode = os.getenv("PAWNPASSANT_DEV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "dev",
    }
    #  $env:PAWNPASSANT_DEV = "true"    # to run in dev mode
    #  Remove-Item Env:PAWNPASSANT_DEV  # to run in prod mode
    ChessApp(page, dev_mode=dev_mode)
