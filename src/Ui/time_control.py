import flet as ft


class ClockUI(ft.Container):
    def __init__(self):
        super().__init__()
        self.black_timer = ft.Text(
            "00:00",
            align=ft.Alignment.CENTER,
            color=ft.Colors.GREY_400,
            margin=20,
            font_family="Roboto",
            size=20,
            weight=ft.FontWeight.BOLD,
            offset=ft.Offset(0, 0.27),
        )
        self.white_timer = ft.Text(
            "00:00",
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
        # self.clock = Clock(TimeControl.THREE_PLUS_TWO)
