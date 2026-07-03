from __future__ import annotations

import asyncio
import logging
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

import flet as ft

from ui.engine_setup_panel import EngineConfigPanel, EngineInstallPanel
from ui.online_setup_panel import OnlineSetupPanel
from ui.task_toast import show_toast
from core.engine_verify import verify_engine_binary
from utils.models import Lc0GameConfig

logger = logging.getLogger(__name__)


def _resolve_archive_to_binary(path: Path, engine_name: str = "lc0") -> Path:
    suffix = path.suffix.lower()
    is_tar_gz = suffix == ".gz" and path.name.lower().endswith(".tar.gz")
    is_tgz = suffix == ".tgz"

    if suffix not in (".zip", ".gz", ".tgz", ".tar") and not is_tar_gz:
        return path

    if not path.exists():
        return path

    tmp_dir = Path(tempfile.mkdtemp(prefix="engine_extract_"))
    logger.info("Extracting %s -> %s", path, tmp_dir)

    try:
        if suffix == ".zip":
            with zipfile.ZipFile(str(path), "r") as zf:
                zf.extractall(str(tmp_dir))
        elif is_tar_gz or is_tgz:
            with tarfile.open(str(path), "r:gz") as tf:
                tf.extractall(str(tmp_dir))
        elif suffix == ".tar":
            with tarfile.open(str(path), "r:") as tf:
                tf.extractall(str(tmp_dir))
        else:
            return path

        candidates = [f for f in tmp_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]

        if not candidates:
            logger.warning("No files found in archive %s", path)
            return path

        if sys.platform == "win32":
            exe_files = [f for f in candidates if f.suffix == ".exe"]
            if exe_files:
                candidates = exe_files
        else:
            noext_files = [f for f in candidates if not f.suffix]
            if noext_files:
                candidates = noext_files

        best = max(candidates, key=lambda f: f.stat().st_size)
        exe_name = f"{engine_name}.exe" if sys.platform == "win32" else engine_name
        exe_path = path.parent / exe_name

        shutil.move(str(best), str(exe_path))
        try:
            current = exe_path.stat().st_mode
            exe_path.chmod(current | 0o111)
        except OSError:
            pass

        logger.info("Extracted %s -> %s", best.name, exe_path)
        return exe_path.resolve()

    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        logger.error("Extraction failed for %s: %s", path, exc, exc_info=True)
        return path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class SetupOverlay(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        file_picker: ft.FilePicker,
        mode: str = "computer",
        binary_available: bool = False,
        on_start_game: Callable[[Lc0GameConfig], None] | None = None,
        on_play_local: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
        on_install_clicked: Callable[[], None] | None = None,
        on_binary_installed: Callable[[str], None] | None = None,
        asset_name: str = "",
        asset_size_bytes: int = 0,
        engine_name: str = "Leela Chess Zero",
        bundled_version: str = "",
        has_downloaded_version: bool = False,
        on_activate_downloaded: Callable[[], None] | None = None,
        available_networks: list | None = None,
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
        self._engine_name = engine_name
        self._bundled_version = bundled_version
        self._has_downloaded_version = has_downloaded_version
        self._on_activate_downloaded = on_activate_downloaded
        self._available_networks = available_networks

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
            content=ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO),
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

        self._config_panel: EngineConfigPanel | None = None
        self._install_panel: EngineInstallPanel | None = None
        self._online_panel: OnlineSetupPanel | None = None

        if mode == "computer":
            if binary_available:
                self._show_config_panel()
            else:
                self._show_install_panel()
        else:
            self._show_online_panel()

    def set_fetching(self) -> None:
        if self._install_panel is not None:
            self._install_panel.set_fetching()

    def set_ready(self, name: str, size_bytes: int, sha256: str = "", platform: str = "", arch: str = "") -> None:
        self._asset_name = name
        self._asset_size_bytes = size_bytes
        if self._install_panel is not None:
            self._install_panel.set_ready(name, size_bytes, sha256, platform, arch)

    def set_error(self, message: str) -> None:
        if self._install_panel is not None:
            self._install_panel.set_error(message)

    def update_asset_info(self, name: str, size_bytes: int) -> None:
        self._asset_name = name
        self._asset_size_bytes = size_bytes
        if self._install_panel is not None:
            self._install_panel.set_asset_info(name, size_bytes)

    def open(self) -> None:
        if self not in self._page.overlay:
            self.visible = True
            self._page.overlay.append(self)
            self._page.update()
            logger.info("Overlay opened mode=%s engine=%s", self._mode, self._engine_name)

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
        self._install_panel = EngineInstallPanel(
            on_installed=lambda: self._show_config_panel(),
            on_install_clicked=self._on_install_clicked,
            on_browse_manual=self._on_browse_manual,
            asset_name=self._asset_name,
            asset_size_bytes=self._asset_size_bytes,
            engine_name=self._engine_name,
            bundled_version=self._bundled_version,
            has_downloaded_version=self._has_downloaded_version,
            on_activate_downloaded=self._on_activate_downloaded,
        )
        self._panel_container.content = self._install_panel
        self._page.update()

    def _show_config_panel(self) -> None:
        logger.debug("Showing config panel")
        self._config_panel = EngineConfigPanel(
            on_start_game=self._on_start_game_callback,
            on_back=self._show_install_panel,
            available_networks=self._available_networks,
        )
        self._panel_container.content = self._config_panel
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

    def _on_start_game_callback(self, config: Lc0GameConfig) -> None:
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
            dialog_title="Select engine executable or archive",
        )
        if not files:
            logger.info("File picker cancelled by user")
            return
        path = files[0].path
        if not path:
            logger.warning("File picker returned empty path")
            return

        if self._install_panel:
            self._install_panel.set_verifying()
        await asyncio.sleep(0)

        logger.info("User selected path=%s", path)
        loop = asyncio.get_running_loop()
        exe_path = await loop.run_in_executor(
            None, lambda: str(_resolve_archive_to_binary(Path(path)))
        )
        valid, version = await loop.run_in_executor(
            None, verify_engine_binary, exe_path
        )

        if valid:
            logger.info("Picked binary verified version=%s path=%s", version, path)
            if self._install_panel:
                self._install_panel.set_asset_info(Path(path).name, Path(path).stat().st_size)
            show_toast(self._page, f"Valid engine: {version}")
            self._on_installed_with_path(path)
        else:
            logger.warning("Picked binary invalid path=%s error=%s", path, version)
            if self._install_panel:
                self._install_panel.set_error(version)
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
