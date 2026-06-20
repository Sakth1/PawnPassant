from __future__ import annotations

import logging
import time
from typing import Callable

import flet as ft

from core.difficulty_presets import DIFFICULTY_PRESETS, get_preset
from utils.dialogs import safe_update
from utils.models import StockfishGameConfig

logger = logging.getLogger(__name__)


def _format_bytes(n: int) -> str:
    if n > 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n > 1_000:
        return f"{n / 1_000:.0f} KB"
    return f"{n} B"


def _format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class StockfishInstallPanel(ft.Column):
    def __init__(
        self,
        on_installed: Callable[[], None] | None = None,
        on_install_clicked: Callable[[], None] | None = None,
        on_browse_manual: Callable[[], None] | None = None,
        asset_name: str = "",
        asset_size_bytes: int = 0,
    ):
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO)
        self._on_installed = on_installed
        self._on_install_clicked = on_install_clicked
        self._on_browse_manual = on_browse_manual
        self._download_started = False
        self._download_completed = False
        self._total_bytes: int = 0
        self._phase: str = "fetching"

        # ── Engine icon ─────────────────────────────────────────────────
        self._engine_icon = ft.Container(
            content=ft.Icon(
                ft.Icons.PRECISION_MANUFACTURING,
                size=40,
                color=ft.Colors.PRIMARY,
            ),
            width=72,
            height=72,
            border_radius=36,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PRIMARY),
            alignment=ft.Alignment.CENTER,
        )

        # ── Asset info (hidden during fetch) ────────────────────────────
        self._asset_name = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        self._asset_size = ft.Text("", size=13)
        self._asset_info = ft.Column(
            spacing=2,
            controls=[self._asset_name, self._asset_size],
            visible=False,
        )

        self._engine_row = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self._engine_icon, self._asset_info],
        )

        # ── Phase status text ────────────────────────────────────────────
        self._phase_text = ft.Text(
            "Checking for latest Stockfish engine...",
            size=14,
            color=ft.Colors.GREY_400,
        )

        # ── Progress controls ────────────────────────────────────────────
        self._progress_bar = ft.ProgressBar(
            visible=True,
            width=400,
            color=ft.Colors.BLUE_400,
        )
        self._percentage_text = ft.Text(
            "", size=28, weight=ft.FontWeight.BOLD, visible=False
        )
        self._bytes_text = ft.Text("", size=12, visible=False)
        self._speed_text = ft.Text(
            "", size=12, color=ft.Colors.GREY_400, visible=False
        )
        self._time_text = ft.Text(
            "", size=12, color=ft.Colors.GREY_400, visible=False
        )
        self._progress_start_time: float = 0.0
        self._last_downloaded: int = 0
        self._last_time: float = 0.0

        # ── Error banner ─────────────────────────────────────────────────
        self._error_banner = ft.Container(
            visible=False,
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED_400),
            border_radius=8,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400),
                    ft.Text("", size=12, color=ft.Colors.RED_400, expand=True),
                ],
            ),
        )

        # ── Buttons ──────────────────────────────────────────────────────
        self._install_button = ft.FilledButton(
            "Install",
            icon=ft.Icons.DOWNLOAD,
            on_click=self._handle_install,
            disabled=True,
        )
        self._browse_button = ft.OutlinedButton(
            "Browse manually",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._handle_browse,
        )
        self._buttons_row = ft.Row(
            spacing=12,
            controls=[self._install_button, self._browse_button],
        )

        # ── Info banner ──────────────────────────────────────────────────
        self._info_banner = ft.Container(
            visible=False,
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE_200),
            border_radius=8,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE_200),
                    ft.Text(
                        "This is a one-time setup. The binary will be saved "
                        "locally and reused for future games.",
                        size=12,
                        color=ft.Colors.BLUE_200,
                        expand=True,
                    ),
                ],
            ),
        )

        # ── Card wrapper ─────────────────────────────────────────────────
        card = ft.Container(
            padding=ft.Padding.all(20),
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=12,
            content=ft.Column(
                spacing=16,
                controls=[
                    self._engine_row,
                    self._phase_text,
                    self._progress_bar,
                    self._percentage_text,
                    ft.Row(
                        spacing=24,
                        controls=[
                            self._bytes_text,
                            self._speed_text,
                            self._time_text,
                        ],
                    ),
                    self._error_banner,
                    self._buttons_row,
                    self._info_banner,
                ],
            ),
        )

        self.controls = [card]

    # ── Phase transitions ──────────────────────────────────────────────

    def set_fetching(self) -> None:
        self._phase = "fetching"
        self._phase_text.value = "Checking for latest Stockfish engine..."
        self._progress_bar.visible = True
        self._progress_bar.color = ft.Colors.BLUE_400
        self._progress_bar.value = None
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
        self._asset_info.visible = False
        self._error_banner.visible = False
        self._install_button.disabled = True
        self._install_button.text = "Install"
        self._install_button.icon = ft.Icons.DOWNLOAD
        self._info_banner.visible = False
        safe_update(self)

    def set_ready(self, asset_name: str, asset_size_bytes: int) -> None:
        self._phase = "ready"
        self._asset_name.value = asset_name
        if asset_size_bytes > 1_000_000:
            self._asset_size.value = f"{asset_size_bytes / 1_000_000:.1f} MB"
        else:
            self._asset_size.value = f"{asset_size_bytes / 1_000:.0f} KB"
        self._phase_text.value = "Ready to install Stockfish engine"
        self._progress_bar.visible = False
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
        self._asset_info.visible = True
        self._error_banner.visible = False
        self._install_button.disabled = False
        self._install_button.text = "Install"
        self._install_button.icon = ft.Icons.DOWNLOAD
        self._info_banner.visible = True
        logger.info("Install panel ready name=%s size=%d", asset_name, asset_size_bytes)
        safe_update(self)

    def set_error(self, message: str) -> None:
        self._phase = "error"
        self._phase_text.value = "Setup failed"
        self._progress_bar.visible = False
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
        self._error_banner.visible = True
        self._error_banner.content.controls[1].value = message
        self._install_button.disabled = False
        self._install_button.text = "Retry"
        self._install_button.icon = ft.Icons.REFRESH
        self._info_banner.visible = False
        logger.warning("Install panel error: %s", message)
        safe_update(self)

    # ── Event handlers ─────────────────────────────────────────────────

    def _handle_install(self, _e=None) -> None:
        if self._phase == "error":
            self.reset_download_state()
            if self._on_install_clicked:
                self._on_install_clicked()
            return
        if self._download_started:
            return
        self._download_started = True
        self._progress_start_time = time.time()
        self._last_downloaded = 0
        self._last_time = self._progress_start_time

        self._phase = "downloading"
        self._phase_text.value = "Downloading Stockfish engine..."
        self._progress_bar.visible = True
        self._progress_bar.color = ft.Colors.GREEN_400
        self._progress_bar.value = 0.0
        self._percentage_text.visible = True
        self._percentage_text.value = "0%"
        self._bytes_text.visible = True
        self._bytes_text.value = "0 B / ?"
        self._speed_text.visible = True
        self._speed_text.value = ""
        self._time_text.visible = True
        self._time_text.value = "Starting..."
        self._asset_info.visible = False
        self._error_banner.visible = False
        self._install_button.disabled = True
        self._info_banner.visible = False
        safe_update(self)
        if self._on_install_clicked:
            try:
                self._on_install_clicked()
            except Exception as exc:
                logger.error("_handle_install: callback raised: %s", exc, exc_info=True)

    def _handle_browse(self, _e=None) -> None:
        if self._on_browse_manual:
            self._on_browse_manual()

    def update_progress(self, downloaded: int, total: int) -> None:
        if self._download_completed or not self._download_started:
            return
        total = total or 1
        self._total_bytes = total
        pct = downloaded / total
        self._progress_bar.value = pct
        self._percentage_text.value = f"{int(pct * 100)}%"

        self._bytes_text.value = f"{_format_bytes(downloaded)} / {_format_bytes(total)}"

        now = time.time()
        elapsed = now - self._progress_start_time
        elapsed_str = _format_duration(elapsed)

        dt = now - self._last_time
        if dt > 0.5:
            dd = downloaded - self._last_downloaded
            speed = dd / dt if dt > 0 else 0.0
            self._last_downloaded = downloaded
            self._last_time = now
            if speed > 0:
                self._speed_text.value = f"{_format_bytes(int(speed))}/s"
            else:
                self._speed_text.value = ""

        if pct > 0.01:
            remaining = elapsed / pct - elapsed
            remaining_str = _format_duration(remaining)
            self._time_text.value = f"{elapsed_str} — {remaining_str} remaining"
        else:
            self._time_text.value = elapsed_str
        safe_update(self)

    def on_download_complete(self, path: str) -> None:
        if self._download_completed:
            return
        self._download_completed = True

        self._phase = "verifying"
        self._phase_text.value = "Verifying downloaded binary..."
        self._progress_bar.value = None
        safe_update(self)

        if self._on_installed:
            self._on_installed()

    def reset_download_state(self) -> None:
        self._phase = "ready"
        self._download_started = False
        self._download_completed = False
        self._progress_bar.visible = False
        self._progress_bar.value = None
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
        self._error_banner.visible = False
        self._install_button.disabled = False
        self._install_button.text = "Install"
        self._install_button.icon = ft.Icons.DOWNLOAD
        self._browse_button.disabled = False
        self._info_banner.visible = True
        self._asset_info.visible = True
        logger.info("Download state reset for retry")
        safe_update(self)

    def set_asset_info(self, name: str, size_bytes: int) -> None:
        self._asset_name.value = name
        if size_bytes > 1_000_000:
            self._asset_size.value = f"{size_bytes / 1_000_000:.1f} MB"
        else:
            self._asset_size.value = f"{size_bytes / 1_000:.0f} KB"
        logger.info("Asset info updated name=%s size=%d", name, size_bytes)
        safe_update(self)


