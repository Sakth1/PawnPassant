import flet as ft
from typing import Callable

from ui.layout import AppLayout, resolve_app_layout
from core.clock import Clock
from utils.signals import bus
from utils.events import (
    ClockStateEvent,
    ClockTickEvent,
    GameEndedEvent,
    GameStartedEvent,
    PieceModevedEvent,
)
from utils.models import ActiveColor, TimeControl


def time_control_to_string(time_control: TimeControl) -> str:
    return f"{time_control[0]:02}:00"


class ClockUI(ft.Container):
    def __init__(
        self,
        time_control: TimeControl = TimeControl.THREE_PLUS_TWO,
        on_draw: Callable | None = None,
        on_resign: Callable | None = None,
    ):
        super().__init__()
        self.time_control = time_control
        self.on_draw = on_draw
        self.on_resign = on_resign
        self.layout = resolve_app_layout(960, 800)
        self.black_timer_main = ft.Text(
            time_control_to_string(time_control),
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=self.layout.timer_font_size,
            weight=ft.FontWeight.BOLD,
            margin=ft.margin.Margin(5, 5, 5, 5),
        )
        self.black_timer_ms = ft.Text(
            "",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=self.layout.timer_ms_size,
            weight=ft.FontWeight.BOLD,
            offset=ft.Offset(0, 0.1),
            margin=ft.margin.Margin(0, 0, 5, 0),
        )
        self.black_timer = ft.Container(
            content=ft.Row(
                controls=[self.black_timer_main, self.black_timer_ms],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=2,
                margin=ft.margin.Margin(5, 5, 5, 5),
            ),
            bgcolor="#262626",
        )
        self.white_timer_main = ft.Text(
            time_control_to_string(time_control),
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=self.layout.timer_font_size,
            weight=ft.FontWeight.BOLD,
            margin=ft.margin.Margin(5, 5, 5, 5),
        )
        self.white_timer_ms = ft.Text(
            "",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=self.layout.timer_ms_size,
            weight=ft.FontWeight.BOLD,
            offset=ft.Offset(0, -0.4),
        )
        self.white_timer = ft.Container(
            content=ft.Row(
                controls=[self.white_timer_main, self.white_timer_ms],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=2,
                margin=ft.margin.Margin(5, 5, 5, 5),
            ),
            bgcolor="#262626",
        )

        self.bgcolor = "#262626"
        self.expand = False
        self.alignment = ft.Alignment.CENTER
        self.border_radius = self.layout.timer_radius
        self.divider = ft.Container(
            height=3,
            bgcolor=ft.Colors.GREY_400,
            width=self.layout.divider_extent,
            margin=ft.margin.Margin(20, 0, 20, 0),
        )
        self.draw_button = self._build_action_button(
            icon_name="HANDSHAKE_OUTLINED",
            tooltip="Offer draw",
            on_click=self._handle_draw_click,
        )
        self.resign_button = self._build_action_button(
            icon_name="FLAG_ROUNDED",
            tooltip="Resign",
            on_click=self._handle_resign_click,
        )
        self.action_bar = ft.Container(
            content=ft.Row(
                controls=[self.draw_button, self.resign_button],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.Padding(8, 4, 8, 4),
            border_radius=12,
            bgcolor="#303030",
        )
        self.content = ft.Column(
            controls=[
                self.black_timer,
                self.action_bar,
                self.divider,
                self.white_timer,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.clock = Clock(
            time_control=time_control,
        )
        self.active_color: ActiveColor = ActiveColor.WHITE
        self.game_over = False
        bus.connect(ClockStateEvent, self._handle_clock_state)
        bus.connect(ClockTickEvent, self._handle_clock_tick)
        bus.connect(PieceModevedEvent, self._handle_piece_moved)
        bus.connect(GameStartedEvent, self._start_clock)
        bus.connect(GameEndedEvent, self._handle_game_ended)
        self.apply_layout(self.layout)

    def _icon(self, name: str, fallback: str = "MORE_HORIZ_ROUNDED"):
        return getattr(ft.Icons, name, getattr(ft.Icons, fallback))

    def _build_action_button(self, icon_name: str, tooltip: str, on_click) -> ft.IconButton:
        return ft.IconButton(
            icon=self._icon(icon_name),
            tooltip=tooltip,
            icon_color=ft.Colors.GREY_300,
            bgcolor="#3A3A3A",
            hover_color=ft.Colors.WHITE_10,
            on_click=on_click,
        )

    def _handle_draw_click(self, event):
        if self.game_over:
            return
        if self.on_draw is not None:
            self.on_draw(event)

    def _handle_resign_click(self, event):
        if self.game_over:
            return
        if self.on_resign is not None:
            self.on_resign(event)

    def set_time_control(self, time_control: tuple[int, int]) -> None:
        self.time_control = time_control
        self.clock.stop()
        self.clock = Clock(time_control=time_control)
        self.game_over = False
        self.content.controls = [
            self.black_timer,
            self.action_bar,
            self.divider,
            self.white_timer,
        ]
        display_value = time_control_to_string(time_control)
        for timer_main, timer_ms, timer_container in (
            (self.black_timer_main, self.black_timer_ms, self.black_timer),
            (self.white_timer_main, self.white_timer_ms, self.white_timer),
        ):
            timer_main.value = display_value
            timer_main.color = ft.Colors.GREY_400
            timer_ms.value = ""
            timer_ms.bgcolor = None
            timer_container.bgcolor = "#262626"
        self._safe_update(self)

    def apply_layout(self, layout: AppLayout):
        """Resize the timer UI for the current responsive breakpoint."""

        self.layout = layout
        self.width = layout.clock_width
        self.border_radius = layout.timer_radius

        row_margin = ft.margin.Margin(
            layout.timer_padding,
            layout.timer_padding,
            layout.timer_padding,
            layout.timer_padding,
        )

        for timer in (self.black_timer, self.white_timer):
            timer.padding = layout.timer_padding
            timer.border_radius = max(10, layout.timer_radius - 2)

        for timer_row in (self.black_timer.content, self.white_timer.content):
            timer_row.margin = row_margin

        for timer_text in (self.black_timer_main, self.white_timer_main):
            timer_text.size = layout.timer_font_size
            timer_text.margin = ft.margin.Margin(4, 2, 0, 2)

        for timer_ms in (self.black_timer_ms, self.white_timer_ms):
            timer_ms.size = layout.timer_ms_size
            timer_ms.margin = ft.margin.Margin(0, 0, 4, 2)

        self.content.spacing = max(10, layout.gap)
        self.divider.width = layout.divider_extent
        self.divider.height = 3
        action_size = max(34, min(44, int(layout.board_square_size * 0.52)))
        self.action_bar.border_radius = max(8, int(layout.timer_radius * 0.55))
        action_padding_y = max(3, int(layout.gap * 0.25))
        action_padding_x = max(6, int(layout.gap * 0.4))
        self.action_bar.padding = ft.Padding(
            action_padding_x,
            action_padding_y,
            action_padding_x,
            action_padding_y,
        )
        self.action_bar.content.spacing = max(6, int(layout.gap * 0.45))
        for button in (self.draw_button, self.resign_button):
            button.width = action_size
            button.height = action_size
            button.icon_size = max(18, int(action_size * 0.55))
        self._safe_update(self)

    def _safe_page(self):
        try:
            return self.page
        except RuntimeError:
            return None

    def _handle_clock_tick(self, event: ClockTickEvent):
        if self.game_over:
            return
        page = self._safe_page()
        if page is None:
            return
        page.run_task(self._update_ui_async, event)

    async def _update_ui_async(self, event: ClockTickEvent):
        self._update_ui(event)

    def _update_ui(self, event: ClockTickEvent):
        is_white = event.color == ActiveColor.WHITE
        target_main = self.white_timer_main if is_white else self.black_timer_main
        target_ms = self.white_timer_ms if is_white else self.black_timer_ms

        target_main.value = f"{event.minutes:02}:{event.seconds:02}"
        target_main.color = ft.Colors.GREY_400
        target_ms.bgcolor = None

        if event.is_critical:
            target_ms.value = f".{event.milliseconds // 10:02}"
            container = self.white_timer if is_white else self.black_timer
            container.bgcolor = "#250E0E"
            target_main.margin = ft.margin.Margin(4, 2, 0, 2)
            target_ms.bgcolor = "#250E0E"
        else:
            target_ms.value = ""
            if is_white:
                self.white_timer.bgcolor = "#262626"
            else:
                self.black_timer.bgcolor = "#262626"
        self.update()

    def _start_clock(self, _event: GameStartedEvent):
        self.game_over = False
        self.clock.start()

    def _handle_piece_moved(self, _event: PieceModevedEvent):
        if self.game_over:
            return
        self.clock.switch()
        self._flip_clock()

    def _handle_clock_state(self, event: ClockStateEvent):
        """Translate a flag-fall into a game-ended result event."""

        if event.state != "flagged" or event.active_color is None or self.game_over:
            return

        winner = "Black" if event.active_color == ActiveColor.WHITE else "White"
        bus.emit(
            GameEndedEvent(
                winner=winner,
                reason="time",
                message=f"{winner} wins on time.",
            )
        )

    def _flip_clock(self):
        """Reverse the clock display orientation."""
        self.content.controls.reverse()
        self._safe_update(self)

    def _handle_game_ended(self, _event: GameEndedEvent):
        self.game_over = True
        self.clock.stop()

    @staticmethod
    def _safe_update(control: ft.Control):
        try:
            control.update()
        except RuntimeError:
            pass
