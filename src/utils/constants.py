"""Project-wide constants for chess assets, special-move square mappings,
board dimensions, layout defaults, timing, animation, colors, and settings
validation sets.

Single-source-of-truth for every value that must stay in sync across multiple
modules. Change the value here to update it everywhere it is used.
"""

import os
from pathlib import Path
from typing import Dict, List, Set

# ── Asset paths ─────────────────────────────────────────────────────────────

#: Maps python-chess piece symbols to bundled PNG asset stem names.
#: Uppercase symbols are white pieces and lowercase symbols are black pieces.
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

#: Font family name used by Flet clock timer controls.
FONT_FAMILY = "RobotoMono"

#: Directory used for downloaded engine binaries (desktop fallback).
ENGINE_DIR: Path = Path(ROOT_DIR) / "assets" / "engine"


# ── Castling square maps ────────────────────────────────────────────────────

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

CASTLING_KING_START_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "e1",
    "KING_SIDE_WHITE": "e1",
    "QUEEN_SIDE_BLACK": "e8",
    "KING_SIDE_BLACK": "e8",
}

CASTLING_KING_END_SQUARE: Dict[str, str] = {
    "QUEEN_SIDE_WHITE": "c1",
    "KING_SIDE_WHITE": "g1",
    "QUEEN_SIDE_BLACK": "c8",
    "KING_SIDE_BLACK": "g8",
}


# ── Board dimensions ────────────────────────────────────────────────────────

#: Number of files (columns) and ranks (rows) on a chessboard.
BOARD_SIZE = 8

#: Maximum number of captured piece slots per color.
MAX_CAPTURES = 16

#: Number of columns in the captured-piece grid view.
CAPTURE_GRID_COLUMNS = 4


# ── Layout defaults (pixels) ────────────────────────────────────────────────

#: Fallback page width used when the Flet viewport reports ``0``.
DEFAULT_PAGE_WIDTH = 960

#: Fallback page height used when the Flet viewport reports ``0``.
DEFAULT_PAGE_HEIGHT = 800

#: Minimum viewport width enforced after safe-area padding is subtracted.
MIN_PAGE_WIDTH = 320.0

#: Minimum viewport height enforced after safe-area padding is subtracted.
MIN_PAGE_HEIGHT = 480.0

#: Default chess square size before responsive layout scales it.
DEFAULT_SQUARE_SIZE = 60

#: Height of the NavigationBar control subtracted from available game height.
NAVIGATION_BAR_HEIGHT = 72

#: Smallest legal chess square size so pieces and labels remain usable.
MIN_SQUARE_SIZE = 34

#: Largest chess square size so desktop layouts do not become oversized.
MAX_SQUARE_SIZE = 96


# ── Time / clock constants ──────────────────────────────────────────────────

#: Millisecond equivalents of standard time units.
MS_PER_MINUTE = 60_000
MS_PER_SECOND = 1_000

#: Remaining-seconds threshold below which the clock emits millisecond ticks.
DEFAULT_CRITICAL_THRESHOLD_SECONDS = 10

#: Worker-thread polling interval in milliseconds.
TICK_INTERVAL_MS = 10


# ── Animation ───────────────────────────────────────────────────────────────

#: User-facing speed names mapped to movement animation durations in ms.
MOVE_ANIMATION_DURATIONS: Dict[str, int] = {
    "off": 0,
    "fast": 60,
    "normal": 120,
    "slow": 220,
}

#: Speed names accepted by the settings model (derived from the durations map).
MOVE_ANIMATION_OPTIONS: Set[str] = set(MOVE_ANIMATION_DURATIONS.keys())

#: Default animation duration used when settings do not override.
DEFAULT_MOVE_ANIMATION_DURATION_MS = 120

#: Piece image scale applied on click feedback.
PIECE_CLICK_SCALE = 1.5

#: Seconds before the click-feedback scale resets to ``1``.
PIECE_CLICK_RESET_DELAY = 0.16

#: Scale applied to the drag feedback ghost.
DRAG_FEEDBACK_SCALE = 1.08

#: Opacity of the source square ``content_when_dragging`` placeholder.
DRAG_OPACITY_VANISH = 0.18

#: Opacity of the drag feedback ghost.
DRAG_OPACITY_FEEDBACK = 0.96

#: Duration of square highlight animation in milliseconds.
SQUARE_ANIMATION_DURATION_MS = 90


# ── Promotion ───────────────────────────────────────────────────────────────

#: Accepted persisted values for automatic or interactive promotion choice.
PROMOTION_DEFAULT_OPTIONS: Set[str] = frozenset(
    {"ask", "queen", "rook", "bishop", "knight"}
)


# ── Drag / drop groups ──────────────────────────────────────────────────────

#: Drag group shared by all main-board piece controls.
BOARD_DRAG_GROUP = "chess-piece"


# ── Time-control categories ─────────────────────────────────────────────────

#: Display order for time-control groups derived from preset length.
CATEGORY_ORDER: List[str] = ["bullet", "blitz", "rapid", "classical"]

#: Human-readable labels for each time-control category.
CATEGORY_LABELS: Dict[str, str] = {
    "bullet": "Bullet",
    "blitz": "Blitz",
    "rapid": "Rapid",
    "classical": "Classical",
}


# ── Colours ─────────────────────────────────────────────────────────────────

#: Background of the normal-state timer container.
TIMER_BG = "#262626"

#: Background of the critical-state (low time) timer container.
TIMER_CRITICAL_BG = "#250E0E"

#: Background of the captured-pieces panel.
CAPTURED_PANEL_BG = "#1F1F1F"

#: Background of empty captured-piece slots (InvisibleSquare).
INVISIBLE_SQUARE_BG = "#343434"
