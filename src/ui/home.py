import flet as ft

class HomeView(ft.Container):
    def __init__(self):
        super().__init__()
        self.content = ft.Text("Home")