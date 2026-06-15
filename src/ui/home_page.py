"""Home screen for selecting a chess time control before starting a game."""

from __future__ import annotations

from dataclasses import fields
import logging
from typing import Callable

import flet as ft

from utils.constants import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
)
from ui.layout import AppLayout, resolve_app_layout
from utils.dialogs import safe_update, show_alert_dialog
from utils.models import TimeControl
from utils.game_state import GameAgainst, game_state

logger = logging.getLogger(__name__)


class HomeView(ft.Container):
    """Render preset and custom time controls and start the selected game."""

    def __init__(
        self,
        on_time_control_selected: Callable[[tuple[int, int]], None] | None = None,
    ):
        super().__init__(expand=True)
        #: Callback invoked with ``(minutes, increment_seconds)`` when play starts.
        self.on_time_control_selected = on_time_control_selected
        #: Last applied responsive layout metrics.
        self.layout = resolve_app_layout(DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT)
        #: Preset dictionaries generated from :class:`utils.models.TimeControl`.
        self.presets = self._build_presets()
        #: Key of the currently selected preset when no custom control is active.
        self.selected_preset_key = self._default_preset_key()
        #: Custom ``(minutes, increment_seconds)`` selected by the user, if any.
        self.selected_custom_time_control: tuple[int, int] | None = None

        self.title_text = ft.Text("Quick pairing", weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text(
            "Choose a preset or enter your own time control.",
            text_align=ft.TextAlign.LEFT,
        )
        self.selection_text = ft.Text(
            text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD
        )
        self.grid = ft.ResponsiveRow(columns=12)
        self.minutes_input = ft.TextField(
            label="Minutes",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_change=self._handle_custom_input_change,
        )
        self.increment_input = ft.TextField(
            label="Increment",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_change=self._handle_custom_input_change,
        )
        self.custom_hint = ft.Text("Custom time control")
        self.custom_apply_button = ft.OutlinedButton(
            "Use custom",
            icon=ft.Icons.TUNE_ROUNDED,
            on_click=self._handle_custom_apply,
        )
        self.play_computer_button = ft.FilledButton(
            "Play computer",
            icon=ft.Icons.COMPUTER,
            on_click=self._handle_play_computer,
        )
        self.play_someone_button = ft.FilledButton(
            "Play someone",
            icon=ft.Icons.PERSON,
            on_click=self._make_wip_handler(feature="Play someone"),
        )
        self.custom_row = ft.ResponsiveRow(columns=12)
        self.footer_row = ft.ResponsiveRow(columns=12)
        self.section_column = ft.Column(
            tight=True,
            controls=[
                self.title_text,
                self.subtitle_text,
                self.grid,
                self.custom_row,
                self.footer_row,
            ],
        )
        self.hero_panel = ft.Container(content=self.section_column)
        self.content = ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Container(content=self.hero_panel),
        )

        self.apply_layout(self.layout)
        self._rebuild_view()

    def apply_layout(self, layout: AppLayout) -> None:
        """Resize the home screen controls for the active breakpoint."""

        self.layout = layout
        panel_width = min(780, int(layout.width - (layout.padding * 2)))

        self.content.padding = ft.Padding.all(layout.padding)
        self.content.content.width = max(300, panel_width)
        self.hero_panel.padding = ft.Padding.all(max(14, layout.padding))
        self.hero_panel.border_radius = 20 if layout.compact else 24
        self.hero_panel.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        self.section_column.spacing = max(12, layout.gap)
        self.grid.spacing = max(8, layout.gap // 2)
        self.grid.run_spacing = max(8, layout.gap // 2)
        self.custom_row.spacing = max(10, layout.gap)
        self.custom_row.run_spacing = 8
        self.footer_row.spacing = max(10, layout.gap)
        self.footer_row.run_spacing = 8

        self.title_text.size = 24 if layout.compact else 32
        self.subtitle_text.size = 13 if layout.compact else 15
        self.selection_text.size = 20 if layout.compact else 24
        self.custom_hint.size = 12 if layout.compact else 13
        self.play_computer_button.height = 44 if layout.compact else 48
        self.play_computer_button.width = None if layout.stacked else 180
        self.play_someone_button.height = 44 if layout.compact else 48
        self.play_someone_button.width = None if layout.stacked else 180
        self.custom_apply_button.height = 44 if layout.compact else 48
        self.custom_apply_button.width = None if layout.stacked else 160

        self._rebuild_view()
        safe_update(self)

    def _build_presets(self) -> list[dict[str, object]]:
        """Build sorted time-control preset metadata from the dataclass fields."""

        presets: list[dict[str, object]] = []
        for time_field in fields(TimeControl):
            minutes, increment = time_field.default
            presets.append(
                {
                    "key": time_field.name,
                    "label": f"{minutes}+{increment}",
                    "minutes": minutes,
                    "increment": increment,
                    "value": (minutes, increment),
                    "category": self._categorize_time_control(minutes),
                }
            )
        return sorted(
            presets,
            key=lambda preset: (
                CATEGORY_ORDER.index(str(preset["category"])),
                int(preset["minutes"]),
                int(preset["increment"]),
            ),
        )

    def _alert_feature_wip(self, feature: str):
        show_alert_dialog(
            self.page,
            "Work In Progress",
            f"{feature} feature is Work In Progress.",
        )

    def _make_wip_handler(self, feature: str):
        """Return a callable that shows a Work-In-Progress dialog."""
        return lambda _e=None: self._alert_feature_wip(feature)

    @staticmethod
    def _categorize_time_control(minutes: int) -> str:
        """Classify a preset by base minutes for grouping and labels."""

        if minutes <= 2:
            return "bullet"
        if minutes <= 5:
            return "blitz"
        if minutes <= 20:
            return "rapid"
        return "classical"

    def _default_preset_key(self) -> str:
        """Return the preset key selected when the home screen first opens."""

        for preset in self.presets:
            if preset["value"] == TimeControl.THREE_PLUS_TWO:
                return str(preset["key"])
        return str(self.presets[0]["key"])

    @property
    def selected_preset(self) -> dict[str, object]:
        """Return metadata for the selected preset, falling back defensively."""

        for preset in self.presets:
            if preset["key"] == self.selected_preset_key:
                return preset
        return self.presets[0]

    @property
    def selected_time_control(self) -> tuple[int, int]:
        """Return the custom time control when present, otherwise the preset."""

        return self.selected_custom_time_control or self.selected_preset["value"]

    def _rebuild_view(self) -> None:
        """Recompose preset grid, custom inputs, and footer selection text."""

        self.grid.controls = [
            self._build_preset_tile(preset) for preset in self.presets
        ]
        self.selection_text.value = self._selection_label()
        self.custom_row.controls = [
            ft.Container(content=self.custom_hint, col={"xs": 12, "md": 12}),
            ft.Container(content=self.minutes_input, col={"xs": 4, "md": 4}),
            ft.Container(content=self.increment_input, col={"xs": 4, "md": 4}),
            ft.Container(
                content=self.custom_apply_button,
                alignment=ft.Alignment.CENTER_RIGHT,
                col={"xs": 4, "md": 4},
            ),
        ]
        self.footer_row.controls = [
            ft.Container(
                content=self.play_computer_button,
                alignment=ft.Alignment.CENTER_LEFT,
                col={"xs": 4, "md": 4},
            ),
            ft.Container(
                content=self.selection_text,
                col={"xs": 4, "md": 4},
                alignment=ft.Alignment.CENTER,
            ),
            ft.Container(
                content=self.play_someone_button,
                alignment=ft.Alignment.CENTER_RIGHT,
                col={"xs": 4, "md": 4},
            ),
        ]
        safe_update(self.grid)
        safe_update(self.custom_row)
        safe_update(self.footer_row)

    def _build_preset_tile(self, preset: dict[str, object]) -> ft.Container:
        """Create one clickable preset tile."""

        is_selected = (
            self.selected_custom_time_control is None
            and preset["key"] == self.selected_preset_key
        )
        return ft.Container(
            col=self._tile_columns(),
            height=74 if self.layout.compact else 84,
            border=ft.Border.all(
                2 if is_selected else 1,
                ft.Colors.PRIMARY if is_selected else ft.Colors.OUTLINE_VARIANT,
            ),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=8, vertical=10),
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip=self._preset_tooltip(preset),
            on_click=lambda _e, key=str(preset["key"]): self._select_preset(key),
            content=ft.Column(
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        str(preset["label"]),
                        size=18 if self.layout.compact else 22,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        CATEGORY_LABELS[str(preset["category"])],
                        size=11 if self.layout.compact else 12,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    def _tile_columns(self) -> dict[str, int]:
        """Return ResponsiveRow column spans for preset tiles."""

        if self.layout.breakpoint == "mobile":
            return {"xs": 4, "sm": 4, "md": 4}
        if self.layout.breakpoint == "tablet":
            return {"xs": 4, "sm": 4, "md": 3}
        return {"xs": 6, "sm": 4, "md": 3, "lg": 3}

    def _preset_tooltip(self, preset: dict[str, object]) -> str:
        """Return accessible detail text for a preset tile."""

        return (
            f"{CATEGORY_LABELS[str(preset['category'])]}  "
            f"{preset['minutes']} min + {preset['increment']} sec increment"
        )

    def _selection_label(self) -> str:
        """Return the footer text describing the active time control."""

        if self.selected_custom_time_control is not None:
            minutes, increment = self.selected_custom_time_control
            return f"Selected: Custom {minutes}+{increment}"
        preset = self.selected_preset
        return (
            f"Selected: {preset['label']} "
            f"{CATEGORY_LABELS[str(preset['category'])]}"
        )

    def _select_preset(self, preset_key: str) -> None:
        """Select a preset and clear any previous custom selection."""

        self.selected_preset_key = preset_key
        self.selected_custom_time_control = None
        logger.info("Preset time control selected key=%s", preset_key)
        self._rebuild_view()

    def _handle_custom_input_change(
        self, _event: ft.ControlEvent | None = None
    ) -> None:
        """Clear validation errors while the user edits custom time fields."""

        self.minutes_input.error_text = None
        self.increment_input.error_text = None
        safe_update(self.minutes_input)
        safe_update(self.increment_input)

    def _parse_custom_time_control(self) -> tuple[int, int] | None:
        """Parse custom minutes/increment fields into a validated tuple."""

        minutes_raw = (self.minutes_input.value or "").strip()
        increment_raw = (self.increment_input.value or "").strip()

        if not minutes_raw and not increment_raw:
            return None

        minutes = int(minutes_raw) if minutes_raw else 0
        increment = int(increment_raw) if increment_raw else 0
        if minutes <= 0:
            self.minutes_input.error_text = "Enter minutes"
            safe_update(self.minutes_input)
            return None
        return (minutes, increment)

    def _handle_custom_apply(self, _event: ft.ControlEvent | None = None) -> None:
        """Store a valid custom time control as the active selection."""

        parsed = self._parse_custom_time_control()
        if parsed is None:
            return
        self.selected_custom_time_control = parsed
        logger.info(
            "Custom time control selected minutes=%s increment_seconds=%s",
            parsed[0],
            parsed[1],
        )
        self._rebuild_view()

    def _handle_play_computer(self, _event: ft.ControlEvent | None = None) -> None:
        """Start a game using the selected preset or valid custom control."""

        if self.selected_custom_time_control is None:
            parsed = self._parse_custom_time_control()
            if parsed is not None:
                self.selected_custom_time_control = parsed
        game_state.game_against = GameAgainst.COMPUTER
        self._start_time_control(self.selected_time_control)

    def _start_time_control(
        self,
        time_control: tuple[int, int],
    ) -> None:
        """Notify the parent app that a time control was chosen."""

        if self.on_time_control_selected is not None:
            logger.info(
                "Starting selected time control minutes=%s increment_seconds=%s",
                time_control[0],
                time_control[1],
            )
            self.on_time_control_selected(
                time_control
            )
