from dataclasses import dataclass
from typing import Optional

from utils.models import ActiveColor
from ui.chess_piece import ChessPiece


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
class PieceCapturedEvent(BaseEvent):
    piece: ChessPiece
    color: ActiveColor
