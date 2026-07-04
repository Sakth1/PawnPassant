from __future__ import annotations

import logging
import time
from typing import Callable

import flet as ft

from core.lc0_config import ALL_BACKENDS, DEFAULT_NETWORKS, NetworkInfo, recommend_backends_for_system
from core.difficulty_presets import elo_to_playouts, elo_to_temperature, rating_context
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
    ):
        super().__init__(spacing=16, scroll=ft.ScrollMode.AUTO)
        self._on_installed = on_installed
        self._on_install_clicked = on_install_clicked
        self._on_browse_manual = on_browse_manual
        self._on_activate_downloaded = on_activate_downloaded
        self._engine_name = engine_name
        self._download_started = False
        self._download_completed = False
        self._total_bytes: int = 0
        self._phase: str = "fetching"
        self._variants: list[dict] = []
        self._selected_variant_idx: int = 0

        self._heading = ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Icon(
                        engine_icon or ft.Icons.PRECISION_MANUFACTURING,
                        size=32,
                        color=ft.Colors.PRIMARY,
                    ),
                    width=56,
                    height=56,
                    border_radius=28,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PRIMARY),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text("Select Lc0 Engine Variant", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Choose the version that matches your hardware", size=12, color=ft.Colors.GREY_400),
                    ],
                ),
            ],
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

        self._variant_cards = ft.Column(spacing=8)
        self._cards_container = ft.Container(
            visible=False,
            content=self._variant_cards,
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

        self.controls = [
            self._heading,
            self._cards_container,
            ft.Divider(height=1, visible=False),
            self._bundled_status,
            self._downloaded_row,
            self._phase_text,
            self._progress_bar,
            ft.Row(
                spacing=24,
                controls=[
                    self._percentage_text,
                    self._bytes_text,
                    self._speed_text,
                    self._time_text,
                ],
            ),
            self._error_banner,
            self._buttons_row,
            self._info_banner,
        ]

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
        self._error_banner.visible = False
        self._install_button.disabled = True
        self._install_button.text = "Install"
        self._install_button.icon = ft.Icons.DOWNLOAD
        self._info_banner.visible = False
        safe_update(self)

    @property
    def selected_variant(self) -> dict | None:
        if self._variants and 0 <= self._selected_variant_idx < len(self._variants):
            return self._variants[self._selected_variant_idx]
        return None

    @staticmethod
    def _variant_icon(label: str) -> ft.Icons:
        lbl = label.lower()
        if "cpu" in lbl:
            return ft.Icons.MEMORY
        if "directml" in lbl or "dml" in lbl:
            return ft.Icons.HARDWARE
        if "cuda" in lbl:
            return ft.Icons.HARDWARE
        if "cudnn" in lbl:
            return ft.Icons.SPEED
        if "tensorrt" in lbl:
            return ft.Icons.BOLT
        if "android" in lbl:
            return ft.Icons.ANDROID
        if "macos" in lbl or "apple" in lbl:
            return ft.Icons.APPLE
        return ft.Icons.PRECISION_MANUFACTURING

    def _build_variant_card(self, variant: dict, index: int) -> ft.Container:
        selected = index == self._selected_variant_idx
        assets = variant.get("assets", [])
        first_asset = assets[0] if assets else None
        asset_name = first_asset.name if first_asset else ""
        asset_size = _format_bytes(first_asset.size) if first_asset else ""
        return ft.Container(
            padding=ft.Padding.all(16),
            border_radius=12,
            border=ft.Border.all(
                2 if selected else 1,
                ft.Colors.PRIMARY if selected else ft.Colors.OUTLINE_VARIANT,
            ),
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.PRIMARY) if selected else None,
            ink=True,
            on_click=lambda _, i=index: self._select_variant(i),
            content=ft.Row(
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        self._variant_icon(variant["label"]),
                        size=32,
                        color=ft.Colors.PRIMARY if selected else ft.Colors.GREY_400,
                    ),
                    ft.Column(
                        spacing=4,
                        expand=True,
                        controls=[
                            ft.Text(
                                variant["label"],
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.PRIMARY if selected else None,
                            ),
                            ft.Text(
                                variant.get("description", ""),
                                size=12,
                                color=ft.Colors.GREY_400,
                            ),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Text(
                                        asset_size,
                                        size=11,
                                        color=ft.Colors.GREY_500,
                                    ),
                                    ft.Text(
                                        asset_name,
                                        size=11,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE,
                        size=24,
                        color=ft.Colors.PRIMARY,
                        visible=selected,
                    ),
                ],
            ),
        )

    def _select_variant(self, index: int) -> None:
        self._selected_variant_idx = index
        self._rebuild_variant_cards()
        safe_update(self)

    def _rebuild_variant_cards(self) -> None:
        self._variant_cards.controls = [
            self._build_variant_card(v, i)
            for i, v in enumerate(self._variants)
        ]

    def set_variants(self, variants: list[dict]) -> None:
        self._variants = list(variants)
        if not variants:
            self._cards_container.visible = False
            safe_update(self)
            return
        self._selected_variant_idx = 0
        self._rebuild_variant_cards()
        self._cards_container.visible = True
        safe_update(self)

    def set_ready(self, asset_name: str = "", asset_size_bytes: int = 0, sha256: str = "", platform: str = "", arch: str = "") -> None:
        self._phase = "ready"
        self._phase_text.value = f"Ready to install {self._engine_name} engine"
        self._progress_bar.visible = False
        self._percentage_text.visible = False
        self._bytes_text.visible = False
        self._speed_text.visible = False
        self._time_text.visible = False
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

    def set_bundled_status(self, version: str) -> None:
        self._bundled_status.visible = True
        self._bundled_status.controls[1].value = f"{self._engine_name} {version} (bundled)"
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
        safe_update(self)

    def set_asset_info(self, name: str = "", size_bytes: int = 0) -> None:
        safe_update(self)

    def update_variant_asset_info(self, idx: int, name: str, size_bytes: int) -> None:
        self._rebuild_variant_cards()
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

        self._elo = 1500

        self._elo_slider = ft.Slider(
            min=100,
            max=3000,
            divisions=29,
            value=1500,
            label="{value}",
            width=400,
            on_change=self._handle_elo_change,
        )

        self._difficulty_label = ft.Text(
            "Intermediate (~1500 ELO)",
            size=14,
            weight=ft.FontWeight.BOLD,
        )

        self._rating_context_text = ft.Text(
            rating_context(1500),
            size=12,
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
                ft.Divider(height=1),
                ft.Text("Neural Network", weight=ft.FontWeight.BOLD, size=14),
                self._network_dropdown,
                self._network_desc,
                ft.Divider(height=1),
                ft.Text("Compute Backend", weight=ft.FontWeight.BOLD, size=14),
                self._backend_dropdown,
                self._backend_desc,
                ft.Divider(height=1),
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
            ft.Text("Skill Level", weight=ft.FontWeight.BOLD, size=14),
            self._elo_slider,
            self._difficulty_label,
            self._rating_context_text,
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

    def _handle_elo_change(self, e: ft.ControlEvent) -> None:
        self._elo = int(e.control.value)
        label = self._elo_label_name(self._elo)
        self._difficulty_label.value = f"{label} (~{self._elo} ELO)"
        self._rating_context_text.value = rating_context(self._elo)
        safe_update(self)

    @staticmethod
    def _elo_label_name(elo: int) -> str:
        if elo >= 2600:
            return "Master"
        if elo >= 2000:
            return "Expert"
        if elo >= 1400:
            return "Advanced"
        if elo >= 800:
            return "Intermediate"
        if elo >= 400:
            return "Casual"
        return "Beginner"

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
        self._config.elo = self._elo
        self._config.max_playouts = elo_to_playouts(self._elo)
        self._config.temperature = elo_to_temperature(self._elo)

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
