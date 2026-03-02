import json
import os
import flet as ft

from Ui.board import ChessBoard


class ChessApp:
    def __init__(self, page: ft.Page, dev_mode: bool = False):
        self.page = page
        self.page.title = "Pawn Passant"
        self.board_view = ChessBoard()
        self.main_page_view = ft.Row(alignment=ft.MainAxisAlignment.CENTER, expand=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.dev_mode = dev_mode

        if self.dev_mode:
            self.position_selector = ft.Dropdown(
                label="Board setup",
                width=280,
                value="Start Position",
                options=[
                    ft.dropdown.Option(key=position_name, text=position_name)
                    for position_name in ChessBoard.TEST_POSITIONS.keys()
                ],
                on_select=self._handle_position_change,
                on_text_change=self._handle_position_change,
            )
            self.main_page_view.controls = [ft.Row([self.position_selector]), self.board_view]
        else:
            self.main_page_view.controls = self.board_view

        self.page.add(self.main_page_view)

    def _handle_position_change(self, e: ft.ControlEvent):
        selected_name = None

        if isinstance(e.data, str) and e.data:
            payload = e.data.strip()
            if payload.startswith("{"):
                try:
                    event_data = json.loads(payload)
                    selected_name = event_data.get("value") or event_data.get("key")
                except json.JSONDecodeError:
                    selected_name = payload
            else:
                selected_name = payload

        if not selected_name:
            selected_name = e.control.value or self.position_selector.value

        if isinstance(selected_name, str):
            selected_name = selected_name.strip()

        if selected_name not in ChessBoard.TEST_POSITIONS:
            return

        self.position_selector.value = selected_name
        selected_fen = ChessBoard.TEST_POSITIONS[selected_name]
        self.board_view.load_position(selected_fen)


def main(page: ft.Page):
    dev_mode = os.getenv("PAWNPASSANT_DEV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "dev",
    }

    ChessApp(page, dev_mode=dev_mode)
