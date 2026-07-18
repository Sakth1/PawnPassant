from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from pathlib import Path

import flet as ft
import chess

from ui.home_page import HomeView
from ui.board import ChessBoard
from ui.clockui import ClockUI
from ui.captured_pieces import CaputredPieces
from ui.settings_page import SettingsView
from ui.layout import AppLayout, resolve_app_layout
from ui.routing import RouteManager
from ui.setup_overlay import SetupOverlay
from core.bot_manager import BotManager
from core.engine_download import EngineDownloadConfig, download_and_extract, get_all_release_assets
from core.engine_verify import verify_engine_binary
from core.stockfish_config import (
    STOCKFISH_GITHUB_REPO,
    WINDOWS_DOWNLOAD_CONFIG,
    get_platform_download_configs,
    is_android,
    is_windows,
)
from utils.constants import (
    ASSET_DIR,
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    FONT_DIR,
    FONT_FAMILY,
    MIN_PAGE_HEIGHT,
    MIN_PAGE_WIDTH,
    NAVIGATION_BAR_HEIGHT,
)
from ui.task_toast import show_toast
from utils.dialogs import safe_pop_dialog, safe_update
from utils.events import (
    EngineBundledDetectedEvent,
    EngineDownloadFailedEvent,
    EngineDownloadReadyEvent,
    EngineInfoReadyEvent,
    GameEndedEvent,
    GameStartedEvent,
)
from utils.paths import (
    get_active_engine_path,
    get_bundled_engine_path,
    get_downloaded_engine_path,
    get_engine_dir,
)
from utils.game_state import GameAgainst, game_state
from utils.logging_config import reconfigure_logging
from utils.log_collector import build_error_report
from utils.models import StockfishGameConfig
from utils.settings import SettingsController
from utils.signals import bus
from ui.log_viewer_dialog import LogViewerDialog

logger = logging.getLogger(__name__)


def platform_from_page(page=None) -> str:
    try:
        if page is not None:
            p = getattr(page, "platform", None)
            if p is not None:
                val = getattr(p, "value", p)
                return str(val).strip().lower()
    except Exception:
        pass
    if "ANDROID_ROOT" in os.environ:
        return "android"
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


