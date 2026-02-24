import flet as ft
from chess import FILE_NAMES, RANK_NAMES, parse_square, square, square_name, Move

from Core.Engine import Game
from Core.MoveType import MoveType
from Ui.chess_piece import ChessPiece
from Ui.square import Square


class ChessBoard(ft.Container):
    def __init__(self):
        super().__init__()
        self.game = Game()
        self.highlighted_squares: set[str] = set()
        self.is_flipped = False
        self.board_frame = ft.GridView(
            runs_count=8,
            controls=self._create_squares(),
            expand=True,
            spacing=0,
            run_spacing=0,
            padding=0,
        )

        self.margin = 0
        self.alignment = ft.Alignment.CENTER
        self.height = 480
        self.width = 480
        self.content = self.board_frame
        self._setup_pieces()

    def _create_squares(self) -> list[Square]:
        self.squares: list[Square] = []
        self.square_map: dict[str, Square] = {}
        reversed_rank = list(reversed(RANK_NAMES))

        for i in range(len(RANK_NAMES)):
            rank_idx = RANK_NAMES.index(reversed_rank[i])
            for j in range(len(FILE_NAMES)):
                file_idx = FILE_NAMES.index(FILE_NAMES[j])
                coords = f"{FILE_NAMES[file_idx]}{RANK_NAMES[rank_idx]}"
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
                coords = f"{FILE_NAMES[file_idx]}{RANK_NAMES[rank_idx]}"
                piece = self.game.piece_at_square(square(file_idx, rank_idx))
                if piece is not None:
                    self.square_map[coords].update_content(ChessPiece(piece))

    def _flip_board(self):
        self.is_flipped = not self.is_flipped
        self.board_frame.controls = self.squares[::-1] if self.is_flipped else self.squares
        self.board_frame.update()

    def _clear_move_highlights(self):
        for coord in self.highlighted_squares:
            sq = self.square_map.get(coord)
            if sq is not None:
                sq.set_highlight(False, None)
        self.highlighted_squares.clear()

    def _handle_square_click(self, square_instance: Square, click_cords: str):
        if square_instance.highlighted_metadata.get("highlighted"):
            self.move_piece(
                from_cords=square_instance.highlighted_metadata.get("parent_piece_square"),
                to_cords=click_cords,
            )
            return

        self._clear_move_highlights()
        from_sq = parse_square(click_cords)
        legal_targets = [
            square_name(move.to_square) for move in self.game.board.legal_moves if move.from_square == from_sq
        ]
        for target in legal_targets:
            sq = self.square_map.get(target)
            if sq is not None:
                sq.set_highlight(True, click_cords)
                self.highlighted_squares.add(target)

    def _en_passant_capture(self):
        self._update_last_move_on_board()
        last_move = self.game.get_last_move()
        piece_color_is_white = self.game.color_of_piece_at_square(last_move.to_square)
        if piece_color_is_white is True:
            opponent_pawn_direction = -1
        else:
            opponent_pawn_direction = 1
        squarename = square_name(last_move.to_square)
        squarename = squarename[0] + str(int(squarename[1]) + opponent_pawn_direction)
        self.square_map[squarename].update_content(None)

    def _update_last_move_on_board(self):
        last_move = self.game.get_last_move()
        self.square_map[square_name(last_move.from_square)].update_content(None)
        self.square_map[square_name(last_move.to_square)].update_content(
            ChessPiece(self.game.piece_at_square(last_move.to_square))
        )
                   
    def move_piece(self, from_cords: str, to_cords: str):
        requested_move = Move(parse_square(from_cords), parse_square(to_cords))
        self._clear_move_highlights()
        movement_type = self.game.get_move_type(requested_move)
        print(movement_type)
        #TODO: Implement other UI features, ex: castling, promotion etc/
        if requested_move in self.game.board.legal_moves:
            if self.game.board.is_en_passant(requested_move):
                self.game.board.push(requested_move)
                self._en_passant_capture()
            else:
                self.game.board.push(requested_move)
                self._update_last_move_on_board()
            self._flip_board()