class StockfishConfigPanel(ft.Column):
    FIXED_OPTIONS = [
        ("default", "Use preset default"),
        ("custom", "Set custom value"),
    ]

    def __init__(
        self,
        on_start_game: Callable[[StockfishGameConfig], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ):
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO)
        self._on_start_game = on_start_game
        self._on_back = on_back

        self._config = StockfishGameConfig()

        self._difficulty_dropdown = ft.Dropdown(
            label="Difficulty",
            value="intermediate",
            options=[
                ft.dropdown.Option(key=k, text=v)
                for k, v in DIFFICULTY_PRESETS.items()
            ]
            if False
            else [
                ft.dropdown.Option(key=k, text=f"{p.name} — {p.description}")
                for k, p in DIFFICULTY_PRESETS.items()
            ],
            on_select=self._handle_difficulty_change,
            width=400,
        )

        self._desc_text = ft.Text(
            DIFFICULTY_PRESETS["intermediate"].description,
            size=13,
            color=ft.Colors.GREY_400,
        )

        self._advanced_checkbox = ft.Checkbox(
            label="Show advanced options",
            value=False,
            on_change=self._toggle_advanced,
        )

        self._advanced_section = ft.Column(
            spacing=12,
            visible=False,
            controls=[
                ft.Text("Engine Configuration", weight=ft.FontWeight.BOLD, size=14),
                self._slider_row("ELO Rating", 1350, 100, 3190, 50, "_elo_slider"),
                self._slider_row("Skill Level", 10, 0, 20, 1, "_skill_slider"),
                self._slider_row("Search Depth", 15, 1, 30, 1, "_depth_slider"),
                self._number_row("Threads", 1, 1, 64, "_threads_field"),
                self._number_row("Hash (MB)", 256, 16, 1024, "_hash_field"),
            ],
        )

        self._start_button = ft.FilledButton(
            "Start Game",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._handle_start,
            height=44,
        )

        back_button = None
        if on_back:
            back_button = ft.OutlinedButton(
                "Back",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: on_back(),
            )

        self.controls = [
            ft.Text(
                "Configure Stockfish",
                weight=ft.FontWeight.BOLD,
                size=18,
            ),
            self._difficulty_dropdown,
            self._desc_text,
            ft.Divider(height=1),
            self._advanced_checkbox,
            self._advanced_section,
            ft.Container(expand=True),
            ft.Row(
                spacing=12,
                controls=[b for b in [back_button, self._start_button] if b is not None],
                alignment=ft.MainAxisAlignment.END,
            ),
        ]

    def _handle_difficulty_change(self, e: ft.ControlEvent) -> None:
        name = e.control.value
        preset = get_preset(name)
        if preset:
            self._desc_text.value = preset.description
            self._config.preset_name = name
            self._config.elo = (preset.elo_min + preset.elo_max) // 2
            if self._config.skill_level is None:
                self._config.skill_level = (preset.skill_min + preset.skill_max) // 2
            self._config.depth = (preset.depth_min + preset.depth_max) // 2
            logger.info("Difficulty changed to %s elo=%d", name, self._config.elo)
            safe_update(self)

    def _toggle_advanced(self, e: ft.ControlEvent) -> None:
        self._advanced_section.visible = e.control.value
        self._config.use_preset = not e.control.value
        logger.info("Advanced options %s", "shown" if e.control.value else "hidden")
        safe_update(self)

    def _handle_start(self, _e=None) -> None:
        if self._on_start_game:
            config = self._collect_config()
            logger.info("Start game requested config=%s", config)
            self._on_start_game(config)

    def _collect_config(self) -> StockfishGameConfig:
        if self._advanced_section.visible:
            self._config.use_preset = False
        return self._config

    def _slider_row(
        self,
        label: str,
        default: int,
        min_val: int,
        max_val: int,
        step: int,
        attr_name: str,
    ) -> ft.Container:
        slider = ft.Slider(
            value=default,
            min=min_val,
            max=max_val,
            divisions=(max_val - min_val) // step,
            label="{value}",
            width=300,
        )
        setattr(self, attr_name, slider)
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(label, expand=True, size=13),
                    slider,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

    def _number_row(
        self,
        label: str,
        default: int,
        min_val: int,
        max_val: int,
        attr_name: str,
    ) -> ft.Container:
        field = ft.TextField(
            value=str(default),
            width=80,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            text_align=ft.TextAlign.RIGHT,
        )
        setattr(self, attr_name, field)
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(label, expand=True, size=13),
                    field,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )
