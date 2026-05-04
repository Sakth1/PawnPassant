from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Tuple
from enum import StrEnum
import chess


@dataclass(frozen=True)
class TimeControl:
    # Default clock time control
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
    WHITE: chess.Color = chess.WHITE
    BLACK: chess.Color = chess.BLACK


@dataclass(frozen=True)
class AppSettings:
    show_legal_moves: bool = True
    show_tap_feedback: bool = True
    auto_flip_board: bool = True
    show_coordinates: bool = True
    move_animation: str = "normal"
    confirm_moves: bool = False
    promotion_default: str = "queen"
    critical_time_seconds: int = 10
    show_milliseconds_in_critical: bool = True
    confirm_resign: bool = True
    confirm_draw: bool = True

    MOVE_ANIMATION_OPTIONS = {"off", "fast", "normal", "slow"}
    PROMOTION_DEFAULT_OPTIONS = {"ask", "queen", "rook", "bishop", "knight"}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AppSettings":
        if not isinstance(payload, dict):
            return cls()

        defaults = cls()
        values = defaults.to_dict()
        field_names = {field.name for field in fields(cls)}

        for key, value in payload.items():
            if key not in field_names:
                continue
            default_value = getattr(defaults, key)
            if isinstance(default_value, bool):
                if isinstance(value, bool):
                    values[key] = value
            elif isinstance(default_value, int) and not isinstance(default_value, bool):
                if isinstance(value, int) and 0 <= value <= 60:
                    values[key] = value
            elif isinstance(default_value, str):
                if key == "move_animation" and value in cls.MOVE_ANIMATION_OPTIONS:
                    values[key] = value
                elif (
                    key == "promotion_default"
                    and value in cls.PROMOTION_DEFAULT_OPTIONS
                ):
                    values[key] = value
                elif key not in {"move_animation", "promotion_default"}:
                    values[key] = value

        return cls(**values)

    def updated(self, **changes: Any) -> "AppSettings":
        return self.from_dict({**self.to_dict(), **changes})
