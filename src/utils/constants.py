"""Project-wide constants for chess assets and special-move square mappings."""

import os
from pathlib import Path
from typing import Dict

# Map python-chess piece symbols to the bundled image asset names.
SYMBOL_MAP: Dict[str, str] = {
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
ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = Path(ROOT_DIR, "assets")
PIECES_DIR = Path(ASSET_DIR, "pieces", "default")
FONT_DIR = Path(ASSET_DIR, "fonts")

# Keep rook source and destination squares centralized for castling UI updates.
CASTLING_ROOK_START_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "a1",
    "KING_SIDE_WHITE": "h1",
    "QUEEN_SIDE_BLACK": "a8",
    "KING_SIDE_BLACK": "h8",
}

CASTLING_ROOK_END_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "d1",
    "KING_SIDE_WHITE": "f1",
    "QUEEN_SIDE_BLACK": "d8",
    "KING_SIDE_BLACK": "f8",
}
