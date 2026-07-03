"""Online match setup panel for the game mode overlay.

Provides three options for playing against another person:
    1. Create a room (WIP)
    2. Join a room with a code (WIP)
    3. Play in person on this device (local flip-board)
"""

from __future__ import annotations

import logging
from typing import Callable

import flet as ft

logger = logging.getLogger(__name__)


class OnlineSetupPanel(ft.Column):
    """Panel with three option cards for starting an online or local game."""

    def __init__(
        self,
        on_play_local: Callable[[], None] | None = None,
        on_create_room: Callable[[], None] | None = None,
        on_join_room: Callable[[str], None] | None = None,
    ):
        super().__init__(spacing=20, scroll=ft.ScrollMode.AUTO)
        self._on_play_local = on_play_local
        self._on_create_room = on_create_room
        self._on_join_room = on_join_room

        self._room_code_field = ft.TextField(
            label="Room code",
            hint_text="Enter room code to join",
            width=300,
        )

        self._join_button = ft.FilledButton(
            "Join Room",
            icon=ft.Icons.LOGIN,
            on_click=self._handle_join,
        )

        self._create_button = ft.FilledButton(
            "Create Room",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            on_click=self._handle_create,
        )

        self._local_button = ft.FilledButton(
            "Play in Person",
            icon=ft.Icons.PEOPLE,
            on_click=self._handle_local,
        )

        self._wip_snack = ft.SnackBar(
            content=ft.Text("Online play is not yet available.", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ORANGE_700,
            duration=3000,
            behavior=ft.SnackBarBehavior.FLOATING,
        )

        self.controls = [
            ft.Text(
                "Play Someone",
                weight=ft.FontWeight.BOLD,
                size=18,
            ),
            ft.Text(
                "Choose how you'd like to play against another person.",
                size=13,
                color=ft.Colors.GREY_400,
            ),
            ft.Divider(height=1),
            self._option_card(
                "Create a Room",
                "Generate a room code to share with your opponent.",
                ft.Icons.ADD_CIRCLE_OUTLINE,
                self._handle_create,
            ),
            ft.Container(
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("Or join an existing room:", size=13),
                        ft.Row(
                            spacing=8,
                            controls=[
                                self._room_code_field,
                                self._join_button,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                    ],
                ),
                padding=ft.Padding.all(16),
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=12,
            ),
            ft.Divider(height=1),
            self._option_card(
                "Play in Person",
                "Flip the board after each move — both players share this device.",
                ft.Icons.PEOPLE,
                self._handle_local,
            ),
        ]

    def _option_card(
        self,
        title: str,
        description: str,
        icon: ft.Icons,
        on_click: Callable | None,
    ) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.all(16),
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=12,
            ink=True,
            on_click=lambda _: on_click() if on_click else None,
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=32, color=ft.Colors.PRIMARY),
                    ft.Column(
                        spacing=4,
                        expand=True,
                        controls=[
                            ft.Text(title, weight=ft.FontWeight.BOLD, size=15),
                            ft.Text(description, size=12, color=ft.Colors.GREY_400),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_500),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _handle_create(self, _e=None) -> None:
        if self._on_create_room:
            self._on_create_room()
        else:
            self._show_wip()

    def _handle_join(self, _e=None) -> None:
        code = (self._room_code_field.value or "").strip()
        if not code:
            self._room_code_field.error_text = "Enter a room code"
            safe_update(self._room_code_field)
            return
        self._room_code_field.error_text = None
        if self._on_join_room:
            self._on_join_room(code)
        else:
            self._show_wip()

    def _handle_local(self, _e=None) -> None:
        if self._on_play_local:
            self._on_play_local()

    def _show_wip(self) -> None:
        try:
            page = self.page
            if page:
                page.show_dialog(self._wip_snack)
        except RuntimeError:
            logger.warning("Failed to show WIP snackbar", exc_info=True)


def safe_update(control: ft.Control) -> None:
    try:
        control.update()
    except RuntimeError:
        logger.debug("safe_update suppressed RuntimeError", exc_info=True)
