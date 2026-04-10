from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TimeControl:
    # Default clock time control
    ZERO_PLUS_ZERO: Tuple[float, int] = (0.1, 0)
    ONE_PLUS_ZERO: Tuple[int, int] = (1, 0)  # Bullet
    ONE_PLUS_ONE: Tuple[int, int] = (1, 1)
    TWO_PLUS_ONE: Tuple[int, int] = (2, 1)
    THREE_PLUS_ZERO: Tuple[int, int] = (3, 0)  # Blitz
    THREE_PLUS_TWO: Tuple[int, int] = (3, 2)
    FIVE_PLUS_ZERO: Tuple[int, int] = (5, 0)
    FIVE_PLUS_THREE: Tuple[int, int] = (5, 3)
    TEN_PLUS_ZERO: Tuple[int, int] = (10, 0)  # Rapid
    TEN_PLUS_FIVE: Tuple[int, int] = (10, 5)
    FIFTEEN_PLUS_TEN: Tuple[int, int] = (15, 10)
    TWENTY_PLUS_TEN: Tuple[int, int] = (20, 10)
    THIRTY_PLUS_ZERO: Tuple[int, int] = (30, 0)  # Classical
    THIRTY_PLUS_THIRTY: Tuple[int, int] = (30, 30)
    SIXETY_PLUS_ZERO: Tuple[int, int] = (60, 0)
    SIXETY_PLUS_SIXETY: Tuple[int, int] = (60, 60)


@dataclass(frozen=True)
class ActiveColor:
    WHITE: str = "white"
    BLACK: str = "black"
