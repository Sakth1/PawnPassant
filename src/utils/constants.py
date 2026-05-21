"""Project-wide constants for chess assets and special-move square mappings.

The board UI works with python-chess coordinates, while Flet renders image
assets and manually moves controls for special moves. Centralizing these values
keeps the UI update code readable and gives future generated documentation a
single place to describe the project's fixed paths and square maps.
"""

import os
from pathlib import Path
from typing import Dict

#: Maps python-chess piece symbols to bundled PNG asset stem names.
#:
#: Uppercase symbols are white pieces and lowercase symbols are black pieces.
#: The values intentionally omit the file extension because
#: :class:`ui.chess_piece.ChessPiece` builds platform-friendly asset paths.
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

#: Absolute path to the ``src`` directory; used as the anchor for bundled assets.
ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Directory containing app images, icons, fonts, and chess piece artwork.
ASSET_DIR = Path(ROOT_DIR, "assets")

#: Directory containing the default chess piece PNG set.
PIECES_DIR = Path(ASSET_DIR, "pieces", "default")

#: Directory containing bundled font files registered with Flet at startup.
FONT_DIR = Path(ASSET_DIR, "fonts")

#: Rook source squares for each castling side/color combination.
#:
#: The engine applies castling as a single king move. The UI still has to move
#: the rook control, so these maps describe the manual visual update.
CASTLING_ROOK_START_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "a1",
    "KING_SIDE_WHITE": "h1",
    "QUEEN_SIDE_BLACK": "a8",
    "KING_SIDE_BLACK": "h8",
}

#: Rook destination squares after the corresponding castling move completes.
CASTLING_ROOK_END_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "d1",
    "KING_SIDE_WHITE": "f1",
    "QUEEN_SIDE_BLACK": "d8",
    "KING_SIDE_BLACK": "f8",
}

#: King source squares for each castling side/color combination.
CASTLING_KING_START_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "e1",
    "KING_SIDE_WHITE": "e1",
    "QUEEN_SIDE_BLACK": "e8",
    "KING_SIDE_BLACK": "e8",
}

#: King destination squares after the corresponding castling move completes.
CASTLING_KING_END_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "c1",
    "KING_SIDE_WHITE": "g1",
    "QUEEN_SIDE_BLACK": "c8",
    "KING_SIDE_BLACK": "g8",
}
