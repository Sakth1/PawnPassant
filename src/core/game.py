"""Game session manager — board state, move logic, and terminal-event emission.

GameManager owns the python-chess Board directly and provides a clean API
for the UI layer to query and mutate board state without accessing
python-chess internals.
"""

from __future__ import annotations

import logging
from typing import Optional

from chess import Board, Color, Move, PAWN, Piece, Square, square_name, square_rank

from core.movetype import MoveType
from utils.events import GameEndedEvent
from utils.game_state import game_state
from utils.signals import bus

logger = logging.getLogger(__name__)


class GameManager:
    """Encapsulate game state, move logic, and terminal-event emission.

    The UI creates one instance per board and delegates all game queries
    and mutations here rather than touching python-chess internals.
    """

    def __init__(self):
        #: Authoritative python-chess board state for the current game.
        self.board: Board = Board()

    # ── Query API ──────────────────────────────────────────────────────────

    def fen(self) -> str:
        """Return the current board position as FEN."""
        return self.board.fen()

    def active_color(self) -> Color:
        """Return the side to move (``chess.WHITE`` or ``chess.BLACK``)."""
        return self.board.turn

    def piece_at(self, square: Square) -> Optional[Piece]:
        """Return the piece occupying *square*, or ``None``."""
        return self.board.piece_at(square)

    def color_at(self, square: Square) -> Optional[Color]:
        """Return the colour of the piece on *square*, or ``None``."""
        return self.board.color_at(square)

    def last_move(self) -> Move:
        """Return the most recently played move."""
        return self.board.move_stack[-1]

    def move_san(self, move: Move) -> str:
        """Format *move* in standard algebraic notation."""
        return self.board.san(move)

    def move_type(self, move: Move) -> MoveType:
        """Classify *move* so the UI can apply the correct visual update path."""
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

    # ── Move validation ───────────────────────────────────────────────────

    def is_legal(self, move: Move) -> bool:
        """Return whether *move* is currently legal.

        Handles the common case where a user-provided move may be missing
        the promotion field by matching on source/destination only.
        """
        if move in self.board.legal_moves:
            return True
        if move.promotion is None:
            for legal_move in self.board.legal_moves:
                if (
                    legal_move.from_square == move.from_square
                    and legal_move.to_square == move.to_square
                ):
                    return True
        return False

    def legal_targets(self, from_square: Square) -> list[str]:
        """Return algebraic-square strings for every legal destination from *from_square*."""
        return [
            square_name(m.to_square)
            for m in self.board.legal_moves
            if m.from_square == from_square
        ]

    def is_selectable(self, square: Square, turn: Color) -> bool:
        """Return whether *square* holds a piece belonging to *turn*."""
        piece_color = self.board.color_at(square)
        return piece_color is not None and piece_color == turn

    def is_game_over(self) -> bool:
        """Return whether the current position is terminal."""
        return self.board.is_game_over()

    def get_winner(self) -> Optional[str]:
        """Return the winning side name, ``Draw``, or ``None`` if play continues."""
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

    def result_summary(self) -> tuple[Optional[str], str, str]:
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

    # ── Board mutation ─────────────────────────────────────────────────────

    def load_fen(self, fen: str) -> None:
        """Set the board position from a FEN string."""
        self.board = Board(fen)
        logger.info("Board set from FEN fen=%s", fen)

    def reset_board(self) -> None:
        """Restore the standard starting position."""
        self.board = Board()
        logger.info("Board reset")

    def push_move(self, move: Move) -> None:
        """Push *move* to the underlying board."""
        self.board.push(move)
        logger.debug("Move pushed move=%s ply=%s", move.uci(), self.board.ply())

    # ── Event emission ────────────────────────────────────────────────────

    def check_game_over(self) -> Optional[GameEndedEvent]:
        """Emit a ``GameEndedEvent`` if the current position is terminal.

        Returns:
            The emitted event when a terminal state is reached, or ``None``
            if the game is still in progress.
        """
        if not self.board.is_game_over():
            return None

        winner, reason, message = self.result_summary()
        game_state.game_over = True
        logger.info("Terminal board state winner=%s reason=%s", winner, reason)
        event = GameEndedEvent(winner=winner, reason=reason, message=message)
        bus.emit(event)
        return event
