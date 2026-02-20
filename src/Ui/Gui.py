import flet as ft
from chess import Square as SQUARES, RANK_NAMES, FILE_NAMES, Piece
from typing import Optional

from Core import Game


class Square(ft.Container):
    def __init__(self, file, rank, color, content=None):
        super().__init__()
        self.file = file
        self.rank = rank
        self.color = color
        self.content = content

        # container attributes
        self.bgcolor = ft.Colors.GREEN_100 if self.color == "w" else ft.Colors.GREEN_900
        self.width = 60
        self.height = 60
        self.padding = 0

    def update_content(self, piece:Piece):
        self.content = piece
        self.update()


class ChessBoard(ft.Container):
    def __init__(self):
        super().__init__()
        self.board_frame = ft.GridView(
            runs_count=8,
            controls=self._create_squares(),
            expand=True,
            )

        self.alignment = ft.Alignment.CENTER
        self.height = 480
        self.width = 480
        self.content = self.board_frame
    
    def _create_squares(self):
        squares = []
        for i in range(len(FILE_NAMES)):
            for j in range(len(RANK_NAMES)):
                squares.append(Square(
                    file=FILE_NAMES[i],
                    rank=RANK_NAMES[j],
                    color="b" if (i+j) % 2 == 0 else "w"
                    ))
        return squares

class ChessApp():
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn Passant"
        self.game = Game.Game()
        self.board_view = ChessBoard()
        #self.board_view.width = self.page.width
        self.page.add(self.board_view)


def main(page: ft.Page):
    ChessApp(page)

    """game = Game.Game()

    while True:
        move = input("Enter your move (e.g., e4, Nf3, etc.): ")
        if move.lower() == "exit":
            break
        if game.make_move(move):
            print(game.board.unicode(borders=True))
        else:
            print("Invalid move. Please try again.")"""