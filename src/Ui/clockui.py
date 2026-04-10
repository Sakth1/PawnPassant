import flet as ft

from utils.signals import bus
from utils.events import PieceModevedEvent
from utils.models import ActiveColor, TimeControl
from core.clock import Clock


class ClockUI(ft.Container):
    def __init__(self):
        super().__init__()
        self.black_timer = ft.Text(
            "01:00",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            #margin=20,
            font_family="RobotoMono",
            size=40,
            weight=ft.FontWeight.BOLD,
        )
        self.white_timer = ft.Text(
            "02:00",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            #margin=20,
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
            white_clock_callback=self.update_white_timer,
            black_clock_callback=self.update_black_timer,
        )
        self.active_color: ActiveColor = ActiveColor.WHITE
        bus.connect(PieceModevedEvent, self._handle_piece_moved)

    def update_white_timer(self, min, sec, ms):
        self.white_timer.value = f"{min}:{sec}.{ms}"

    def update_black_timer(self, min, sec, ms):
        self.black_timer.value = f"{min}:{sec}.{ms}"

    def _handle_piece_moved(self):
        print("received signal")
