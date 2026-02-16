import flet as ft


class NumButton(ft.Button):
    def __init__(self, num):
        super().__init__(content=str(num), on_click=lambda: self.button_click(num))

    def button_click(self, e):
        print(e)

class CalculatorApp():
    def __init__(self):
        pass

    def MainPage(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn passant"
        self.create_ui()

    def create_ui(self):
        self.display = ft.TextField(disabled=True)
        self.page.add(self.display)

        button = NumButton(1)
        self.page.add(button)
    
    def button_click(self, e):
        print("Button clicked")
