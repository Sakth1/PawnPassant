from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable

import flet as ft

from ui.stockfish_setup_panel import StockfishConfigPanel, StockfishInstallPanel
from ui.online_setup_panel import OnlineSetupPanel
from ui.task_toast import show_toast
from core.binary_verifier import verify_stockfish_binary
from core.download_manager import _resolve_archive
from utils.models import StockfishGameConfig

logger = logging.getLogger(__name__)


class SetupOverlay(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        file_picker: ft.FilePicker,
        mode: str = "computer",
        binary_available: bool = False,
        on_start_game: Callable[[StockfishGameConfig], None] | None = None,
        on_play_local: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
        on_install_clicked: Callable[[], None] | None = None,
        on_binary_installed: Callable[[str], None] | None = None,
        asset_name: str = "",
        asset_size_bytes: int = 0,
    ):
        super().__init__()
        self._page = page
        self._file_picker = file_picker
        self._mode = mode
        self._on_start_game = on_start_game
        self._on_play_local = on_play_local
        self._on_close = on_close
        self._on_install_clicked = on_install_clicked
        self._on_binary_installed = on_binary_installed
        self._asset_name = asset_name
        self._asset_size_bytes = asset_size_bytes

        self._title_text = ft.Text(
            "Play vs Computer" if mode == "computer" else "Play Someone",
            weight=ft.FontWeight.BOLD,
            size=22,
        )

        self._close_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            on_click=lambda _: self.close(),
        )

        self._header_row = ft.Row(
            controls=[self._title_text, self._close_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._panel_container = ft.Container(
            expand=True,
            content=ft.Column(
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

        card = ft.Container(
            expand=True,
            content=ft.Column(
                tight=False,
                spacing=16,
                controls=[
                    self._header_row,
                    ft.Divider(height=1),
                    self._panel_container,
                ],
            ),
        )

        self._panel_wrapper = ft.Container(
            width=min(page.width * 0.9, 640) if page.width else 640,
            height=min(page.height * 0.85, 600) if page.height else 600,
            bgcolor=ft.Colors.with_opacity(0.97, ft.Colors.GREY_900),
            border_radius=16,
            padding=ft.Padding.all(24),
            content=card,
        )

        self.content = ft.Stack(
            expand=True,
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
                    on_click=lambda _: self.close(),
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=self._panel_wrapper,
                ),
            ],
        )
        self.visible = False

        self._stockfish_config_panel: StockfishConfigPanel | None = None
        self._stockfish_install_panel: StockfishInstallPanel | None = None
        self._online_panel: OnlineSetupPanel | None = None

        if mode == "computer":
            if binary_available:
                self._show_config_panel()
            else:
                self._show_install_panel()
        else:
            self._show_online_panel()

    def set_fetching(self) -> None:
        if self._stockfish_install_panel is not None:
            self._stockfish_install_panel.set_fetching()

    def set_ready(self, name: str, size_bytes: int) -> None:
        self._asset_name = name
        self._asset_size_bytes = size_bytes
        if self._stockfish_install_panel is not None:
            self._stockfish_install_panel.set_ready(name, size_bytes)
            logger.info("Install panel set ready name=%s size=%d", name, size_bytes)

    def set_error(self, message: str) -> None:
        if self._stockfish_install_panel is not None:
            self._stockfish_install_panel.set_error(message)
            logger.info("Install panel set error message=%s", message)

    def update_asset_info(self, name: str, size_bytes: int) -> None:
        self._asset_name = name
        self._asset_size_bytes = size_bytes
        if self._stockfish_install_panel is not None:
            self._stockfish_install_panel.set_asset_info(name, size_bytes)
            logger.info("Asset info pushed to install panel name=%s", name)

    def open(self) -> None:
        if self not in self._page.overlay:
            self.visible = True
            self._page.overlay.append(self)
            self._page.update()
            logger.info("Overlay opened mode=%s", self._mode)

    def close(self) -> None:
        self.visible = False
        if self in self._page.overlay:
            self._page.overlay.remove(self)
        self._page.update()
        logger.info("Overlay closed mode=%s", self._mode)
        if self._on_close:
            self._on_close()

    def show_install_panel(self) -> None:
        self._show_install_panel()

    def show_config_panel(self) -> None:
        self._show_config_panel()

    def _show_install_panel(self) -> None:
        logger.debug("Showing install panel")
        self._stockfish_install_panel = StockfishInstallPanel(
            on_installed=lambda: self._show_config_panel(),
            on_install_clicked=self._on_install_clicked,
            on_browse_manual=self._on_browse_manual,
            asset_name=self._asset_name,
            asset_size_bytes=self._asset_size_bytes,
        )
        self._panel_container.content = self._stockfish_install_panel
        self._page.update()

    def _show_config_panel(self) -> None:
        logger.debug("Showing config panel")
        self._stockfish_config_panel = StockfishConfigPanel(
            on_start_game=self._on_start_game_callback,
            on_back=self._show_install_panel if not self._binary_check() else None,
        )
        self._panel_container.content = self._stockfish_config_panel
        self._page.update()

    def _show_online_panel(self) -> None:
        logger.debug("Showing online panel")
        self._online_panel = OnlineSetupPanel(
            on_play_local=self._on_play_local_callback,
            on_create_room=self._on_create_room,
            on_join_room=self._on_join_room,
        )
        self._panel_container.content = self._online_panel
        self._page.update()

    def _binary_check(self) -> bool:
        return bool(self._page and hasattr(self._page, "session") and False)

    def _on_start_game_callback(self, config: StockfishGameConfig) -> None:
        self.close()
        if self._on_start_game:
            self._on_start_game(config)

    def _on_play_local_callback(self) -> None:
        self.close()
        if self._on_play_local:
            self._on_play_local()

    def _on_browse_manual(self) -> None:
        logger.info("Manual binary browse requested")
        self._page.run_task(self._async_pick_file)

    async def _async_pick_file(self) -> None:
        files = await self._file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["exe", "bin", "zip", ""],
            dialog_title="Select Stockfish executable or archive",
        )
        if not files:
            logger.info("File picker cancelled by user")
            return
        path = files[0].path
        if not path:
            logger.warning("File picker returned empty path")
            return

        if self._stockfish_install_panel:
            self._stockfish_install_panel.set_verifying()
        await asyncio.sleep(0)

        logger.info("User selected path=%s", path)
        loop = asyncio.get_running_loop()
        exe_path = await loop.run_in_executor(
            None, lambda: str(_resolve_archive(Path(path)))
        )
        valid, version = await loop.run_in_executor(
            None, verify_stockfish_binary, exe_path
        )

        if valid:
            logger.info("Picked binary verified version=%s path=%s", version, path)
            if self._stockfish_install_panel:
                self._stockfish_install_panel.set_asset_info(
                    Path(path).name, Path(path).stat().st_size
                )
            show_toast(self._page, f"Valid Stockfish binary: {version}")
            self._on_installed_with_path(path)
        else:
            logger.warning("Picked binary invalid path=%s error=%s", path, version)
            if self._stockfish_install_panel:
                self._stockfish_install_panel.set_error(version)
            show_toast(self._page, version, is_error=True)

    def _on_installed_with_path(self, path: str) -> None:
        logger.info("Binary installed via manual selection path=%s", path)
        if self._on_binary_installed:
            self._on_binary_installed(path)
        self.show_config_panel()

    def _on_create_room(self) -> None:
        logger.info("Create room requested (WIP)")

    def _on_join_room(self, room_code: str) -> None:
        logger.info("Join room requested code=%s (WIP)", room_code)
