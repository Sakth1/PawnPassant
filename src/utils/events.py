"""Application event payloads exchanged through the in-process signal bus.

The UI is intentionally split into independent Flet controls: the board should
not know how the clock draws itself, and the clock should not know how result
dialogs are presented. These small event classes form the contract between those
components and are written as stable docstring-friendly types for future
generated API documentation.
"""

from dataclasses import dataclass
from typing import Optional

from utils.models import ActiveColor, AppSettings
from utils.game_state import GameAgainst
from ui.chess_piece import ChessPiece


class BaseEvent:
    """Marker base class for events emitted on :mod:`utils.signals`."""


@dataclass(frozen=True)
class PieceMovedEvent(BaseEvent):
    """Published after a legal board move is committed.

    The event tells clock and side-panel subscribers to advance their state.
    """

    board_fen: str
    """FEN representation of the board after the move. Used by stockfish."""
    active_color: ActiveColor
    """Side to move after the move."""


@dataclass(frozen=True)
class GameStartedEvent(BaseEvent):
    """Published when a fresh game begins or the board is reset for replay."""

    opponent_nature: GameAgainst
    """Identity of the opponent in the current or upcoming game."""


@dataclass(frozen=True)
class SettingsChangedEvent(BaseEvent):
    """Published whenever settings are loaded, reset, or updated."""

    #: Complete settings snapshot that subscribers should apply as authoritative.
    settings: AppSettings


@dataclass(frozen=True)
class GameEndedEvent(BaseEvent):
    """Published when a checkmate, draw, resignation, or timeout ends the game."""

    winner: Optional[str]
    """Winner name, ``"Draw"``, or ``None`` when no winner applies."""

    reason: str
    """Machine-readable result reason such as ``"checkmate"`` or ``"time"``."""

    message: str
    """User-facing summary shown by the result dialog."""


@dataclass(frozen=True)
class ClockTickEvent(BaseEvent):
    """Published by the clock backend when a timer display should change."""

    #: Side whose visible timer should be redrawn.
    color: ActiveColor
    #: Whole minutes remaining for the side's clock display.
    minutes: int
    #: Whole seconds remaining after minutes are removed.
    seconds: int
    #: Milliseconds remaining within the current second.
    milliseconds: int
    #: Whether the clock is inside the configured critical-time threshold.
    is_critical: bool


@dataclass(frozen=True)
class ClockStateEvent(BaseEvent):
    """Published for clock lifecycle transitions and flag-fall events."""

    state: str
    """Lifecycle state: ``started``, ``switched``, ``stopped``, or ``flagged``."""

    active_color: Optional[ActiveColor]
    """Color associated with the state, or ``None`` when no side is active."""


@dataclass(frozen=True)
class PieceCapturedEvent(BaseEvent):
    """Published when a move removes a piece from the board."""

    piece: ChessPiece
    """Captured piece control moved into the captured-pieces panel."""

    color: ActiveColor
    """Color of the player who made the capture."""


# ── Stockfish download workflow events ───────────────────────────────────


@dataclass(frozen=True)
class StockfishInfoReadyEvent(BaseEvent):
    """Published after release info is fetched and best asset determined.

    UI can listen for this to display download confirmation.
    """

    release_tag: str
    """GitHub release tag, e.g. ``"sf_17"``."""
    asset_name: str
    """Best-matching asset filename for the current system."""
    asset_size_bytes: int
    """Size of the best-matching asset in bytes."""
    asset_subarch: str
    """CPU sub-architecture of the best asset, e.g. ``"avx2"``."""


@dataclass(frozen=True)
class StockfishDownloadProgressEvent(BaseEvent):
    """Emitted during download to drive a progress indicator."""

    bytes_downloaded: int
    """Bytes transferred so far."""
    total_bytes: int
    """Total bytes to transfer."""


@dataclass(frozen=True)
class StockfishDownloadCompleteEvent(BaseEvent):
    """Emitted when the Stockfish binary has been downloaded and saved."""

    download_path: str
    """Absolute path to the downloaded binary."""
    asset_name: str
    """Name of the downloaded asset."""


@dataclass(frozen=True)
class StockfishDownloadFailedEvent(BaseEvent):
    """Emitted when the Stockfish download fails for any reason."""

    error_message: str
    """Human-readable error description."""


@dataclass(frozen=True)
class BinaryVerificationResultEvent(BaseEvent):
    """Emitted after verifying a Stockfish binary path."""

    valid: bool
    """Whether the binary is a valid Stockfish executable."""
    path: str
    """The path that was verified."""
    version: str
    """Version string if valid, or error message if invalid."""
