import flet as ft

from utils.models import ActiveColor, TimeControl
from core.clock import Clock


class ClockUI(ft.Container):
    def __init__(self):
        super().__init__()
        self.black_timer = ft.Text(
            "01:00",
            align=ft.Alignment.CENTER,
            color=ft.Colors.GREY_400,
            margin=20,
            font_family="Roboto",
            size=20,
            weight=ft.FontWeight.BOLD,
            offset=ft.Offset(0, 0.27),
        )
        self.white_timer = ft.Text(
            "02:00",
            align=ft.Alignment.CENTER,
            color=ft.Colors.GREY_400,
            margin=20,
            font_family="Roboto",
            size=20,
            weight=ft.FontWeight.BOLD,
            offset=ft.Offset(0, -0.27),
        )
        self.width = 150
        self.bgcolor = "#262626"
        self.alignment = ft.Alignment.CENTER
        self.blur = 1
        self.border_radius = 15
        self.content = ft.Column(
            [
                self.black_timer,
                ft.Divider(color=ft.Colors.BLACK),
                self.white_timer,
            ]
        )
        self.clock = Clock(TimeControl.THREE_PLUS_TWO, white_clock_callback=self.update_white_timer, black_clock_callback=self.update_black_timer)
        self.active_color: ActiveColor = ActiveColor.WHITE

    def update_white_timer(self, min, sec, ms):
        self.white_timer.value = f"{min}:{sec}.{ms}"

    def update_black_timer(self, min, sec, ms):
        self.black_timer.value = f"{min}:{sec}.{ms}"
