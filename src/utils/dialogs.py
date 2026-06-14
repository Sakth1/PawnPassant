"""Reusable alert/message-box dialog helpers for Pawn Passant."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft


def show_alert_dialog(
    page: ft.Page,
    title: str,
    message: str,
    button_text: str = "OK",
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Show a modal info dialog with a single action button."""
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, weight=ft.FontWeight.BOLD),
        content=ft.Text(message, text_align=ft.TextAlign.CENTER),
        actions=[
            ft.TextButton(
                button_text,
                on_click=lambda _: _handle_alert_close(page, on_close),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.show_dialog(dialog)
    safe_update(page)


def _handle_alert_close(page: ft.Page, on_close: Optional[Callable]) -> None:
    safe_pop_dialog(page)
    if on_close is not None:
        on_close()


def safe_pop_dialog(page: ft.Page) -> None:
    """Close the topmost dialog while tolerating detached-control errors."""
    try:
        page.pop_dialog()
    except (IndexError, RuntimeError):
        pass


def safe_update(control: ft.Control) -> None:
    """Update a Flet control while tolerating detached-control errors."""
    try:
        control.update()
    except RuntimeError:
        pass
