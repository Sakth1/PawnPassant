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
from ui.chess_piece import ChessPiece


class BaseEvent:
    """Marker base class for events emitted on :mod:`utils.signals`."""


class PieceMovedEvent(BaseEvent):
    """Published after a legal board move is committed.

    The event tells clock and side-panel subscribers to advance their state.
    """

    pass


class GameStartedEvent(BaseEvent):
    """Published when a fresh game begins or the board is reset for replay."""

    pass


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
