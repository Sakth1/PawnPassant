from chess import Board, Move, Square
from Core.MoveType import MoveType


class Game:
    def __init__(self):
        self.board: Board = Board()

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

    def is_game_over(self):
        return self.board.is_game_over()

    def piece_at_square(self, square: Square):
        return self.board.piece_at(square)

    def color_of_piece_at_square(self, square: Square):
        return self.board.color_at(square)

    def get_last_move(self):
        return self.board.move_stack[-1]

    def get_winner(self):
        if self.board.is_checkmate():
            return "Black" if self.board.turn else "White"
        elif self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            return "Draw"
        else:
            return None
