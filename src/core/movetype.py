"""Move classifications used to keep board updates aligned with chess rules."""

from enum import Enum


class MoveType(str, Enum):
    """Enumerates the move behaviors the UI needs to render specially."""

    NORMAL = "normal"
    CAPTURE = "capture"
    EN_PASSANT = "en_passant"
    KING_SIDE_CASTLING = "king_side_castling"
    QUEEN_SIDE_CASTLING = "queen_side_castling"
    PROMOTION = "promotion"
