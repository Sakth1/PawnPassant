import os
from pathlib import Path

from chess.svg import PIECES

SYMBOL_MAP = {
    "P": "WHITE_PAWN",
    "N": "WHITE_KNIGHT",
    "B": "WHITE_BISHOP",
    "R": "WHITE_ROOK",
    "Q": "WHITE_QUEEN",
    "K": "WHITE_KING",
    "p": "BLACK_PAWN",
    "n": "BLACK_KNIGHT",
    "b": "BLACK_BISHOP",
    "r": "BLACK_ROOK",
    "q": "BLACK_QUEEN",
    "k": "BLACK_KING",
}
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = Path(ROOT_DIR, "assets")
PIECES_DIR = Path(ASSET_DIR, "pieces", "default")