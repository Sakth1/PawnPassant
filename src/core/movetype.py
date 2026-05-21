"""Move classifications used to keep board updates aligned with chess rules."""

from enum import Enum


class MoveType(str, Enum):
    """Enumerates the move behaviors the UI needs to render specially."""

    #: Ordinary legal move with no captured piece or extra UI cleanup.
    NORMAL = "normal"
    #: Move that captures a piece on the destination square.
    CAPTURE = "capture"
    #: Pawn capture where the captured pawn sits behind the destination square.
    EN_PASSANT = "en_passant"
    #: Castling move where the rook travels from h-file to f-file.
    KING_SIDE_CASTLING = "king_side_castling"
    #: Castling move where the rook travels from a-file to d-file.
    QUEEN_SIDE_CASTLING = "queen_side_castling"
    #: Pawn move to the back rank requiring a promotion piece choice.
    PROMOTION = "promotion"
