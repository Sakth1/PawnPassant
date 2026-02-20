import flet as ft
from chess import square, RANK_NAMES, FILE_NAMES, Piece
from typing import Optional


from Core.Engine import Game


class Square(ft.Container):
    def __init__(self, file, rank, color, content=None):
        super().__init__(expand=True)
        self.file = file
        self.rank = rank
        self.color = color
        self.content = content

        # container attributes
        self.bgcolor = ft.Colors.GREEN_100 if self.color == "w" else ft.Colors.GREEN_900
        self.width = 60
        self.height = 60

        # ensure no gap around each square
        self.margin = 0

    def update_content(self, piece:Piece=None):
        self.content = piece
        self.update()


class ChessBoard(ft.Container):
    def __init__(self):
        super().__init__()
        self.game = Game()
        print("game.board.piece_map")
        print(self.game.board)
        self.board_frame = ft.GridView(
            runs_count=8,
            controls=self._create_squares(),
            expand=True,
            spacing=0,
            run_spacing=0,
            padding=0
            )

        # remove padding on the board container as well
        self.margin = 0
        self.alignment = ft.Alignment.CENTER
        self.height = 480
        self.width = 480
        self.content = self.board_frame
        self._setup_pieces()
    
    def _create_squares(self):
        self.squares = []
        for i in range(len(FILE_NAMES)):
            current_file = FILE_NAMES[i]
            for j in range(len(RANK_NAMES)):
                current_rank = RANK_NAMES[j]
                self.squares.append(Square(
                    file=current_file,
                    rank=current_rank,
                    color="b" if (i+j) % 2 == 0 else "w",
                    ))
        return self.squares

    def _setup_pieces(self):
        for i in range(len(RANK_NAMES)):
            for j in range(len(FILE_NAMES)):
                chess_sq = square(j, i)
                piece = self.game.board.piece_at(chess_sq)
                print(f"Setting up square {FILE_NAMES[j]}{RANK_NAMES[i]} with piece {piece}")

    def get_square_from_coards(self, position:str) -> Optional[Square]:
        file = position[0]
        rank = position[1]
        for square in self.board_frame.controls:
            if square.file == file and square.rank == rank:
                return square
        return None
    
class ChessApp():
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn Passant"
        self.board_view = ChessBoard()
        self.page.add(self.board_view)
        #self.board_view.width = self.page.width
        


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