"""Project-wide constants for chess assets and special-move square mappings."""

import os
from pathlib import Path
from typing import List, Dict

# Map python-chess piece symbols to the bundled image asset names.
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
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = Path(ROOT_DIR, "assets")
PIECES_DIR = Path(ASSET_DIR, "pieces", "default")

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

# Default clock time control
TIME_CONTROL: List[str] = [
    "1|0",
    "1|1",
    "2|1",  # Bullet
    "3|0",
    "3|2",
    "5|0",
    "5|3",  # Blitz
    "10|0",
    "10|5",
    "15|10",
    "20|10"  # Rapid
    "30|0",
    "30|30",
    "60|0",
    "60|60",  # Classical
]
