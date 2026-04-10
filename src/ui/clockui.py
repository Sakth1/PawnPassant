import flet as ft

from utils.signals import bus
from utils.events import (
    ClockTickEvent,
    GameEndedEvent,
    GameStartedEvent,
    PieceModevedEvent,
)
from utils.models import ActiveColor, TimeControl
from core.clock import Clock


def time_control_to_string(time_control: TimeControl) -> str:
    return f"{time_control[0]:02}:00"


class ClockUI(ft.Container):
    def __init__(self, time_control: TimeControl = TimeControl.ONE_PLUS_ONE):
        super().__init__()
        self.black_timer_main = ft.Text(
            time_control_to_string(time_control),
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=40,
            weight=ft.FontWeight.BOLD,
            margin=ft.margin.Margin(5, 5, 5, 5),
        )
        self.black_timer_ms = ft.Text(
            "",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=20,
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
            size=40,
            weight=ft.FontWeight.BOLD,
            margin=ft.margin.Margin(5, 5, 5, 5),
        )
        self.white_timer_ms = ft.Text(
            "",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=20,
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
        self.expand = True
        self.alignment = ft.Alignment.CENTER
        self.border_radius = 15
        self.content = ft.Column(
            controls=[
                self.black_timer,
                ft.Container(
                    height=3,
                    bgcolor=ft.Colors.GREY_400,
                    width=100,
                    margin=ft.margin.Margin(20, 0, 20, 0),
                ),  # fixed width
                self.white_timer,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.clock = Clock(
            time_control=time_control,
        )
        self.active_color: ActiveColor = ActiveColor.WHITE
        bus.connect(ClockTickEvent, self._handle_clock_tick)
        bus.connect(PieceModevedEvent, self._handle_piece_moved)
        bus.connect(GameStartedEvent, self._start_clock)
        bus.connect(GameEndedEvent, self._handle_game_ended)

    def _safe_page(self):
        try:
            return self.page
        except RuntimeError:
            return None

    def _handle_clock_tick(self, event: ClockTickEvent):
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

        if event.is_critical:
            target_ms.value = f".{event.milliseconds // 10:02}"
            container = self.white_timer if is_white else self.black_timer
            container.bgcolor = "#250E0E"
            target_main.margin = ft.margin.Margin(5, 5, 0, 5)
            target_ms.bgcolor = "#250E0E"
        else:
            target_ms.value = ""
        self.update()

    def _start_clock(self, _event: GameStartedEvent):
        self.clock.start()

    def _handle_piece_moved(self, _event: PieceModevedEvent):
        self.clock.switch()

    def _handle_game_ended(self, _event: GameEndedEvent):
        self.clock.stop()
