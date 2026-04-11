"""Top-level application wiring for the Pawn Passant interface."""

from __future__ import annotations

import json
import os
from pathlib import Path

import flet as ft

from ui.board import ChessBoard
from ui.clockui import ClockUI
from ui.layout import AppLayout, resolve_app_layout
from utils.constants import ASSET_DIR, FONT_DIR
from utils.events import GameEndedEvent, GameStartedEvent
from utils.signals import bus


class ChessApp:
    """Builds the page layout and optional developer controls."""

    def __init__(self, page: ft.Page, dev_mode: bool = False):
        self.page = page
        self.dev_mode = dev_mode
        self.layout: AppLayout = resolve_app_layout(960, 800)
        self.previous_layout_type: str | None = None  # Track layout type changes

        self.page.fonts = {
            "RobotoMono": str(Path(FONT_DIR, "RobotoMono-VariableFont_wght.ttf"))
        }
        self.page.title = "Pawn Passant"
        self.page.window.icon = str(Path(ASSET_DIR, "PawnPassant.ico"))
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = ft.ScrollMode.AUTO

        self.board_view = ChessBoard()
        self.time_control_view = ClockUI()
        
        # Create initial captured pieces display using factory
        from ui.captured_pieces import create_captured_pieces_display
        self.piece_display = create_captured_pieces_display(self.layout.layout_type)
        
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
            col={"xs": 12, "md": 8},
        )
        self.clock_slot = ft.Container(
            content=self.time_control_view,
            alignment=ft.Alignment.CENTER,
            col={"xs": 12, "md": 4},
        )
        self.piece_display_slot = ft.Container(
            content=self.piece_display,
            alignment=ft.Alignment.CENTER,
            col={"xs": 12, "md": 8},
        )
        self.content_row.controls = [self.piece_display_slot, self.board_slot, self.clock_slot]

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
            minimum_padding=self.layout.padding,
            content=self.content_container,
        )
        self.main_page_view = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=self.safe_area,
        )

        self.page.on_resize = self._handle_page_resize
        self.page.on_media_change = self._handle_page_resize
        bus.connect(GameStartedEvent, self._handle_game_started)
        bus.connect(GameEndedEvent, self._handle_game_ended)
        self.page.add(self.main_page_view)
        self._apply_responsive_layout()
        bus.emit(GameStartedEvent())

    def _resolve_page_dimensions(self) -> tuple[float, float]:
        page_width = getattr(self.page, "width", 0) or 960
        page_height = getattr(self.page, "height", 0) or 800

        media = getattr(self.page, "media", None)
        padding = getattr(media, "padding", None)
        if padding is not None:
            page_width = max(
                320.0,
                page_width
                - (getattr(padding, "left", 0) or 0)
                - (getattr(padding, "right", 0) or 0),
            )
            page_height = max(
                480.0,
                page_height
                - (getattr(padding, "top", 0) or 0)
                - (getattr(padding, "bottom", 0) or 0),
            )
        return page_width, page_height

    def _apply_responsive_layout(self):
        """Apply responsive layout and handle layout type transitions."""
        page_width, page_height = self._resolve_page_dimensions()
        new_layout = resolve_app_layout(page_width, page_height)

        # Check if layout type changed (desktop/tablet/mobile transition)
        layout_type_changed = (
            self.previous_layout_type is not None 
            and self.previous_layout_type != new_layout.layout_type
        )

        if layout_type_changed:
            # Emit layout change event
            from utils.events import LayoutChangedEvent
            bus.emit(
                LayoutChangedEvent(
                    from_layout=self.previous_layout_type,
                    to_layout=new_layout.layout_type,
                    layout_template=new_layout.layout_template,
                )
            )

            # Replace piece display with appropriate variant for new layout
            from ui.captured_pieces import create_captured_pieces_display
            old_display = self.piece_display
            self.piece_display = create_captured_pieces_display(new_layout.layout_type)
            self.piece_display_slot.content = self.piece_display

        self.layout = new_layout
        self.previous_layout_type = new_layout.layout_type

        # Apply layout metrics to all components
        self.board_view.apply_layout(self.layout)
        self.time_control_view.apply_layout(self.layout)
        self.piece_display.apply_layout(self.layout)

        self.content_row.spacing = self.layout.gap
        self.content_row.run_spacing = self.layout.gap
        self.board_slot.col = {"xs": 12, "md": self.layout.board_col}
        self.clock_slot.col = {"xs": 12, "md": self.layout.clock_col}
        self.root_column.spacing = self.layout.gap
        self.safe_area.minimum_padding = self.layout.padding
        self.content_container.padding = ft.Padding.all(self.layout.padding)
        self.result_dialog_title.size = max(18, int(self.layout.timer_font_size * 0.5))
        self.result_dialog_message.size = max(14, int(self.layout.timer_ms_size * 1.05))

        if self.position_selector is not None:
            self.position_selector.width = self.layout.dev_control_width

        self._safe_update(self.main_page_view)

    def _handle_page_resize(self, _event):
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
        self.board_view.load_position(selected_fen)
        bus.emit(GameStartedEvent())

    def _handle_game_started(self, _event: GameStartedEvent):
        self.page.pop_dialog()
        self.result_dialog.open = False
        self.result_dialog_title.value = ""
        self.result_dialog_message.value = ""
        self._safe_update(self.page)

    def _handle_game_ended(self, event: GameEndedEvent):
        self.result_dialog_title.value = event.winner or "Game Over"
        self.result_dialog_message.value = event.message
        self.page.show_dialog(self.result_dialog)
        self._safe_update(self.page)

    def _handle_result_dialog_close(self, _event=None):
        self.page.pop_dialog()
        self.result_dialog.open = False
        if self.position_selector is not None:
            self.position_selector.value = "Start Position"
        self.board_view.load_position()
        bus.emit(GameStartedEvent())
        self._safe_update(self.page)

    @staticmethod
    def _safe_update(control: ft.Control):
        try:
            control.update()
        except RuntimeError:
            pass


def main(page: ft.Page):
    """Create the app with dev-mode controls toggled by environment variable."""

    dev_mode = os.getenv("PAWNPASSANT_DEV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "dev",
    }

    ChessApp(page, dev_mode=dev_mode)