class ChessApp:
    def __init__(self, page: ft.Page, dev_mode: bool = False):
        logger.info("Initializing app shell dev_mode=%s", dev_mode)

        self._install_crash_handlers()

        self.page = page
        self.dev_mode = dev_mode
        self.layout: AppLayout = resolve_app_layout(
            DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT
        )

        self.bot_manager: BotManager | None = None
        self._setup_overlay: SetupOverlay | None = None
        self._pending_time_control: tuple[int, int] | None = None
        self._pending_engine_config: StockfishGameConfig | None = None
        self._checking_binary: bool = False
        self._log_viewer: LogViewerDialog | None = None

        reconfigure_logging(self.page)
        self.page.on_error = self._handle_flet_error

        self.page.fonts = {
            FONT_FAMILY: str(Path(FONT_DIR, "RobotoMono-VariableFont_wght.ttf"))
        }
        self.page.title = "Pawn Passant"
        self.page.window.icon = str(Path(ASSET_DIR, "PawnPassant.ico"))
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = ft.ScrollMode.AUTO

        self.settings_controller = SettingsController(page)
        self._file_picker = ft.FilePicker()
        self.board_view = ChessBoard()
        self.time_control_UI = ClockUI(
            on_draw=self._handle_draw_action,
            on_resign=self._handle_resign_action,
        )
        self.home_view = HomeView(
            on_time_control_selected=None,
            on_play_computer=self._handle_open_computer_setup,
            on_play_someone=self._handle_open_online_setup,
        )

        # Combined capture panel (backward compat for tests)
        self.piece_display = CaputredPieces()

        # Split capture panels for 3b layout
        self.opponent_captures = CaputredPieces(capturing_side=chess.BLACK)
        self.player_captures = CaputredPieces(capturing_side=chess.WHITE)

        self.time_control_UI._external_layout = True

        self.result_dialog_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.result_dialog_message = ft.Text(text_align=ft.TextAlign.CENTER)
        self.result_dialog = ft.AlertDialog(
            modal=True,
            title=self.result_dialog_title,
            content=self.result_dialog_message,
            actions=[
                ft.TextButton("New Game", on_click=self._handle_result_dialog_close)
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.pending_terminal_action: str | None = None
        self.confirm_action_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.confirm_action_message = ft.Text(text_align=ft.TextAlign.CENTER)
        self.confirm_action_dialog = ft.AlertDialog(
            modal=True,
            title=self.confirm_action_title,
            content=self.confirm_action_message,
            actions=[
                ft.TextButton("Cancel", on_click=self._handle_action_cancel),
                ft.FilledButton("Confirm", on_click=self._handle_action_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Board slot (used in both old test layout and new game layout)
        self.board_slot = ft.Container(
            content=self.board_view,
            alignment=ft.Alignment.CENTER,
        )

        # Backward compat slots kept for existing tests
        self.piece_display_slot = ft.Container(
            content=self.piece_display,
            alignment=ft.Alignment.CENTER,
        )
        self.clock_slot = ft.Container(
            content=self.time_control_UI,
            alignment=ft.Alignment.CENTER,
        )
        self.content_row = ft.ResponsiveRow(
            columns=12,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=self.layout.gap,
            run_spacing=self.layout.gap,
            controls=[self.piece_display_slot, self.board_slot, self.clock_slot],
        )

        # 3b layout: opponent timer + captures / board / player timer + captures + actions
        self.top_section = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=self.time_control_UI.black_timer, expand=1),
                    ft.Container(content=self.opponent_captures, expand=3),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

        self.bottom_section = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=self.time_control_UI.white_timer, expand=1),
                    ft.Container(content=self.player_captures, expand=2),
                    ft.Container(content=self.time_control_UI.action_bar, expand=1),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

        self.game_page_column = ft.Column(
            controls=[
                self.top_section,
                self.board_slot,
                self.bottom_section,
            ],
            spacing=self.layout.gap,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if self.dev_mode:
            self.position_selector = ft.Dropdown(
                label="Board setup",
                value="Start Position",
                width=self.layout.dev_control_width,
                options=[
                    ft.dropdown.Option(key=position_name, text=position_name)
                    for position_name in ChessBoard.TEST_POSITIONS.keys()
                ],
                on_select=self._handle_position_change,
                on_text_change=self._handle_position_change,
            )
            root_controls = [self.game_page_column]
        else:
            self.position_selector = None
            root_controls = [self.game_page_column]

        self.root_column = ft.Column(
            controls=root_controls,
            tight=True,
            spacing=self.layout.gap,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content_container = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.all(self.layout.padding),
            content=self.root_column,
        )
        self.safe_area = ft.SafeArea(
            expand=True,
            minimum_padding=0,
            content=self.content_container,
        )
        self.game_page_view = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=self.safe_area,
        )

        self.settings_view = SettingsView(
            self.settings_controller,
            file_picker=self._file_picker,
            on_open_log_viewer=self._show_log_viewer,
        )
        self.view_container = ft.Container(expand=True)

        route_to_index = {
            "/home": 0,
            "/game": 1,
            "/settings": 2,
        }
        route_views = {
            "/home": self.home_view,
            "/game": self.game_page_view,
            "/settings": self.settings_view,
        }
        self._route_manager = RouteManager(
            page=self.page,
            view_container=self.view_container,
            route_views=route_views,
            route_to_index=route_to_index,
        )

        self._route_manager.on_enter("/game", self._on_game_enter)
        self._route_manager.on_exit("/game", self._on_game_exit)

        self.page.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.icons.Icons.HOME, label="Home"),
                ft.NavigationBarDestination(icon=ft.icons.Icons.GAMES, label="Game"),
                ft.NavigationBarDestination(icon=ft.icons.Icons.SETTINGS, label="Settings"),
            ],
            on_change=self._handle_navigation_change,
        )

        self.page.on_route_change = self._route_manager.handle_route_change

        self.page.on_resize = self._handle_page_resize
        self.page.on_media_change = self._handle_page_resize
        bus.connect(GameStartedEvent, self._handle_game_started)
        bus.connect(GameEndedEvent, self._handle_game_ended)

        self.page.add(self.view_container)
        self._apply_responsive_layout()
        self.page.run_task(self.settings_controller.load)
        self._route_manager.navigate("/home")

    @staticmethod
    def _install_crash_handlers() -> None:
        def global_exc(exc_type, exc_value, exc_tb):
            logger.critical(
                "Unhandled exception: %s",
                "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip(),
            )
        sys.excepthook = global_exc
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.set_exception_handler(
            lambda _loop, ctx: logger.critical(
                "Asyncio exception handler: %s",
                ctx.get("message", ctx),
                exc_info=ctx.get("exception"),
            )
        )

    def _on_game_enter(self) -> None:
        self.board_view.on_enter()
        self.time_control_UI.on_enter()

    def _on_game_exit(self) -> None:
        self.time_control_UI.on_exit()
        self.board_view.on_exit()

    def _handle_navigation_change(self, event):
        self._route_manager.handle_navigation_change(event)

    def _resolve_page_dimensions(self) -> tuple[float, float]:
        page_width = getattr(self.page, "width", 0) or DEFAULT_PAGE_WIDTH
        page_height = getattr(self.page, "height", 0) or DEFAULT_PAGE_HEIGHT
        media = getattr(self.page, "media", None)
        padding = getattr(media, "padding", None)
        if padding is not None:
            page_width = max(MIN_PAGE_WIDTH, page_width - (getattr(padding, "left", 0) or 0) - (getattr(padding, "right", 0) or 0))
            page_height = max(MIN_PAGE_HEIGHT, page_height - (getattr(padding, "top", 0) or 0) - (getattr(padding, "bottom", 0) or 0))
        if getattr(self.page, "navigation_bar", None) is not None:
            page_height = max(MIN_PAGE_HEIGHT, page_height - NAVIGATION_BAR_HEIGHT)
        return page_width, page_height

    def _apply_responsive_layout(self):
        page_width, page_height = self._resolve_page_dimensions()
        self.layout = resolve_app_layout(page_width, page_height)
        self.board_view.apply_layout(self.layout)
        self.piece_display.apply_layout(self.layout)
        self.opponent_captures.apply_layout(self.layout)
        self.player_captures.apply_layout(self.layout)
        self.time_control_UI.apply_layout(self.layout)
        self.home_view.apply_layout(self.layout)
        self.settings_view.apply_layout(self.layout)

        # Backward-compat slot sizing for existing tests
        self.piece_display_slot.col = {"xs": 12, "md": self.layout.piece_col}
        self.board_slot.col = {"xs": 12, "md": self.layout.board_col}
        self.clock_slot.col = {"xs": 12, "md": self.layout.clock_col}

        # New 3b layout sizing
        self.content_row.spacing = self.layout.gap
        self.content_row.run_spacing = self.layout.gap
        self.game_page_column.spacing = self.layout.gap
        self.root_column.spacing = self.layout.gap
        self.safe_area.minimum_padding = 0
        self.content_container.padding = ft.Padding.all(self.layout.padding)
        self.result_dialog_title.size = max(18, int(self.layout.timer_font_size * 0.5))
        self.result_dialog_message.size = max(14, int(self.layout.timer_ms_size * 1.05))
        if self.position_selector is not None:
            self.position_selector.width = self.layout.dev_control_width

    def _handle_page_resize(self, _event):
        self._apply_responsive_layout()

    def _handle_position_change(self, e: ft.ControlEvent):
        selected_name = None
        if isinstance(e.data, str) and e.data:
            payload = e.data.strip()
            if payload.startswith("{"):
                try:
                    event_data = json.loads(payload)
                    selected_name = event_data.get("value") or event_data.get("key")
                except json.JSONDecodeError:
                    logger.warning("Failed to decode board setup payload=%s", payload, exc_info=True)
                    selected_name = payload
            else:
                selected_name = payload
        if not selected_name and self.position_selector is not None:
            selected_name = e.control.value or self.position_selector.value
        if isinstance(selected_name, str):
            selected_name = selected_name.strip()
        if selected_name not in ChessBoard.TEST_POSITIONS or self.position_selector is None:
            return
        self.position_selector.value = selected_name
        selected_fen = ChessBoard.TEST_POSITIONS[selected_name]
        logger.info("Loading developer board position name=%s", selected_name)
        self.board_view.load_position(selected_fen)
        self._pending_engine_config = None
        self._pending_time_control = game_state.time_control
        game_state.game_against = GameAgainst.COMPUTER
        self._launch_game()

    def _handle_game_started(self, _event: GameStartedEvent):
        safe_pop_dialog(self.page)
        self.result_dialog.open = False
        self.result_dialog_title.value = ""
        self.result_dialog_message.value = ""
        logger.info("Game started")

    def _handle_game_ended(self, event: GameEndedEvent):
        self.result_dialog_title.value = event.winner or "Game Over"
        self.result_dialog_message.value = event.message
        logger.info("Game ended winner=%s reason=%s message=%s", event.winner, event.reason, event.message)
        self.page.show_dialog(self.result_dialog)
        safe_update(self.page)

    def _handle_draw_action(self, _event=None):
        if game_state.game_over:
            logger.info("Ignoring draw action because game is already over")
            return
        settings = getattr(getattr(self, "settings_controller", None), "settings", None)
        if settings is not None and settings.confirm_draw:
            self._show_terminal_action_confirmation("draw", "Confirm draw", "End this game as a draw by agreement?")
            return
        self._emit_draw_agreement()

    def _emit_draw_agreement(self):
        bus.emit(GameEndedEvent(winner="Draw", reason="agreement", message="Draw by agreement."))
        logger.info("Draw agreement emitted")

    def _handle_resign_action(self, _event=None):
        if game_state.game_over:
            logger.info("Ignoring resign action because game is already over")
            return
        settings = getattr(getattr(self, "settings_controller", None), "settings", None)
        if settings is not None and settings.confirm_resign:
            self._show_terminal_action_confirmation("resign", "Confirm resignation", "Resign this game?")
            return
        self._emit_resignation()

    def _emit_resignation(self):
        winner = "Black" if self.board_view.game_manager.active_color() == chess.WHITE else "White"
        loser = "White" if winner == "Black" else "Black"
        bus.emit(GameEndedEvent(winner=winner, reason="resignation", message=f"{loser} resigned. {winner} wins."))
        logger.info("Resignation emitted loser=%s winner=%s", loser, winner)

    def _show_terminal_action_confirmation(self, action: str, title: str, message: str):
        if game_state.game_over:
            logger.info("Ignoring %s confirmation because game is already over", action)
            return
        self.pending_terminal_action = action
        logger.info("Showing terminal action confirmation action=%s", action)
        self.confirm_action_title.value = title
        self.confirm_action_message.value = message
        self.page.show_dialog(self.confirm_action_dialog)
        safe_update(self.page)

    def _handle_action_cancel(self, _event=None):
        self.pending_terminal_action = None
        logger.info("Terminal action cancelled")
        self.page.pop_dialog()
        safe_update(self.page)

    def _handle_action_confirm(self, _event=None):
        action = self.pending_terminal_action
        self.pending_terminal_action = None
        logger.info("Terminal action confirmed action=%s", action)
        self.page.pop_dialog()
        if game_state.game_over:
            safe_update(self.page)
            return
        if action == "draw":
            self._emit_draw_agreement()
        elif action == "resign":
            self._emit_resignation()
        safe_update(self.page)

    def _handle_result_dialog_close(self, _event=None):
        self.page.pop_dialog()
        self.result_dialog.open = False
        logger.info("Resetting game from result dialog")
        if self.position_selector is not None:
            self.position_selector.value = "Start Position"
        self.board_view.load_position()
        self.time_control_UI.set_time_control(self.time_control_UI.time_control)
        self._route_manager.navigate("/game")

    def _handle_open_computer_setup(self, time_control: tuple[int, int]) -> None:
        self._pending_time_control = time_control
        self._pending_engine_config = None

        logger.info("Opening computer setup with time_control=%s+%s", time_control[0], time_control[1])

        settings = self.settings_controller.settings

        bundled_path = get_bundled_engine_path(self.page)
        bundled_available = False
        bundled_version = ""
        if bundled_path is not None:
            valid, version = verify_engine_binary(str(bundled_path))
            bundled_available = valid
            if valid:
                bundled_version = version
                if not settings.engine_binary_path or settings.engine_source != "downloaded":
                    self.settings_controller.update(
                        engine_binary_path=str(bundled_path),
                        engine_source="bundled",
                    )

        downloaded_path = None
        if settings.engine_downloaded_path:
            dp = Path(settings.engine_downloaded_path)
            if dp.exists():
                valid, _ = verify_engine_binary(str(dp))
                if valid:
                    downloaded_path = settings.engine_downloaded_path

        binary_available = bundled_available or downloaded_path is not None

        self._setup_overlay = SetupOverlay(
            page=self.page,
            file_picker=self._file_picker,
            mode="computer",
            binary_available=binary_available,
            on_start_game=self._handle_engine_start,
            on_close=self._handle_overlay_closed,
            on_install_clicked=self._handle_overlay_install_clicked,
            on_binary_installed=self._handle_binary_installed,
            engine_name="Stockfish",
            bundled_version=bundled_version,
            has_downloaded_version=downloaded_path is not None,
            on_activate_downloaded=self._handle_activate_downloaded,
        )
        self._setup_overlay.open()

        if bundled_available:
            bus.emit(EngineBundledDetectedEvent(path=str(bundled_path), version=bundled_version))

        if not binary_available:
            self._checking_binary = True
            self.page.run_task(self._async_fetch_and_update_binary_info)

    def _handle_binary_installed(self, path: str) -> None:
        self.settings_controller.update(engine_binary_path=path)
        logger.info("Binary path saved to settings path=%s", path)

    def _handle_activate_downloaded(self) -> None:
        settings = self.settings_controller.settings
        if not settings.engine_downloaded_path:
            return
        path = settings.engine_downloaded_path
        valid, version = verify_engine_binary(path)
        if valid:
            self.settings_controller.update(
                engine_source="downloaded",
                engine_binary_path=path,
            )
            show_toast(self.page, f"Activated Stockfish {version}")
            logger.info("Activated downloaded Stockfish version=%s path=%s", version, path)
            if self._setup_overlay is not None:
                self._setup_overlay.show_config_panel()
        else:
            show_toast(self.page, f"Downloaded binary invalid: {version}", is_error=True)
            logger.error("Failed to activate downloaded binary: %s", version)

    async def _async_fetch_and_update_binary_info(self) -> None:
        logger.info("Fetching available Stockfish binary info...")
        if self._setup_overlay is not None:
            self._setup_overlay.set_fetching()

        platform_configs = get_platform_download_configs()
        if not platform_configs:
            self._checking_binary = False
            if self._setup_overlay is not None:
                self._setup_overlay.set_error("No Stockfish release found for your platform")
                self._setup_overlay.set_ready()
            return

        try:
            all_assets = await asyncio.to_thread(get_all_release_assets, STOCKFISH_GITHUB_REPO)
        except Exception as exc:
            logger.error("Failed to fetch release assets: %s", exc)
            self._checking_binary = False
            if self._setup_overlay is not None:
                self._setup_overlay.set_error(f"Failed to fetch release: {exc}")
            return

        cfg = platform_configs[0]
        config = EngineDownloadConfig(
            github_repo=cfg.github_repo,
            asset_name_filter=cfg.asset_name_filter,
            binary_name=cfg.binary_name,
            archive_binary_name=cfg.archive_binary_name,
            label=cfg.label,
            description=cfg.description,
        )
        matched = [a for a in all_assets if config.asset_name_filter in a.name]

        if not matched:
            logger.error("No Stockfish assets found matching filter=%s", config.asset_name_filter)
            self._checking_binary = False
            if self._setup_overlay is not None:
                self._setup_overlay.set_error("No Stockfish release found for your system")
            return

        self._checking_binary = False
        best_asset = matched[0]

        bus.emit(
            EngineInfoReadyEvent(
                release_tag="latest",
                asset_name=best_asset.name,
                asset_size_bytes=best_asset.size,
                asset_sha256=best_asset.sha256 or "",
                asset_platform=config.asset_name_filter,
                asset_arch="",
            )
        )

        if self._setup_overlay is not None:
            self._setup_overlay.set_ready(
                best_asset.name,
                best_asset.size,
                best_asset.sha256 or "",
                config.asset_name_filter,
                "",
            )

    def _handle_overlay_install_clicked(self) -> None:
        self.page.run_task(self._async_download_engine)

    async def _async_download_engine(self) -> None:
        logger.info("_async_download_engine ENTER")
        try:
            await self._do_download_engine()
        except Exception as exc:
            logger.critical("_async_download_engine unhandled exception: %s", exc, exc_info=True)

    async def _do_download_engine(self) -> None:
        logger.info("_do_download_engine ENTER")
        dest_dir = get_engine_dir(self.page)
        dest_dir.mkdir(parents=True, exist_ok=True)

        panel = self._setup_overlay._install_panel if self._setup_overlay else None

        platform_configs = get_platform_download_configs()
        if not platform_configs:
            if panel is not None:
                panel.set_error("No Stockfish config for this platform")
            return

        cfg = platform_configs[0]
        config = EngineDownloadConfig(
            github_repo=cfg.github_repo,
            asset_name_filter=cfg.asset_name_filter,
            binary_name=cfg.binary_name,
            archive_binary_name=cfg.archive_binary_name,
            label=cfg.label,
            description=cfg.description,
        )

        try:
            all_assets = await asyncio.to_thread(get_all_release_assets, STOCKFISH_GITHUB_REPO)
        except Exception as exc:
            logger.error("Failed to fetch release: %s", exc)
            if panel is not None:
                panel.set_error(f"Failed to fetch release: {exc}")
            bus.emit(EngineDownloadFailedEvent(error_message=str(exc)))
            return

        matched = [a for a in all_assets if config.asset_name_filter in a.name]
        if not matched:
            if panel is not None:
                panel.set_error("No Stockfish release found for your system")
            return

        best = matched[0]
        loop = asyncio.get_running_loop()

        async def _update_ui(downloaded: int, total: int) -> None:
            if panel is not None:
                panel.update_progress(downloaded, total)

        def on_progress(downloaded: int, total: int) -> None:
            asyncio.run_coroutine_threadsafe(_update_ui(downloaded, total), loop)

        try:
            extracted = await asyncio.to_thread(
                download_and_extract,
                best,
                config,
                dest_dir,
                on_progress,
            )
        except Exception as exc:
            logger.error("Stockfish download failed: %s", exc, exc_info=True)
            if panel is not None:
                panel.set_error(f"Download failed: {exc}")
            show_toast(self.page, f"Download failed: {exc}", is_error=True)
            bus.emit(EngineDownloadFailedEvent(error_message=str(exc)))
            return

        path = str(extracted.get(config.binary_name, ""))
        if not path:
            logger.error("Extracted binary not found in archive")
            if panel is not None:
                panel.set_error("Binary not found in downloaded archive")
            bus.emit(EngineDownloadFailedEvent(error_message="Binary not found in archive"))
            return

        self.settings_controller.update(
            engine_downloaded_path=path,
            engine_source="bundled",
        )
        logger.info("Stockfish downloaded successfully path=%s", path)

        bus.emit(EngineDownloadReadyEvent(download_path=path, release_tag="latest"))

        if panel is not None:
            panel.on_download_complete(path)
            panel.show_downloaded_available(version)

    def _handle_open_online_setup(self, time_control: tuple[int, int]) -> None:
        self._pending_time_control = time_control
        logger.info("Opening online setup with time_control=%s+%s", time_control[0], time_control[1])
        self._setup_overlay = SetupOverlay(
            page=self.page,
            file_picker=self._file_picker,
            mode="online",
            on_play_local=self._handle_local_play,
            on_close=self._handle_overlay_closed,
        )
        self._setup_overlay.open()

    def _handle_engine_start(self, config: StockfishGameConfig) -> None:
        self._pending_engine_config = config
        logger.info("Starting engine game config=preset=%s", config)
        self._setup_overlay = None
        game_state.game_against = GameAgainst.COMPUTER
        self._launch_game()

    def _handle_local_play(self) -> None:
        logger.info("Starting local flip-board game")
        self._setup_overlay = None
        game_state.game_against = GameAgainst.LOCAL
        self._launch_game()

    def _handle_overlay_closed(self) -> None:
        logger.info("Setup overlay closed without starting game")
        self._setup_overlay = None
        self._pending_time_control = None
        self._pending_engine_config = None

    def _launch_game(self) -> None:
        tc = self._pending_time_control
        if tc is None:
            tc = game_state.time_control
        self.time_control_UI.set_time_control(tc)
        game_state.time_control = tc

        if self.position_selector is not None:
            self.position_selector.value = "Start Position"
        self.board_view.load_position()

        self._route_manager.swap_view("/game")
        self.page.run_task(self._async_navigate_and_start)

    async def _async_navigate_and_start(self) -> None:
        if game_state.game_against == GameAgainst.COMPUTER and self.bot_manager is None:
            config = self._pending_engine_config or StockfishGameConfig()
            settings = self.settings_controller.settings

            binary_path = get_active_engine_path(
                self.page,
                source=settings.engine_source,
                downloaded_path=settings.engine_downloaded_path,
            )
            if binary_path is None and settings.engine_binary_path:
                binary_path = Path(settings.engine_binary_path)

            if binary_path and binary_path.exists():
                self.bot_manager = BotManager(
                    engine_path=str(binary_path),
                    config=config,
                    on_bot_move=self.board_view.play_uci_move,
                    page=self.page,
                )
                logger.info("Created BotManager with binary=%s", binary_path)
                self.bot_manager.start()

        await self.page.push_route("/game")
        self._on_game_enter()
        bus.emit(GameStartedEvent(opponent_nature=game_state.game_against))

    def _show_log_viewer(self) -> None:
        if self._log_viewer is None or self._log_viewer not in self.page.overlay:
            self._log_viewer = LogViewerDialog(page=self.page, on_close=self._handle_log_viewer_closed)
        self._log_viewer.open()

    def _handle_log_viewer_closed(self) -> None:
        self._log_viewer = None

    def _handle_flet_error(self, e: ft.ControlEvent) -> None:
        error_data = getattr(e, "data", str(e))
        logger.error("Flet runtime error: %s", error_data)
        show_toast(self.page, "An unexpected error occurred", is_error=True)


def entry_point(page: ft.Page):
    dev_mode = os.getenv("PAWNPASSANT_DEV", "").strip().lower() in {"1", "true", "yes", "dev"}
    logger.info("Entry point invoked dev_mode=%s", dev_mode)
    ChessApp(page, dev_mode=dev_mode)
