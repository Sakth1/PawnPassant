from dataclasses import dataclass
from typing import Optional

from utils.models import ActiveColor


class BaseEvent:
    """Base event class."""


class PieceModevedEvent(BaseEvent):
    pass


class GameStartedEvent(BaseEvent):
    pass


class GameEndedEvent(BaseEvent):
    pass


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
