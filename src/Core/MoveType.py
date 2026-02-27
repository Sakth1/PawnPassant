from enum import Enum


class MoveType(str, Enum):
    NORMAL = "normal"
    CAPTURE = "capture"
    EN_PASSANT = "en_passant"
    KING_SIDE_CASTLING = "king_side_castling"
    QUEEN_SIDE_CASTLING = "queen_side_castling"
    PROMOTION = "promotion"
