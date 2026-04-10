"""Top-level application wiring for the Pawn Passant interface."""

import json
import os
import flet as ft
from pathlib import Path

from ui.board import ChessBoard
from ui.time_control import ClockUI
from utils.constants import ASSET_DIR


class ChessApp:
    """Builds the page layout and optional developer controls."""

    def __init__(self, page: ft.Page, dev_mode: bool = False):
        self.page = page
        self.page.title = "Pawn Passant"
        self.page.window.icon = str(Path(ASSET_DIR, "PawnPassant.ico"))
        self.board_view = ChessBoard()
        self.time_control_view = ClockUI()
        self.main_page_view = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
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
            self.main_page_view.controls = [
                ft.Column(
                    controls=[
                        self.position_selector,
                        ft.Row(
                            controls=[
                                self.board_view,
                                self.time_control_view,
                            ],
                            tight=True,
                            spacing=12,
                            alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    tight=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ]
        else:
            self.main_page_view.controls = self.board_view

        self.page.add(self.main_page_view)
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.PURPLE)

    def _handle_position_change(self, e: ft.ControlEvent):
        """Load a canned board position selected from the developer dropdown."""

        selected_name = None

        if isinstance(e.data, str) and e.data:
            payload = e.data.strip()
            # Flet events can arrive as either raw strings or a JSON payload.
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
    """Create the app with dev-mode controls toggled by environment variable."""

    dev_mode = os.getenv("PAWNPASSANT_DEV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "dev",
    }

    ChessApp(page, dev_mode=dev_mode)
