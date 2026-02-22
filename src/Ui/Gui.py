import flet as ft
from chess import square, parse_square, square_name, RANK_NAMES, FILE_NAMES, Piece
from typing import Optional
from pathlib import Path
import traceback

from Core.Engine import Game
from Constants import SYMBOL_MAP

class ChessPiece(ft.Container):
    def __init__(self, piece:Piece):
        super().__init__()
        self.piece = piece
    
    def to_control(self) -> ft.Control:
        try:
            symbol = self.piece.symbol()
            piece_name = SYMBOL_MAP.get(symbol)
            # Flet static assets must be addressed relative to the assets directory.
            piece_src = Path("pieces", "default", f"{piece_name}.png").as_posix()
            return ft.Image(src=piece_src)

        except Exception:
            traceback.print_exc()
            return ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
                
class Square(ft.Container):
    def __init__(self, file, rank, coordinate, color, on_square_click=None, size=60):
        super().__init__(expand=True)
        self.file = file
        self.rank = rank
        self.coordinate = coordinate
        self.color = color
        self.on_square_click = on_square_click

        #constants
        dot_size = size * 0.3
        ring_size = size * 0.8

        self.square_dot = ft.Container(
            width=dot_size,
            height=dot_size,
            border_radius=dot_size / 2,
            bgcolor=ft.Colors.BLACK_45,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.BLACK_45,
                offset=ft.Offset(0, 0),
            )
        )

        self.square_ring = ft.Container(
            width=ring_size,
            height=ring_size,
            border_radius=ring_size / 2,
            border=ft.Border.all(3, ft.Colors.BLACK_54),
            bgcolor=ft.Colors.TRANSPARENT,
        )

        # container attributes
        self.base_bgcolor = ft.Colors.GREEN_100 if self.color == "w" else ft.Colors.GREEN_900
        self.bgcolor = self.base_bgcolor
        self.width = size
        self.height = size
        self.piece_control: Optional[ft.Control] = None
        self.stack = ft.Stack(controls=[], expand=True, alignment=ft.Alignment.CENTER)
        self.content = self.stack
        self.highlighted_metadata: dict[str:bool|str|None] = {"highlighted":False, "parent_piece_square":None}
        self.has_piece = False

        # ensure no gap around each square
        self.margin = 0
        self.on_click = self._handle_click
        self.on_hover = self._handle_hover
    
    def _handle_click(self, e):
        if self.on_square_click is not None:
            self.on_square_click(self, self.coordinate)

    def _handle_hover(self, e):
        if self.highlighted_metadata.get("highlighted"):
            return
        if e.data is True:
            self.bgcolor = ft.Colors.BLUE
        else:
            self.bgcolor = self.base_bgcolor
        self.update()

    def set_highlight(self, highlighted: bool, parent_piece_square=None):
        self.highlighted_metadata["highlighted"] = highlighted
        self.highlighted_metadata["parent_piece_square"] = parent_piece_square
        self._rebuild_stack()
        self.update()

    def update_content(self, piece:Optional[ChessPiece]=None):
        try:
            if piece is None:
                content = None
                self.has_piece = False
            
            elif isinstance(piece, ChessPiece):
                content = piece.to_control()
                self.has_piece = True
            
            else:
                content = ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
                self.has_piece = False

        except Exception:
            traceback.print_exc()
            content = ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
        self.piece_control = content
        self._rebuild_stack()

    def _rebuild_stack(self):
        controls: list[ft.Control] = []
        if self.piece_control is not None:
            controls.append(self.piece_control)

        if self.highlighted_metadata.get("highlighted"):
            if self.piece_control is None:
                controls.append(self.square_dot)
            else:
                controls.append(self.square_ring)

        self.stack.controls = controls


class ChessBoard(ft.Container):
    def __init__(self):
        super().__init__()
        self.game = Game()
        self.highlighted_squares: set[str] = set()
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
                    on_square_click=self._handle_square_click,
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
                    self.square_map[coords].update_content(ChessPiece(piece))

    def _clear_move_highlights(self):
        for coord in self.highlighted_squares:
            sq = self.square_map.get(coord)
            if sq is not None:
                sq.set_highlight(False, None)
        self.highlighted_squares.clear()

    def _handle_square_click(self, square_instance: Square, click_cords: str):
        if square_instance.highlighted_metadata.get("highlighted"):
            self.move_piece(from_cords = square_instance.highlighted_metadata.get("parent_piece_square"), to_cords = click_cords)
            return
        
        self._clear_move_highlights()
        from_sq = parse_square(click_cords)
        legal_targets = [
            square_name(move.to_square)
            for move in self.game.board.legal_moves
            if move.from_square == from_sq
        ]
        for target in legal_targets:
            sq = self.square_map.get(target)
            if sq is not None:
                sq.set_highlight(True, click_cords)
                self.highlighted_squares.add(target)

    def _update_last_move_on_board(self):
        last_move = self.game.board.move_stack[-1]
        self.square_map[square_name(last_move.from_square)].update_content(self.game.board.piece_at(last_move.from_square))
        self.square_map[square_name(last_move.to_square)].update_content(ChessPiece(self.game.board.piece_at(last_move.to_square)))

    def move_piece(self, from_cords: str, to_cords: str):
        requested_move = f"{from_cords}{to_cords}"
        self._clear_move_highlights()
        for move in self.game.board.legal_moves:
            if str(move) == requested_move:
                self.game.board.push(move)
                self._update_last_move_on_board()
                break

    
class ChessApp():
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Pawn Passant"
        self.board_view = ChessBoard()
        self.page.add(self.board_view)
        #self.board_view.width = self.page.width
        


def main(page: ft.Page):
    ChessApp(page)
