from dataclasses import dataclass

from chess.engine import T


@dataclass(frozen=True)
class TimeControl:
    # Default clock time control
    ONE_PLUS_ZERO = (1, 0)  # Bullet
    ONE_PLUS_ONE = (1, 1)
    TWO_PLUS_ONE = (2, 1)
    THREE_PLUS_ZERO = (3, 0)  # Blitz
    THREE_PLUS_TWO = (3, 2)
    FIVE_PLUS_ZERO = (5, 0)
    FIVE_PLUS_THREE = (5, 3)
    TEN_PLUS_ZERO = (10, 0)  # Rapid
    TEN_PLUS_FIVE = (10, 5)
    FIFTEEN_PLUS_TEN = (15, 10)
    TWENTY_PLUS_TEN = (20, 10)
    THIRTY_PLUS_ZERO = (30, 0)  # Classical
    THIRTY_PLUS_THIRTY = (30, 30)
    SIXETY_PLUS_ZERO = (60, 0)
    SIXETY_PLUS_SIXETY = (60, 60)
