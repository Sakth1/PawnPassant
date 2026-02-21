import flet as ft
from chess import square, RANK_NAMES, FILE_NAMES, Piece
from typing import Optional
from dataclasses import dataclass


from Core.Engine import Game


class Square(ft.Container, ft.Control):
    def __init__(self, file, rank, coordinate, color, content=None):
        super().__init__(expand=True)
        self.file = file
        self.rank = rank
        self.coordinate = coordinate
        self.color = color
        self.content = content

        # container attributes
        self.bgcolor = ft.Colors.GREEN_100 if self.color == "w" else ft.Colors.GREEN_900
        self.width = 60
        self.height = 60

        # ensure no gap around each square
        self.margin = 0

    def update_content(self, piece:Optional[Piece | str]=None):
        if piece is None:
            self.content = ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
            return
        
        if isinstance(piece, Piece):
            piece = piece.symbol()

        self.content = ft.Text(piece, align=ft.Alignment.CENTER, color=ft.Colors.RED)  # TODO: use actual piece
        # calling update() before the control is attached to a page raises RuntimeError
        # so attempt to update but ignore if not yet added to a page
        try:
            self.update()
        except RuntimeError:
            pass


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
    
    def _create_squares(self) -> list[Square]:
        # Create a flat list of Square controls in the same order GridView expects
        # and also keep a lookup map by algebraic coord (e.g., 'a1') for quick access.
        self.squares: list[Square] = []
        self.square_map: dict[str, Square] = {}
        reversed_rank = list(reversed(RANK_NAMES))  # so we start from rank 8 down to 1

        for i in range(len(RANK_NAMES)):
            rank_idx = RANK_NAMES.index(reversed_rank[i])
            for j in range(len(FILE_NAMES)):
                file_idx = FILE_NAMES.index(FILE_NAMES[j])
                coords=f"{FILE_NAMES[file_idx]}{RANK_NAMES[rank_idx]}"
                sq = Square(
                    file=file_idx,
                    rank=rank_idx,
                    coordinate=coords,
                    color="b" if (file_idx + rank_idx) % 2 == 0 else "w",
                    content=ft.Text(coords, align=ft.Alignment.CENTER, color=ft.Colors.RED)  # placeholder content for debugging
                )
                self.squares.append(sq)
                self.square_map[coords] = sq
        return self.squares

    def _setup_pieces(self):
        for rank_idx in range(len(RANK_NAMES)):
            for file_idx in range(len(FILE_NAMES)):
                coords=f"{FILE_NAMES[file_idx]}{RANK_NAMES[rank_idx]}"
                piece = self.game.board.piece_at(square(file_idx, rank_idx))
                if piece is not None:
                    self.square_map[coords].update_content(piece.symbol())

    
class ChessApp():
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn Passant"
        self.board_view = ChessBoard()
        self.page.add(self.board_view)
        #self.board_view.width = self.page.width
        


def main(page: ft.Page):
    ChessApp(page)
