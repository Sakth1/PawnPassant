"""Top-level application wiring for the Pawn Passant interface.

``ChessApp`` composes independent Flet controls into one routed application,
subscribes to game-level events, and owns app-shell concerns such as dialogs,
navigation, responsive layout, settings loading, and developer-only board setup.
"""

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
from core.download_manager import StockfishDownloadManager
from core.binary_verifier import verify_stockfish_binary
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
    GameEndedEvent,
    GameStartedEvent,
    StockfishDownloadFailedEvent,
    StockfishInfoReadyEvent,
)
from utils.paths import get_stockfish_dir
from utils.game_state import GameAgainst, game_state
from utils.models import StockfishGameConfig
from utils.settings import SettingsController
from utils.signals import bus

logger = logging.getLogger(__name__)


class ChessApp:
    """Build page layout, navigation, dialogs, and optional developer controls."""

    def __init__(self, page: ft.Page, dev_mode: bool = False):
        """Create and attach the app shell to a Flet page."""

        logger.info("Initializing app shell dev_mode=%s", dev_mode)

        self._install_crash_handlers()

        #: Flet page owned by the running application.
        self.page = page
        #: Whether developer-only controls such as FEN presets are visible.
        self.dev_mode = dev_mode
        #: Current responsive layout snapshot shared by child views.
        self.layout: AppLayout = resolve_app_layout(
            DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT
        )

        self.bot_manager: BotManager | None = None
        self._setup_overlay: SetupOverlay | None = None
        self._pending_time_control: tuple[int, int] | None = None
        self._pending_stockfish_config: StockfishGameConfig | None = None
        self._stockfish_downloader: StockfishDownloadManager | None = None
        self._checking_binary: bool = False

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
        # Child controls are long-lived; route changes swap which one is visible
        # rather than reconstructing game state on every navigation event.
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
        self.piece_display = CaputredPieces()
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

        self.content_row = ft.ResponsiveRow(
            columns=12,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=self.layout.gap,
            run_spacing=self.layout.gap,
            controls=[],
        )

        self.board_slot = ft.Container(
            content=self.board_view,
            alignment=ft.Alignment.CENTER,
            col={"xs": 12, "md": 7},
        )
        self.clock_slot = ft.Container(
            content=self.time_control_UI,
            alignment=ft.Alignment.CENTER,
            col={"xs": 12, "md": 2},
        )
        self.piece_display_slot = ft.Container(
            content=self.piece_display,
            alignment=ft.Alignment.CENTER,
            col={"xs": 12, "md": 3},
        )
        self.content_row.controls = [
            self.piece_display_slot,
            self.board_slot,
            self.clock_slot,
        ]

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
            root_controls = [self.content_row]
        else:
            self.position_selector = None
            root_controls = [self.content_row]

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

        self.settings_view = SettingsView(self.settings_controller, file_picker=self._file_picker)
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

        # Register lifecycle callbacks so that services only start after
        # the game view is attached to the page tree.
        self._route_manager.on_enter("/game", self._on_game_enter)
        self._route_manager.on_exit("/game", self._on_game_exit)

        # Add NavigationBar with at least 2 destinations
        self.page.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.HOME,
                    label="Home",
                    visible=True,
                ),
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.GAMES,
                    label="Game",
                    visible=True,
                ),
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.SETTINGS,
                    label="Settings",
                    visible=True,
                ),
            ],
            on_change=self._route_manager.handle_navigation_change,
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
                "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                ).rstrip(),
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
            )
        )

    # ── lifecycle callbacks ─────────────────────────────────────────────

    def _on_game_enter(self) -> None:
        """Start game services when the game view is mounted.

        Called by :class:`RouteManager` after the game page is attached to
        the page tree, so clock ticks and board interactions never race
        against navigation.
        """
        self.board_view.on_enter()
        self.time_control_UI.on_enter()

    def _on_game_exit(self) -> None:
        """Stop game services when the game view is unmounted."""
        self.time_control_UI.on_exit()
        self.board_view.on_exit()

    def _handle_navigation_change(self, event):
        """Handle navigation bar tab changes."""

        self._route_manager.handle_navigation_change(event)

    def _navigate_to(self, route: str) -> None:
        """Show a route immediately and sync it to Flet navigation history."""

        self._route_manager.navigate(route)

    def _resolve_page_dimensions(self) -> tuple[float, float]:
        """Return usable page dimensions after safe-area and nav adjustments."""

        page_width = getattr(self.page, "width", 0) or DEFAULT_PAGE_WIDTH
        page_height = getattr(self.page, "height", 0) or DEFAULT_PAGE_HEIGHT

        media = getattr(self.page, "media", None)
        padding = getattr(media, "padding", None)
        if padding is not None:
            page_width = max(
                MIN_PAGE_WIDTH,
                page_width
                - (getattr(padding, "left", 0) or 0)
                - (getattr(padding, "right", 0) or 0),
            )
            page_height = max(
                MIN_PAGE_HEIGHT,
                page_height
                - (getattr(padding, "top", 0) or 0)
                - (getattr(padding, "bottom", 0) or 0),
            )
        if getattr(self.page, "navigation_bar", None) is not None:
            page_height = max(MIN_PAGE_HEIGHT, page_height - NAVIGATION_BAR_HEIGHT)

        return page_width, page_height

    def _apply_responsive_layout(self):
        """Resolve and apply responsive metrics to every child view."""

        page_width, page_height = self._resolve_page_dimensions()
        self.layout = resolve_app_layout(page_width, page_height)

        self.board_view.apply_layout(self.layout)
        self.piece_display.apply_layout(self.layout)
        self.time_control_UI.apply_layout(self.layout)
        self.home_view.apply_layout(self.layout)
        self.settings_view.apply_layout(self.layout)

        self.content_row.spacing = self.layout.gap
        self.content_row.run_spacing = self.layout.gap
        self.piece_display_slot.col = {"xs": 12, "md": self.layout.piece_col}
        self.board_slot.col = {"xs": 12, "md": self.layout.board_col}
        self.clock_slot.col = {"xs": 12, "md": self.layout.clock_col}
        self.root_column.spacing = self.layout.gap
        self.safe_area.minimum_padding = 0
        self.content_container.padding = ft.Padding.all(self.layout.padding)
        self.result_dialog_title.size = max(18, int(self.layout.timer_font_size * 0.5))
        self.result_dialog_message.size = max(14, int(self.layout.timer_ms_size * 1.05))

        if self.position_selector is not None:
            self.position_selector.width = self.layout.dev_control_width

    def _handle_page_resize(self, _event):
        """Recalculate layout after Flet reports size or media changes."""

        self._apply_responsive_layout()

    def _handle_position_change(self, e: ft.ControlEvent):
        """Load a canned board position selected from the developer dropdown."""

        selected_name = None

        if isinstance(e.data, str) and e.data:
            payload = e.data.strip()
            if payload.startswith("{"):
                try:
                    event_data = json.loads(payload)
                    selected_name = event_data.get("value") or event_data.get("key")
                except json.JSONDecodeError:
                    logger.warning("Failed to decode board setup payload=%s", payload)
                    selected_name = payload
            else:
                selected_name = payload

        if not selected_name and self.position_selector is not None:
            selected_name = e.control.value or self.position_selector.value

        if isinstance(selected_name, str):
            selected_name = selected_name.strip()

        if (
            selected_name not in ChessBoard.TEST_POSITIONS
            or self.position_selector is None
        ):
            return

        self.position_selector.value = selected_name
        selected_fen = ChessBoard.TEST_POSITIONS[selected_name]
        logger.info("Loading developer board position name=%s", selected_name)
        self.board_view.load_position(selected_fen)
        self._pending_stockfish_config = None
        self._pending_time_control = game_state.time_control
        game_state.game_against = GameAgainst.COMPUTER
        self._launch_game()

    def _handle_game_started(self, _event: GameStartedEvent):
        """Clear terminal dialogs and return the shell to active-game state."""

        safe_pop_dialog(self.page)
        self.result_dialog.open = False
        self.result_dialog_title.value = ""
        self.result_dialog_message.value = ""
        logger.info("Game started")

    def _handle_game_ended(self, event: GameEndedEvent):
        """Show the result dialog for a terminal game event."""

        self.result_dialog_title.value = event.winner or "Game Over"
        self.result_dialog_message.value = event.message
        logger.info(
            "Game ended winner=%s reason=%s message=%s",
            event.winner,
            event.reason,
            event.message,
        )
        self.page.show_dialog(self.result_dialog)
        safe_update(self.page)

    def _handle_draw_action(self, _event=None):
        """Handle draw button clicks, including optional confirmation."""

        if game_state.game_over:
            logger.info("Ignoring draw action because game is already over")
            return
        settings = getattr(getattr(self, "settings_controller", None), "settings", None)
        if settings is not None and settings.confirm_draw:
            self._show_terminal_action_confirmation(
                "draw",
                "Confirm draw",
                "End this game as a draw by agreement?",
            )
            return

        self._emit_draw_agreement()

    def _emit_draw_agreement(self):
        """Publish a draw-by-agreement result."""

        bus.emit(
            GameEndedEvent(
                winner="Draw",
                reason="agreement",
                message="Draw by agreement.",
            )
        )
        logger.info("Draw agreement emitted")

        # TODO: have to implement draw agreement by the other color

    def _handle_resign_action(self, _event=None):
        """Handle resign button clicks, including optional confirmation."""

        if game_state.game_over:
            logger.info("Ignoring resign action because game is already over")
            return
        settings = getattr(getattr(self, "settings_controller", None), "settings", None)
        if settings is not None and settings.confirm_resign:
            self._show_terminal_action_confirmation(
                "resign",
                "Confirm resignation",
                "Resign this game?",
            )
            return

        self._emit_resignation()

    def _emit_resignation(self):
        """Publish a resignation result for the side that is not to move."""

        winner = (
            "Black"
            if self.board_view.game_manager.active_color() == chess.WHITE
            else "White"
        )
        loser = "White" if winner == "Black" else "Black"
        bus.emit(
            GameEndedEvent(
                winner=winner,
                reason="resignation",
                message=f"{loser} resigned. {winner} wins.",
            )
        )
        logger.info("Resignation emitted loser=%s winner=%s", loser, winner)

    def _show_terminal_action_confirmation(
        self,
        action: str,
        title: str,
        message: str,
    ):
        """Open a confirmation dialog for draw or resignation actions."""

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
        """Dismiss a pending terminal-action confirmation."""

        self.pending_terminal_action = None
        logger.info("Terminal action cancelled")
        self.page.pop_dialog()
        safe_update(self.page)

    def _handle_action_confirm(self, _event=None):
        """Commit the pending confirmed draw or resignation action."""

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
        """Close the result dialog and reset board/clock for a new game."""

        self.page.pop_dialog()
        self.result_dialog.open = False
        logger.info("Resetting game from result dialog")
        if self.position_selector is not None:
            self.position_selector.value = "Start Position"
        self.board_view.load_position()
        self.time_control_UI.set_time_control(self.time_control_UI.time_control)
        self._route_manager.navigate("/game")

    def _handle_open_computer_setup(self, time_control: tuple[int, int]) -> None:
        """Open the computer setup overlay with the selected time control."""
        self._pending_time_control = time_control
        self._pending_stockfish_config = None
        self._stockfish_downloader = None

        logger.info(
            "Opening computer setup with time_control=%s+%s",
            time_control[0],
            time_control[1],
        )

        settings = self.settings_controller.settings
        binary_path = settings.stockfish_binary_path
        binary_available = False
        asset_name = ""
        asset_size_bytes = 0
        if binary_path:
            valid, _ = verify_stockfish_binary(binary_path)
            binary_available = valid

        self._setup_overlay = SetupOverlay(
            page=self.page,
            file_picker=self._file_picker,
            mode="computer",
            binary_available=binary_available,
            asset_name=asset_name,
            asset_size_bytes=asset_size_bytes,
            on_start_game=self._handle_stockfish_start,
            on_close=self._handle_overlay_closed,
            on_install_clicked=self._handle_overlay_install_clicked,
            on_binary_installed=self._handle_binary_installed,
        )
        self._setup_overlay.open()

        if not binary_available:
            self._checking_binary = True
            self.page.run_task(self._async_fetch_and_update_binary_info)

    def _handle_binary_installed(self, path: str) -> None:
        """Store the installed binary path in settings."""
        self.settings_controller.update(stockfish_binary_path=path)
        logger.info("Binary path saved to settings path=%s", path)

    async def _async_fetch_and_update_binary_info(self) -> None:
        """Query GitHub for available Stockfish binaries and push info to overlay."""
        logger.info("Fetching available Stockfish binary info...")
        downloader = StockfishDownloadManager()
        downloader.set_storage_dir(get_stockfish_dir(self.page))
        try:
            match = await downloader.query_release_async()
        except Exception as exc:
            logger.error("Stockfish binary info fetch failed: %s", exc)
            self._checking_binary = False
            if self._setup_overlay is not None:
                show_toast(
                    self.page,
                    f"Could not fetch binary info: {exc}",
                    is_error=True,
                )
            return

        self._stockfish_downloader = downloader
        self._checking_binary = False

        bus.emit(
            StockfishInfoReadyEvent(
                release_tag=match.release_tag,
                asset_name=match.best_asset.name,
                asset_size_bytes=match.best_asset.size_bytes,
                asset_subarch=match.best_asset.subarch.value,
            )
        )

        if self._setup_overlay is not None:
            self._setup_overlay.update_asset_info(
                match.best_asset.name,
                match.best_asset.size_bytes,
            )
            logger.info(
                "Binary info pushed to overlay name=%s size=%d",
                match.best_asset.name,
                match.best_asset.size_bytes,
            )

    def _handle_overlay_install_clicked(self) -> None:
        """Trigger Stockfish download as an async task on the Flet event loop."""
        self.page.run_task(self._async_download_stockfish)

    async def _async_download_stockfish(self) -> None:
        """Download Stockfish binary. Runs on the Flet event loop.

        Uses ``query_release_async`` for non-blocking HTTP and offloads the
        blocking subprocess polling to a thread via ``asyncio.to_thread``.
        Progress updates are marshalled back to the event loop with
        ``asyncio.run_coroutine_threadsafe`` so Flet controls are never
        touched from a background thread.
        """
        logger.info("_async_download_stockfish ENTER")
        try:
            await self._do_download_stockfish()
        except Exception as exc:
            logger.critical(
                "_async_download_stockfish unhandled exception: %s",
                exc, exc_info=True,
            )

    async def _do_download_stockfish(self) -> None:
        logger.info("_do_download_stockfish ENTER")

        downloader = StockfishDownloadManager()
        dest_dir = get_stockfish_dir(self.page)
        downloader.set_storage_dir(dest_dir)

        try:
            await downloader.query_release_async()
        except Exception as exc:
            logger.error("Stockfish query failed: %s", exc)
            show_toast(self.page, f"Failed to query binary info: {exc}", is_error=True)
            bus.emit(StockfishDownloadFailedEvent(error_message=str(exc)))
            return

        panel = (
            self._setup_overlay._stockfish_install_panel
            if self._setup_overlay
            else None
        )

        loop = asyncio.get_running_loop()

        async def _update_ui(downloaded: int, total: int) -> None:
            if panel is not None:
                panel.update_progress(downloaded, total)

        def on_progress(downloaded: int, total: int) -> None:
            asyncio.run_coroutine_threadsafe(
                _update_ui(downloaded, total), loop
            )

        logger.info(
            "Running synchronous download with panel=%s",
            "available" if panel else "None",
        )
        try:
            downloaded = await asyncio.to_thread(
                downloader._download_via_subprocess_sync,
                asset=downloader.last_query.best_asset,
                dest_dir=dest_dir,
                progress_callback=on_progress,
            )
        except Exception as exc:
            logger.error("Stockfish download failed: %s", exc)
            if panel is not None:
                panel.reset_download_state()
            show_toast(self.page, f"Download failed: {exc}", is_error=True)
            bus.emit(StockfishDownloadFailedEvent(error_message=str(exc)))
            return

        path = str(downloaded.download_path)
        logger.info("Download succeeded, path=%s", path)

        valid, version = verify_stockfish_binary(path)
        if not valid:
            logger.error("Downloaded binary validation failed: %s", version)
            if panel is not None:
                panel.reset_download_state()
            show_toast(
                self.page,
                f"Downloaded binary is not compatible: {version}",
                is_error=True,
            )
            bus.emit(StockfishDownloadFailedEvent(error_message=version))
            if Path(path).exists():
                Path(path).unlink()
            return

        self.settings_controller.update(stockfish_binary_path=path)
        logger.info("Stockfish downloaded and saved version=%s path=%s", version, path)

        if panel is not None:
            panel.on_download_complete(path)

        logger.info("_do_download_stockfish EXIT")

    def _handle_open_online_setup(self, time_control: tuple[int, int]) -> None:
        """Open the online setup overlay with the selected time control."""
        self._pending_time_control = time_control

        logger.info(
            "Opening online setup with time_control=%s+%s",
            time_control[0],
            time_control[1],
        )

        self._setup_overlay = SetupOverlay(
            page=self.page,
            file_picker=self._file_picker,
            mode="online",
            on_play_local=self._handle_local_play,
            on_close=self._handle_overlay_closed,
        )
        self._setup_overlay.open()

    def _handle_stockfish_start(self, config: StockfishGameConfig) -> None:
        """Start a game against Stockfish with the given configuration."""
        self._pending_stockfish_config = config
        logger.info(
            "Starting Stockfish game config=preset=%s elo=%s",
            config.preset_name,
            config.elo,
        )
        self._setup_overlay = None
        game_state.game_against = GameAgainst.COMPUTER
        self._launch_game()

    def _handle_local_play(self) -> None:
        """Start a local flip-board game."""
        logger.info("Starting local flip-board game")
        self._setup_overlay = None
        game_state.game_against = GameAgainst.LOCAL
        self._launch_game()

    def _handle_overlay_closed(self) -> None:
        """Clean up when the setup overlay is closed without starting."""
        logger.info("Setup overlay closed without starting game")
        self._setup_overlay = None
        self._pending_time_control = None
        self._pending_stockfish_config = None

    def _launch_game(self) -> None:
        """Navigate to the game view and start the game session."""
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
        """Push route, start BotManager if needed, then emit start event."""

        if (
            game_state.game_against == GameAgainst.COMPUTER
            and self.bot_manager is None
        ):
            config = self._pending_stockfish_config or StockfishGameConfig()
            settings = self.settings_controller.settings
            binary_path = settings.stockfish_binary_path
            if binary_path:
                self.bot_manager = BotManager(
                    engine_path=binary_path,
                    config=None,
                    on_bot_move=self.board_view.play_uci_move,
                )
                logger.info("Created BotManager with binary=%s", binary_path)

        await self.page.push_route("/game")
        self._on_game_enter()
        bus.emit(GameStartedEvent(opponent_nature=game_state.game_against))


def entry_point(page: ft.Page):
    """Create the app with dev-mode controls toggled by environment variable."""

    dev_mode = os.getenv("PAWNPASSANT_DEV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "dev",
    }

    logger.info("Entry point invoked dev_mode=%s", dev_mode)
    ChessApp(page, dev_mode=dev_mode)
