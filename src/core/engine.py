"""Game-state helpers built on top of python-chess."""

from chess import Board, Move, Square, Color, PAWN, square_rank
from typing import Optional

from core.movetype import MoveType


class Game:
    """Wraps the chess board with helpers tailored to the UI layer."""

    def __init__(self):
        self.board: Board = Board()

    def reset_board(self):
        """Restore the standard starting position."""

        self.board = Board()

    def set_board_fen(self, fen: str):
        """Load a board position from a FEN string."""

        self.board = Board(fen)

    def get_board_fen(self):
        """Return the current board position as FEN."""

        return self.board.fen()
    
    def get_active_color(self) -> Color:
        return self.board.turn

    def get_move_type(self, move: Move) -> MoveType:
        """Classify a move so the UI can apply the correct visual update path."""

        if self.board.is_queenside_castling(move):
            return MoveType.QUEEN_SIDE_CASTLING
        if self.board.is_kingside_castling(move):
            return MoveType.KING_SIDE_CASTLING
        if self.board.is_en_passant(move):
            return MoveType.EN_PASSANT
        if self._is_promotion_move(move):
            return MoveType.PROMOTION
        if self.board.is_capture(move):
            return MoveType.CAPTURE
        return MoveType.NORMAL

    def _is_promotion_move(self, move: Move) -> bool:
        """Return whether the move is a pawn move that reaches the back rank."""

        piece = self.board.piece_at(move.from_square)
        if piece is None or piece.piece_type != PAWN:
            return False
        return square_rank(move.to_square) in (0, 7)

    def move(self, move: Move):
        """Apply a legal move to the underlying board."""

        self.board.push(move)

    def get_move_san(self, move: Move) -> str:
        """Format a move using standard algebraic notation."""

        return self.board.san(move)

    def is_game_over(self):
        """Return whether the current position has ended the game."""

        return self.board.is_game_over()

    def display_board(self):
        """Print the board for quick local debugging."""

        print(self.board)

    def piece_at_square(self, square: Square):
        """Return the piece currently occupying a square, if any."""

        return self.board.piece_at(square)

    def color_of_piece_at_square(self, square: Square) -> Optional[Color]:
        """Return the color of the piece on a square, if present."""

        return self.board.color_at(square)

    def get_last_move(self):
        """Return the most recently played move."""

        return self.board.move_stack[-1]

    def get_winner(self):
        """Return the winning side name, `Draw`, or `None` if play continues."""

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

    def get_result_summary(self) -> tuple[Optional[str], str, str]:
        """Return a normalized winner, reason, and user-facing message."""

        winner = self.get_winner()
        if self.board.is_checkmate():
            return winner, "checkmate", f"{winner} wins by checkmate."
        if self.board.is_stalemate():
            return "Draw", "stalemate", "Draw by stalemate."
        if self.board.is_insufficient_material():
            return "Draw", "insufficient_material", "Draw by insufficient material."
        if self.board.is_seventyfive_moves():
            return "Draw", "seventyfive_moves", "Draw by seventy-five move rule."
        if self.board.is_fivefold_repetition():
            return "Draw", "fivefold_repetition", "Draw by fivefold repetition."
        return None, "ongoing", ""
