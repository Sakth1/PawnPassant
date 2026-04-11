from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from utils.models import ActiveColor

if TYPE_CHECKING:
    from ui.layout_templates import LayoutTemplate


class BaseEvent:
    """Base event class."""


class PieceModevedEvent(BaseEvent):
    pass


class GameStartedEvent(BaseEvent):
    pass


@dataclass(frozen=True)
class GameEndedEvent(BaseEvent):
    winner: Optional[str]
    reason: str
    message: str


@dataclass(frozen=True)
class ClockTickEvent(BaseEvent):
    color: ActiveColor
    minutes: int
    seconds: int
    milliseconds: int
    is_critical: bool


@dataclass(frozen=True)
class ClockStateEvent(BaseEvent):
    state: str
    active_color: Optional[ActiveColor]


@dataclass(frozen=True)
class LayoutChangedEvent(BaseEvent):
    """Emitted when the layout type switches (desktop/tablet/mobile).
    
    This is different from a simple resize: it indicates a qualitative change
    in the UI structure, not just metric adjustments.
    """
    from_layout: str  # Previous layout type ("desktop", "tablet", "mobile")
    to_layout: str    # New layout type ("desktop", "tablet", "mobile")
    layout_template: Optional["LayoutTemplate"] = None  # The new template instance


@dataclass(frozen=True)
class PieceCapturedEvent(BaseEvent):
    """Emitted when a piece is captured and animation completes.
    
    This signals that a piece has been captured and moved to the captured pieces UI.
    """
    piece_type: str     # Type of piece ("pawn", "knight", "bishop", "rook", "queen", "king")
    captured_by: str    # Player who captured ("white" or "black")


@dataclass(frozen=True)
class CapturedPiecesUpdatedEvent(BaseEvent):
    """Emitted when the captured pieces model is updated.
    
    Components listening to this event should refresh their displayed captured pieces.
    """
    pass

