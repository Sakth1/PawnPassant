import flet as ft


class NumButton(ft.Button):
    def __init__(self, num):
        super().__init__(content=str(num), on_click=lambda: self.button_click(num))

    def button_click(self, e):
        if self.page and self.page.controls:
            display = self.page.controls[0]
            if isinstance(display, ft.TextField):
                display.value = f"{display.value or ''}{e}"
                display.update()

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

        row1 = ft.Row(controls=[NumButton(1), NumButton(2), NumButton(3)])
        row2 = ft.Row(controls=[NumButton(4), NumButton(5), NumButton(6)])
        row3 = ft.Row(controls=[NumButton(7), NumButton(8), NumButton(9)])
        self.page.add(row1)
        self.page.add(row2)
        self.page.add(row3)
    
    def button_click(self, e):
        print("Button clicked")
