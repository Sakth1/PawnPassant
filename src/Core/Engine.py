from chess import Board, Move, Square, Color, square_file, square_rank
from typing import Optional

from Core.MoveType import MoveType


class Game:
    def __init__(self):
        self.board: Board = Board()

    def reset_board(self):
        self.board = Board()

    def set_board_fen(self, fen: str):
        self.board = Board(fen)

    def get_board_fen(self):
        return self.board.fen()

    def get_move_type(self, move: Move) -> MoveType:
        if self.board.is_castling(move):
            return MoveType.CASTLING
        if self.board.is_en_passant(move):
            return MoveType.EN_PASSANT
        if move.promotion is not None:
            return MoveType.PROMOTION
        if self.board.is_capture(move):
            return MoveType.CAPTURE
        return MoveType.NORMAL

    def move(self, move: Move):
        self.board.push(move)

    def castling_side(self, move: Move):
        if self.board.is_queenside_castling(move):
            return "q"
        if self.board.is_kingside_castling(move):
            return "k"
        return None

    def is_game_over(self):
        return self.board.is_game_over()

    def display_board(self):
        print(self.board)

    def piece_at_square(self, square: Square):
        return self.board.piece_at(square)

    def color_of_piece_at_square(self, square: Square) -> Optional[Color]:
        return self.board.color_at(square)

    def get_last_move(self):
        return self.board.move_stack[-1]

    def get_winner(self):
        if self.board.is_checkmate():
            return "Black" if self.board.turn else "White"
        elif (
            self.board.is_stalemate()
            or self.board.is_insufficient_material()
            or self.board.is_seventyfive_moves()
            or self.board.is_fivefold_repetition()
        ):
            return "Draw"
        else:
            return None
