from enum import Enum


class MoveType(str, Enum):
    NORMAL = "normal"
    CAPTURE = "capture"
    EN_PASSANT = "en_passant"
    CASTLING = "castling"
    PROMOTION = "promotion"
