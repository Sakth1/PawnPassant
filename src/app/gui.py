import flet as ft

DARK = "#769656"
LIGHT = "#eeeed2"
class ChessSquare(ft.Container):
    def __init__(self, color):
        super().__init__(
            width=5,
            height=5,
            bgcolor=color
        )
        Position: tuple[str, int] = (None, None)  # Example position, can be set dynamically

class ChessBoard(ft.GridView):
    def __init__(self):
        super().__init__(
            expand=True,
            child_aspect_ratio=1,
            max_extent=50,
        )
        self.create_board()

    def create_board(self):
        colors = [DARK, LIGHT]  # Light and dark square colors
        for row in range(8):
            for col in range(8):
                color = colors[(row + col) % 2]
                print(f"Adding square at row {row}, col {col} with color {color}")
                self.controls.append(ChessSquare(color))


def main(page: ft.Page):
    page.title = "Chess Board"
    chess_board = ChessBoard()
    page.add(chess_board)

"""
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
"""