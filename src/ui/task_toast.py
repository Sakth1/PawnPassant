"""Reusable toast notification for transient background-task feedback.

Wraps ``ft.SnackBar`` with consistent styling and auto-dismiss behavior.
"""

from __future__ import annotations

import flet as ft


def show_toast(
    page: ft.Page,
    message: str,
    duration_seconds: int = 4,
    is_error: bool = False,
) -> None:
    """Display a non-blocking snackbar notification.

    Args:
        page: The Flet page to show the snackbar on.
        message: The text to display.
        duration_seconds: Auto-dismiss timeout (default 4s).
        is_error: If ``True``, use error styling (red background).
    """
    snackbar = ft.SnackBar(
        content=ft.Text(message, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700,
        duration=duration_seconds * 1000,
        behavior=ft.SnackBarBehavior.FLOATING,
    )
    page.show_snack_bar(snackbar)
