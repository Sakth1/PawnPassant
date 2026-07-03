from __future__ import annotations

import logging
import time
from typing import Callable

import flet as ft

from core.lc0_config import ALL_BACKENDS, DEFAULT_NETWORKS, NetworkInfo, recommend_backends_for_system
from core.difficulty_presets import DIFFICULTY_PRESETS, get_preset
from utils.dialogs import safe_update
from utils.models import Lc0GameConfig
from utils.log_collector import build_error_report

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


class EngineInstallPanel(ft.Column):
    def __init__(
        self,
        on_installed: Callable[[], None] | None = None,
        on_install_clicked: Callable[[], None] | None = None,
        on_browse_manual: Callable[[], None] | None = None,
        asset_name: str = "",
        asset_size_bytes: int = 0,
        engine_name: str = "Leela Chess Zero",
        engine_icon: ft.Icons | None = None,
        bundled_version: str = "",
        has_downloaded_version: bool = False,
        on_activate_downloaded: Callable[[], None] | None = None,
        on_check_updates: Callable[[], None] | None = None,
    ):
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO)
        self._on_installed = on_installed
        self._on_install_clicked = on_install_clicked
        self._on_browse_manual = on_browse_manual
        self._on_activate_downloaded = on_activate_downloaded
        self._on_check_updates = on_check_updates
        self._engine_name = engine_name
        self._download_started = False
        self._download_completed = False
        self._total_bytes: int = 0
        self._phase: str = "fetching"

        self._engine_icon = ft.Container(
            content=ft.Icon(
                engine_icon or ft.Icons.PRECISION_MANUFACTURING,
                size=40,
                color=ft.Colors.PRIMARY,
            ),
            width=72,
            height=72,
            border_radius=36,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PRIMARY),
            alignment=ft.Alignment.CENTER,
        )

        self._asset_name = ft.Text("", size=16, weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS)
        self._asset_size = ft.Text("", size=13)
        self._asset_debug = ft.Column(spacing=2, visible=False)
        self._asset_info = ft.Column(
            spacing=2,
            controls=[self._asset_name, self._asset_size, self._asset_debug],
            visible=False,
        )

        self._engine_row = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self._engine_icon, self._asset_info],
        )

        self._phase_text = ft.Text(
            f"Checking for latest {engine_name} engine...",
            size=14,
            color=ft.Colors.GREY_400,
        )

        self._progress_bar = ft.ProgressBar(
            visible=True,
            width=400,
            color=ft.Colors.BLUE_400,
        )
        self._percentage_text = ft.Text("", size=28, weight=ft.FontWeight.BOLD, visible=False)
        self._bytes_text = ft.Text("", size=12, visible=False)
        self._speed_text = ft.Text("", size=12, color=ft.Colors.GREY_400, visible=False)
        self._time_text = ft.Text("", size=12, color=ft.Colors.GREY_400, visible=False)
        self._progress_start_time: float = 0.0
        self._last_downloaded: int = 0
        self._last_time: float = 0.0

        self._copy_log_button = ft.IconButton(
            icon=ft.Icons.COPY,
            icon_size=16,
            icon_color=ft.Colors.RED_400,
            tooltip="Copy error log",
            on_click=self._handle_copy_log,
        )
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
                    self._copy_log_button,
                ],
            ),
        )

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

        self._bundled_status = ft.Row(
            spacing=8,
            visible=bool(bundled_version),
            controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=16),
                ft.Text(
                    f"{engine_name} {bundled_version} (bundled)" if bundled_version else "",
                    size=13,
                    color=ft.Colors.GREEN_400,
                ),
            ],
        )

        self._activate_button = ft.FilledTonalButton(
            "Activate",
            on_click=self._handle_activate,
            visible=False,
        )
        self._downloaded_status = ft.Text("", size=13, visible=False)
        self._downloaded_row = ft.Row(
            spacing=8,
            visible=False,
            controls=[self._downloaded_status, self._activate_button],
        )

        self._check_updates_button = ft.OutlinedButton(
            "Check for updates",
            icon=ft.Icons.UPDATE,
            on_click=self._handle_check_updates,
            visible=not bool(bundled_version),
        )

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
                        "One-time setup. Saved locally and reused for future games.",
                        size=12,
                        color=ft.Colors.BLUE_200,
                        expand=True,
                    ),
                ],
            ),
        )

        card = ft.Container(
            padding=ft.Padding.all(20),
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=12,
            content=ft.Column(
                spacing=16,
                controls=[
                    self._engine_row,
                    self._bundled_status,
                    self._downloaded_row,
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
                    self._check_updates_button,
                    self._buttons_row,
                    self._info_banner,
                ],
            ),
        )

        self.controls = [card]

    def set_fetching(self) -> None:
        self._phase = "fetching"
        self._phase_text.value = f"Checking for latest {self._engine_name} engine..."
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

    def set_ready(self, asset_name: str, asset_size_bytes: int, sha256: str = "", platform: str = "", arch: str = "") -> None:
        self._phase = "ready"
        self._asset_name.value = asset_name
        self._asset_size.value = _format_bytes(asset_size_bytes)
        self._phase_text.value = f"Ready to install {self._engine_name} engine"
        self._progress_bar.visible = False
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
        self._asset_info.visible = True

        debug_lines = []
        if sha256:
            debug_lines.append(ft.Text(f"SHA-256: {sha256[:16]}...", size=11, color=ft.Colors.GREY_500, font_family="monospace"))
        if platform:
            debug_lines.append(ft.Text(f"Platform: {platform}  Arch: {arch}", size=11, color=ft.Colors.GREY_500))
        self._asset_debug.controls = debug_lines
        self._asset_debug.visible = bool(debug_lines)

        self._error_banner.visible = False
        self._install_button.disabled = False
        self._install_button.text = "Install"
        self._install_button.icon = ft.Icons.DOWNLOAD
        self._info_banner.visible = True
        safe_update(self)

    def set_verifying(self) -> None:
        self._phase = "verifying"
        self._phase_text.value = "Verifying selected binary..."
        self._progress_bar.visible = True
        self._progress_bar.value = None
        self._progress_bar.color = ft.Colors.BLUE_400
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
        self._asset_info.visible = False
        self._error_banner.visible = False
        self._install_button.disabled = True
        self._info_banner.visible = False
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
        safe_update(self)

    def _handle_copy_log(self, _e=None) -> None:
        error_msg = self._error_banner.content.controls[1].value
        if not error_msg:
            return
        report = build_error_report(error_msg=error_msg, page=self.page, recent_lines=30)
        self._show_report_inline(report)

    def _show_report_inline(self, report: str) -> None:
        original = self._error_banner.content.controls[:]
        self._error_banner.content.controls = [
            ft.TextField(
                value=report,
                read_only=True,
                multiline=True,
                min_lines=5,
                max_lines=12,
                text_size=11,
                expand=True,
            ),
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back",
                on_click=lambda e: self._restore_error_banner(original),
            ),
        ]
        self.page.update()

    def _restore_error_banner(self, original: list) -> None:
        self._error_banner.content.controls = original
        self.page.update()

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
        self._phase_text.value = f"Downloading {self._engine_name} engine..."
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

    def _handle_activate(self, _e=None) -> None:
        if self._on_activate_downloaded:
            self._on_activate_downloaded()

    def _handle_check_updates(self, _e=None) -> None:
        if self._on_check_updates:
            self._on_check_updates()

    def set_bundled_status(self, version: str) -> None:
        self._bundled_status.visible = True
        self._bundled_status.controls[1].value = f"{self._engine_name} {version} (bundled)"
        self._check_updates_button.visible = True
        safe_update(self)

    def show_downloaded_available(self, version: str) -> None:
        self._downloaded_row.visible = True
        self._downloaded_status.value = f"Downloaded {version} available -- tap Activate to switch"
        self._activate_button.visible = True
        safe_update(self)

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
            self._speed_text.value = f"{_format_bytes(int(speed))}/s" if speed > 0 else ""

        if pct > 0.01:
            remaining = elapsed / pct - elapsed
            remaining_str = _format_duration(remaining)
            self._time_text.value = f"{elapsed_str} - {remaining_str} remaining"
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
        safe_update(self)

    def set_asset_info(self, name: str, size_bytes: int) -> None:
        self._asset_name.value = name
        self._asset_size.value = _format_bytes(size_bytes)
        safe_update(self)


