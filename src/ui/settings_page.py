"""Settings screen for board, gameplay, and clock preferences."""

from __future__ import annotations

from typing import Any

import flet as ft

from ui.layout import AppLayout, resolve_app_layout
from utils.events import SettingsChangedEvent
from utils.models import AppSettings
from utils.settings import SettingsController
from utils.signals import bus


class SettingsView(ft.Container):
    def __init__(self, controller: SettingsController | None = None):
        super().__init__(expand=True)
        self.controller = controller or SettingsController()
        self.settings = self.controller.settings
        self.layout = resolve_app_layout(960, 800)

        self.title_text = ft.Text("Settings", weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text("Board, gameplay, and clock preferences.")
        self.board_section = ft.Column(tight=True)
        self.gameplay_section = ft.Column(tight=True)
        self.clock_section = ft.Column(tight=True)
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
        ):
            section.spacing = max(8, layout.gap // 2)
        self._safe_update(self)

    def _rebuild_sections(self):
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
        self.status_text.value = "Preferences saved locally"
        self._safe_update(self)

    def _section_header(self, label: str) -> ft.Container:
        return ft.Container(
            padding=ft.Padding(0, 8, 0, 2),
            content=ft.Text(label, weight=ft.FontWeight.BOLD, size=16),
        )

    def _setting_row(self, label: str, control: ft.Control) -> ft.Container:
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
        control = ft.Dropdown(
            width=190 if self.layout.compact else 220,
            value=value,
            options=[
                ft.dropdown.Option(key=option, text=text)
                for option, text in options
            ],
            on_select=lambda event, setting_key=key: self._update_setting(
                setting_key, event.control.value
            ),
        )
        return self._setting_row(label, control)

    def _number_row(self, label: str, key: str, value: int) -> ft.Container:
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

    def _update_setting(self, key: str, value: Any):
        self.controller.update(**{key: value})

    def _update_number_setting(self, key: str, control: ft.TextField):
        raw_value = (control.value or "").strip()
        if not raw_value:
            return
        value = int(raw_value)
        self.controller.update(**{key: value})

    def _handle_reset_defaults(self, _event=None):
        self.controller.reset_defaults()

    def _handle_settings_changed(self, event: SettingsChangedEvent):
        self.settings = event.settings
        self._rebuild_sections()

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except RuntimeError:
            pass
