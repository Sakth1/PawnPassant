"""Settings screen for board, gameplay, and clock preferences.

This view owns only the controls. Validation, persistence, and notification are
delegated to :class:`utils.settings.SettingsController` so settings remain
consistent across board, clock, and app shell subscribers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import flet as ft

from core.binary_verifier import verify_stockfish_binary
from core.download_manager import _resolve_archive
from ui.task_toast import show_toast
from utils.constants import DEFAULT_PAGE_HEIGHT, DEFAULT_PAGE_WIDTH
from ui.layout import AppLayout, resolve_app_layout
from utils.dialogs import safe_update
from utils.events import SettingsChangedEvent
from utils.settings import SettingsController
from utils.signals import bus

logger = logging.getLogger(__name__)


class SettingsView(ft.Container):
    """Render grouped settings controls and forward changes to the controller."""

    def __init__(
        self,
        controller: SettingsController | None = None,
        file_picker: ft.FilePicker | None = None,
        on_open_log_viewer: Callable[[], None] | None = None,
    ):
        super().__init__(expand=True)
        #: Controller that validates, emits, and persists settings changes.
        self.controller = controller or SettingsController()
        #: Current settings snapshot reflected by the controls.
        self.settings = self.controller.settings
        #: File picker for manual binary selection.
        self._file_picker = file_picker
        #: Callback to open the in-app log viewer.
        self._on_open_log_viewer = on_open_log_viewer
        #: Last applied responsive layout metrics.
        self.layout = resolve_app_layout(DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT)

        self.title_text = ft.Text("Settings", weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text("Board, gameplay, and clock preferences.")
        self.board_section = ft.Column(tight=True)
        self.gameplay_section = ft.Column(tight=True)
        self.clock_section = ft.Column(tight=True)
        self.stockfish_section = ft.Column(tight=True)
        self.debug_section = ft.Column(tight=True)
        self.reset_button = ft.OutlinedButton(
            "Reset defaults",
            icon=ft.Icons.RESTART_ALT_ROUNDED,
            on_click=self._handle_reset_defaults,
        )
        self.status_text = ft.Text("")
        self.main_column = ft.Column(
            tight=True,
            controls=[
                self.title_text,
                self.subtitle_text,
                self.board_section,
                self.gameplay_section,
                self.clock_section,
                self.stockfish_section,
                self.debug_section,
                ft.Row(
                    controls=[self.reset_button, self.status_text],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        )
        self.content = ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Container(content=self.main_column),
        )

        bus.connect(SettingsChangedEvent, self._handle_settings_changed)
        self.apply_layout(self.layout)
        self._rebuild_sections()

    def apply_layout(self, layout: AppLayout) -> None:
        """Resize the settings page for the active breakpoint."""

        self.layout = layout
        panel_width = min(860, int(layout.width - (layout.padding * 2)))
        self.content.padding = ft.Padding.all(layout.padding)
        self.content.content.width = max(300, panel_width)
        self.main_column.spacing = max(12, layout.gap)
        self.title_text.size = 24 if layout.compact else 32
        self.subtitle_text.size = 13 if layout.compact else 15
        for section in (
            self.board_section,
            self.gameplay_section,
            self.clock_section,
            self.stockfish_section,
        ):
            section.spacing = max(8, layout.gap // 2)
        safe_update(self)

    def _rebuild_sections(self):
        """Rebuild all setting rows from the current settings snapshot."""

        self.board_section.controls = [
            self._section_header("Board"),
            self._switch_row(
                "Show legal moves",
                "show_legal_moves",
                self.settings.show_legal_moves,
            ),
            self._switch_row(
                "Tap feedback",
                "show_tap_feedback",
                self.settings.show_tap_feedback,
            ),
            self._switch_row(
                "Auto flip board",
                "auto_flip_board",
                self.settings.auto_flip_board,
            ),
            self._switch_row(
                "Coordinates",
                "show_coordinates",
                self.settings.show_coordinates,
            ),
            self._dropdown_row(
                "Move animation",
                "move_animation",
                self.settings.move_animation,
                [
                    ("off", "Off"),
                    ("fast", "Fast"),
                    ("normal", "Normal"),
                    ("slow", "Slow"),
                ],
            ),
        ]
        self.gameplay_section.controls = [
            self._section_header("Gameplay"),
            self._switch_row(
                "Confirm moves",
                "confirm_moves",
                self.settings.confirm_moves,
            ),
            self._dropdown_row(
                "Promotion",
                "promotion_default",
                self.settings.promotion_default,
                [
                    ("ask", "Ask every time"),
                    ("queen", "Queen"),
                    ("rook", "Rook"),
                    ("bishop", "Bishop"),
                    ("knight", "Knight"),
                ],
            ),
        ]
        self.clock_section.controls = [
            self._section_header("Clock and actions"),
            self._number_row(
                "Critical time seconds",
                "critical_time_seconds",
                self.settings.critical_time_seconds,
            ),
            self._switch_row(
                "Show critical milliseconds",
                "show_milliseconds_in_critical",
                self.settings.show_milliseconds_in_critical,
            ),
            self._switch_row(
                "Confirm resign",
                "confirm_resign",
                self.settings.confirm_resign,
            ),
            self._switch_row(
                "Confirm draw",
                "confirm_draw",
                self.settings.confirm_draw,
            ),
        ]
        self.stockfish_section.controls = [
            self._section_header("Stockfish Engine"),
            self._binary_path_row(),
        ]
        self.debug_section.controls = [
            self._section_header("Support"),
            self._log_viewer_row(),
        ]
        self.status_text.value = "Preferences saved locally"
        safe_update(self)

    def _section_header(self, label: str) -> ft.Container:
        """Create a section title used to group related preferences."""

        return ft.Container(
            padding=ft.Padding(0, 8, 0, 2),
            content=ft.Text(label, weight=ft.FontWeight.BOLD, size=16),
        )

    def _setting_row(self, label: str, control: ft.Control) -> ft.Container:
        """Wrap a label/control pair in the shared settings row style."""

        return ft.Container(
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            padding=ft.Padding(12, 8, 12, 8),
            content=ft.Row(
                controls=[
                    ft.Text(label, expand=True),
                    control,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _switch_row(self, label: str, key: str, value: bool) -> ft.Container:
        """Create a boolean settings row backed by an adaptive switch."""

        control = ft.Switch(
            value=value,
            adaptive=True,
            on_change=lambda event, setting_key=key: self._update_setting(
                setting_key, bool(event.control.value)
            ),
        )
        return self._setting_row(label, control)

    def _dropdown_row(
        self,
        label: str,
        key: str,
        value: str,
        options: list[tuple[str, str]],
    ) -> ft.Container:
        """Create an option-list settings row backed by a dropdown."""

        control = ft.Dropdown(
            width=190 if self.layout.compact else 220,
            value=value,
            options=[
                ft.dropdown.Option(key=option, text=text) for option, text in options
            ],
            on_select=lambda event, setting_key=key: self._update_setting(
                setting_key, event.control.value
            ),
        )
        return self._setting_row(label, control)

    def _number_row(self, label: str, key: str, value: int) -> ft.Container:
        """Create a numeric settings row backed by a number-only text field."""

        control = ft.TextField(
            width=96,
            value=str(value),
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            text_align=ft.TextAlign.RIGHT,
            on_change=lambda event, setting_key=key: self._update_number_setting(
                setting_key, event.control
            ),
        )
        return self._setting_row(label, control)

    def _binary_path_row(self) -> ft.Container:
        """Show the Stockfish binary path as read-only with a remove option."""
        path = self.settings.stockfish_binary_path
        path_text = ft.Text(
            path if path else "Not installed",
            size=13,
            color=ft.Colors.GREY_400 if not path else None,
            selectable=True,
            expand=True,
        )

        select_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            tooltip="Select Stockfish binary",
            on_click=self._handle_select_binary,
        )
        remove_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            tooltip="Remove Stockfish binary path",
            on_click=self._handle_remove_stockfish,
            visible=bool(path),
        )

        return self._setting_row(
            "Binary path",
            ft.Row(
                controls=[path_text, select_btn, remove_btn],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _log_viewer_row(self) -> ft.Container:
        """Create a row that opens the in-app log viewer."""
        return self._setting_row(
            "Application Logs",
            ft.Row(
                controls=[
                    ft.Text(
                        "View and copy diagnostic logs",
                        size=13,
                        color=ft.Colors.GREY_400,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.BUG_REPORT,
                        tooltip="Open log viewer",
                        on_click=self._handle_open_log_viewer,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _handle_open_log_viewer(self, _event=None) -> None:
        if self._on_open_log_viewer:
            self._on_open_log_viewer()

    def _handle_select_binary(self, _event=None) -> None:
        """Open file picker to select a Stockfish binary."""
        if self._file_picker is None:
            return
        self.page.run_task(self._async_pick_binary)

    async def _async_pick_binary(self) -> None:
        files = await self._file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["exe", "bin", "zip", ""],
            dialog_title="Select Stockfish executable or archive",
        )
        if not files or not files[0].path:
            return
        path = files[0].path
        logger.info("Settings: user selected path=%s", path)
        exe_path = str(_resolve_archive(Path(path)))
        valid, version = verify_stockfish_binary(exe_path)
        if valid:
            self.controller.update(stockfish_binary_path=path)
            show_toast(self.page, f"Valid Stockfish: {version}")
        else:
            show_toast(self.page, version, is_error=True)

    def _handle_remove_stockfish(self, _event=None) -> None:
        """Clear the stored Stockfish binary path."""
        self.controller.update(stockfish_binary_path="")

    def _update_setting(self, key: str, value: Any):
        """Send one setting change to the controller."""

        logger.info("Settings view update key=%s value=%s", key, value)
        self.controller.update(**{key: value})

    def _update_number_setting(self, key: str, control: ft.TextField):
        """Parse and send a numeric setting change when the field has a value."""

        raw_value = (control.value or "").strip()
        if not raw_value:
            return
        value = int(raw_value)
        logger.info("Settings view numeric update key=%s value=%s", key, value)
        self.controller.update(**{key: value})

    def _handle_reset_defaults(self, _event=None):
        """Restore all settings to their default values."""

        logger.info("Settings defaults requested")
        self.controller.reset_defaults()

    def _handle_settings_changed(self, event: SettingsChangedEvent):
        """Refresh controls after any settings change event."""

        self.settings = event.settings
        logger.debug("Settings view refreshed")
        self._rebuild_sections()
