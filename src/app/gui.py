import flet as ft


class CalculatorApp():
    def __init__(self):
        pass

    def MainPage(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn passant"
        self.create_ui()

    def create_ui(self):
        button = ft.Button("1", on_click=self.button_click, height=50, width=50, type=ft.ButtonStyle.elevation)
        self.page.add(button)
    
    def button_click(self, e):
        print("Button clicked")
