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


class ClockUI(ft.Container):
    def __init__(self):
        super().__init__()
        self.black_timer = ft.Text(
            "01:00",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=40,
            weight=ft.FontWeight.BOLD,
        )
        self.white_timer = ft.Text(
            "02:00",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=40,
            weight=ft.FontWeight.BOLD,
        )
        self.bgcolor = "#262626"
        self.expand = True
        self.alignment = ft.Alignment.CENTER
        self.border_radius = 15
        self.content = ft.Column(
            controls=[
                self.black_timer,
                ft.Container(height=3, bgcolor=ft.Colors.GREY_400, width=100, margin=ft.margin.Margin(20, 0, 20, 0)),  # fixed width
                self.white_timer,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.clock = Clock(
            TimeControl.THREE_PLUS_TWO,
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
        target = (
            self.white_timer
            if event.color == ActiveColor.WHITE
            else self.black_timer
        )
        if event.is_critical:
            target.value = (
                f"{event.minutes:02}:{event.seconds:02}.{event.milliseconds // 10:02}"
            )
        else:
            target.value = f"{event.minutes:02}:{event.seconds:02}"
        self.update()

    def _start_clock(self, _event: GameStartedEvent):
        self.clock.start()

    def _handle_piece_moved(self, _event: PieceModevedEvent):
        self.clock.switch()

    def _handle_game_ended(self, _event: GameEndedEvent):
        self.clock.stop()