class EngineConfigPanel(ft.Column):
    def __init__(
        self,
        on_start_game: Callable[[Lc0GameConfig], None] | None = None,
        on_back: Callable[[], None] | None = None,
        available_networks: list | None = None,
    ):
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO)
        self._on_start_game = on_start_game
        self._on_back = on_back
        self._config = Lc0GameConfig()
        self._available_networks = available_networks or DEFAULT_NETWORKS

        recommended = recommend_backends_for_system()

        self._difficulty_dropdown = ft.Dropdown(
            label="Difficulty",
            value="intermediate",
            options=[
                ft.dropdown.Option(key=k, text=f"{p.name} - {p.description}")
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

        network_options = [ft.dropdown.Option(key=n.name, text=n.name) for n in self._available_networks]
        self._network_dropdown = ft.Dropdown(
            label="Neural Network (weights)",
            value=self._available_networks[0].name if self._available_networks else "",
            options=network_options,
            on_select=self._handle_network_change,
            width=400,
        )

        self._network_desc = ft.Text(
            self._available_networks[0].description if self._available_networks else "",
            size=12,
            color=ft.Colors.GREY_400,
        )

        backend_options = [
            ft.dropdown.Option(key=bid, text=info.label)
            for bid, info in ALL_BACKENDS.items()
            if bid in recommended or bid == "blas"
        ]
        self._backend_dropdown = ft.Dropdown(
            label="Compute Backend",
            value=recommended[0] if recommended else "blas",
            options=backend_options,
            on_select=self._handle_backend_change,
            width=400,
        )

        self._backend_desc = ft.Text(
            ALL_BACKENDS.get(recommended[0], ALL_BACKENDS["blas"]).description if recommended else "",
            size=12,
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
                self._number_row("CPU Threads", 2, 1, 64, "_threads_field"),
                self._number_row("Minibatch Size", 256, 1, 1024, "_minibatch_field"),
                self._slider_row("Temperature", 0.0, 0.0, 2.0, 0.1, "_temp_slider"),
                self._slider_row("CPuct", 3.4, 0.0, 10.0, 0.1, "_cpuct_slider"),
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
            ft.Text("Configure Lc0", weight=ft.FontWeight.BOLD, size=18),
            self._difficulty_dropdown,
            self._desc_text,
            ft.Divider(height=1),
            ft.Text("Neural Network", weight=ft.FontWeight.BOLD, size=14),
            self._network_dropdown,
            self._network_desc,
            ft.Divider(height=1),
            ft.Text("Compute Backend", weight=ft.FontWeight.BOLD, size=14),
            self._backend_dropdown,
            self._backend_desc,
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
            safe_update(self)

    def _handle_network_change(self, e: ft.ControlEvent) -> None:
        name = e.control.value
        for n in self._available_networks:
            if n.name == name:
                self._network_desc.value = n.description
                self._config.network_name = name
                break
        safe_update(self)

    def _handle_backend_change(self, e: ft.ControlEvent) -> None:
        backend_id = e.control.value
        info = ALL_BACKENDS.get(backend_id)
        if info:
            self._backend_desc.value = info.description
            self._config.backend = backend_id
        safe_update(self)

    def _toggle_advanced(self, e: ft.ControlEvent) -> None:
        self._advanced_section.visible = e.control.value
        self._config.use_preset = not e.control.value
        safe_update(self)

    def _handle_start(self, _e=None) -> None:
        if self._on_start_game:
            config = self._collect_config()
            logger.info("Start game requested config=%s", config)
            self._on_start_game(config)

    def _collect_config(self) -> Lc0GameConfig:
        if self._advanced_section.visible:
            threads = getattr(self, "_threads_field", None)
            if threads and threads.value:
                try:
                    self._config.threads = int(threads.value)
                except ValueError:
                    pass
        return self._config

    def _slider_row(self, label: str, default: float, min_val: float, max_val: float, step: float, attr_name: str) -> ft.Container:
        slider = ft.Slider(
            value=default,
            min=min_val,
            max=max_val,
            divisions=int((max_val - min_val) / step) if step > 0 else None,
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

    def _number_row(self, label: str, default: int, min_val: int, max_val: int, attr_name: str) -> ft.Container:
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
