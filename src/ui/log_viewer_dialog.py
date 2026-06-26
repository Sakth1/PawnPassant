"""In-app log viewer overlay with severity filtering and clipboard export."""

from __future__ import annotations

import logging
from typing import Callable

import flet as ft

from utils.dialogs import safe_update
from utils.log_collector import (
    build_error_report,
    read_recent_logs,
)
from ui.task_toast import show_toast  # kept for the no-entries edge case

logger = logging.getLogger(__name__)

#: Colour mapping by severity level.
_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": ft.Colors.GREY_500,
    "INFO": ft.Colors.ON_SURFACE,
    "WARNING": ft.Colors.AMBER_400,
    "ERROR": ft.Colors.RED_400,
    "CRITICAL": ft.Colors.RED_700,
}

_LEVEL_WEIGHTS: dict[str, int] = {
    "DEBUG": ft.FontWeight.NORMAL,
    "INFO": ft.FontWeight.NORMAL,
    "WARNING": ft.FontWeight.W_500,
    "ERROR": ft.FontWeight.W_600,
    "CRITICAL": ft.FontWeight.BOLD,
}

_LEVEL_OPTIONS = [
    ft.dropdown.Option("", "All levels"),
    ft.dropdown.Option("DEBUG"),
    ft.dropdown.Option("INFO"),
    ft.dropdown.Option("WARNING"),
    ft.dropdown.Option("ERROR"),
    ft.dropdown.Option("CRITICAL"),
]

_LINE_COUNT_OPTIONS = [
    ft.dropdown.Option("50"),
    ft.dropdown.Option("100"),
    ft.dropdown.Option("200"),
    ft.dropdown.Option("500"),
]


class LogViewerDialog(ft.Container):
    """A full-screen modal overlay that displays recent application logs.

    Users can filter by severity level, refresh the view, and copy the log
    content to the system clipboard.
    """

    def __init__(
        self,
        page: ft.Page,
        on_close: Callable[[], None] | None = None,
    ):
        super().__init__(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
            alignment=ft.Alignment.CENTER,
        )
        self._page = page
        self._on_close = on_close

        # ── Level filter ────────────────────────────────────────────────
        self._level_filter = ft.Dropdown(
            value="",
            label="Level",
            options=_LEVEL_OPTIONS,
            width=140,
            on_select=self._refresh,
        )
        self._line_count = ft.Dropdown(
            value="200",
            label="Lines",
            options=_LINE_COUNT_OPTIONS,
            width=100,
            on_select=self._refresh,
        )
        self._refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Refresh logs",
            on_click=self._refresh,
        )

        # ── Log entries container (filled by _refresh) ──────────────────
        self._log_list = ft.Column(
            spacing=2,
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,
        )

        # ── Buttons ─────────────────────────────────────────────────────
        self._copy_report_button = ft.FilledButton(
            "Copy Full Report",
            icon=ft.Icons.COPY,
            on_click=self._handle_copy_report,
        )
        self._copy_recent_button = ft.OutlinedButton(
            "Copy Recent 50",
            icon=ft.Icons.COPY,
            on_click=self._handle_copy_recent,
        )
        self._close_button = ft.TextButton(
            "Close",
            icon=ft.Icons.CLOSE,
            on_click=self._handle_close,
        )

        # ── Panel layout ────────────────────────────────────────────────
        panel = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.97, ft.Colors.GREY_900),
            border_radius=16,
            padding=ft.Padding.all(24),
            width=min(page.width * 0.9, 800) if page.width else 640,
            height=min(page.height * 0.85, 600) if page.height else 500,
            content=ft.Column(
                spacing=12,
                controls=[
                    self._header_row(),
                    self._toolbar_row(),
                    ft.Divider(height=1),
                    ft.Container(
                        content=self._log_list,
                        expand=True,
                        border=ft.Border.all(
                            1, ft.Colors.OUTLINE_VARIANT,
                        ),
                        border_radius=8,
                        padding=ft.Padding.all(8),
                    ),
                    ft.Divider(height=1),
                    self._button_row(),
                ],
            ),
        )

        self.content = panel
        self._refresh()

    def open(self) -> None:
        """Add this overlay to the page's overlay stack."""
        if self not in self._page.overlay:
            self.visible = True
            self._page.overlay.append(self)
            self._page.update()
            self._refresh()
            logger.info("Log viewer opened")

    def close(self) -> None:
        """Remove this overlay from the page's overlay stack."""
        self.visible = False
        if self in self._page.overlay:
            self._page.overlay.remove(self)
        self._page.update()
        logger.info("Log viewer closed")
        if self._on_close:
            self._on_close()

    def _header_row(self) -> ft.Row:
        return ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.BUG_REPORT, size=20),
                ft.Text(
                    "Application Logs",
                    weight=ft.FontWeight.BOLD,
                    size=18,
                    expand=True,
                ),
                self._close_button,
            ],
        )

    def _toolbar_row(self) -> ft.Row:
        return ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self._level_filter,
                self._line_count,
                self._refresh_button,
            ],
        )

    def _button_row(self) -> ft.Container:
        self._button_row_container = ft.Container(
            content=ft.Row(
                spacing=12,
                controls=[
                    self._copy_report_button,
                    self._copy_recent_button,
                ],
                alignment=ft.MainAxisAlignment.END,
            )
        )
        return self._button_row_container

    # ── Handlers ────────────────────────────────────────────────────────

    def _handle_close(self, _e=None) -> None:
        self.close()
        if self._on_close:
            self._on_close()

    def _refresh(self, _e=None) -> None:
        """Reload log entries from the log file."""
        self._log_list.controls.clear()

        try:
            max_lines = int(self._line_count.value or "200")
        except ValueError:
            max_lines = 200

        min_level = self._level_filter.value or None

        entries = read_recent_logs(
            max_lines=max_lines,
            page=self._page,
            min_level=min_level,
        )

        if not entries:
            self._log_list.controls.append(
                ft.Container(
                    ft.Text(
                        "No log entries found.\n\n"
                        "Logs are written to:\n"
                        f"{self._log_path_hint()}",
                        color=ft.Colors.GREY_500,
                        italic=True,
                    ),
                    padding=ft.Padding.all(24),
                    alignment=ft.Alignment.CENTER,
                ),
            )
            safe_update(self._log_list)
            return

        for entry in entries:
            level = entry.get("level", "INFO")
            color = _LEVEL_COLORS.get(level, ft.Colors.ON_SURFACE)
            weight = _LEVEL_WEIGHTS.get(level, ft.FontWeight.NORMAL)

            ts = entry.get("timestamp", "")
            if len(ts) > 19:
                ts = ts[-19:-6]

            module = entry.get("module", "?")
            msg = entry.get("message", "")
            lineno = entry.get("lineno", 0)

            label = f" [{ts}] {level:8s} [{module}:{lineno}] {msg}"

            self._log_list.controls.append(
                ft.Text(
                    label,
                    size=12,
                    font_family="RobotoMono",
                    color=color,
                    weight=weight,
                    selectable=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            )

        self._log_list.controls.append(
            ft.Text(
                f"── {len(entries)} entries ──",
                size=11,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER,
            ),
        )
        safe_update(self._log_list)

    def _handle_copy_report(self, _e=None) -> None:
        report = build_error_report(
            error_msg="User-requested log export",
            page=self._page,
            recent_lines=100,
        )
        self._show_inline_text(report)

    def _handle_copy_recent(self, _e=None) -> None:
        entries = read_recent_logs(max_lines=50, page=self._page)
        if not entries:
            show_toast(self._page, "No log entries to copy", is_error=True)
            self._page.update()
            return
        text = "\n".join(e["raw"] for e in entries)
        self._show_inline_text(text)

    def _show_inline_text(self, text: str) -> None:
        self._button_row_container.content = ft.Row(
            spacing=12,
            controls=[
                ft.TextField(
                    value=text,
                    read_only=True,
                    multiline=True,
                    min_lines=8,
                    max_lines=15,
                    text_size=11,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Back to buttons",
                    on_click=self._hide_inline_text,
                ),
            ],
        )
        self._page.update()

    def _hide_inline_text(self, _e=None) -> None:
        self._button_row_container.content = ft.Row(
            spacing=12,
            controls=[
                self._copy_report_button,
                self._copy_recent_button,
            ],
            alignment=ft.MainAxisAlignment.END,
        )
        self._page.update()

    def _log_path_hint(self) -> str:
        """Show where logs are stored for user reference."""
        from utils.log_collector import get_log_path
        path = get_log_path(page=self._page)
        return str(path) if path else "(unknown)"
