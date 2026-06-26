"""Typed value objects that define user-facing chess app preferences.

These models sit at the boundary between UI controls, persisted settings, and
core behavior. Keeping them small and immutable makes settings updates explicit:
the UI asks for a changed copy, and the controller publishes that copy to the
rest of the app.
"""

import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Optional, Tuple
import chess
from enum import Enum

from utils.constants import MOVE_ANIMATION_OPTIONS, PROMOTION_DEFAULT_OPTIONS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeControl:
    """Named clock presets expressed as ``(minutes, increment_seconds)`` tuples.

    The home screen discovers presets from this dataclass instead of duplicating
    a separate list. That keeps displayed choices and their canonical values in
    one place for future generated documentation and UI expansion.
    """

    # Default clock time controls grouped loosely by common chess speed classes.
    #: One-minute game with no increment; the fastest bullet preset.
    ONE_PLUS_ZERO: Tuple[int, int] = (1, 0)  # Bullet
    #: One-minute game with a one-second increment for playable bullet games.
    ONE_PLUS_ONE: Tuple[int, int] = (1, 1)
    #: Two-minute game with a one-second increment, still categorized as bullet.
    TWO_PLUS_ONE: Tuple[int, int] = (2, 1)
    #: Three-minute game with no increment; the classic blitz baseline.
    THREE_PLUS_ZERO: Tuple[int, int] = (3, 0)  # Blitz
    #: Three-minute game with a two-second increment; the app's default preset.
    THREE_PLUS_TWO: Tuple[int, int] = (3, 2)
    #: Five-minute game with no increment for slower blitz play.
    FIVE_PLUS_ZERO: Tuple[int, int] = (5, 0)
    #: Five-minute game with a three-second increment for increment blitz.
    FIVE_PLUS_THREE: Tuple[int, int] = (5, 3)
    #: Ten-minute game with no increment; the first rapid preset.
    TEN_PLUS_ZERO: Tuple[int, int] = (10, 0)  # Rapid
    #: Ten-minute game with a five-second increment for rapid play.
    TEN_PLUS_FIVE: Tuple[int, int] = (10, 5)
    #: Fifteen-minute game with a ten-second increment for longer rapid games.
    FIFTEEN_PLUS_TEN: Tuple[int, int] = (15, 10)
    #: Twenty-minute game with a ten-second increment at the rapid/classical edge.
    TWENTY_PLUS_TEN: Tuple[int, int] = (20, 10)
    #: Thirty-minute game with no increment; the first classical preset.
    THIRTY_PLUS_ZERO: Tuple[int, int] = (30, 0)  # Classical
    #: Thirty-minute game with a thirty-second increment for classical play.
    THIRTY_PLUS_THIRTY: Tuple[int, int] = (30, 30)
    #: Sixty-minute game with no increment for long-form play.
    SIXETY_PLUS_ZERO: Tuple[int, int] = (60, 0)
    #: Sixty-minute game with a sixty-second increment for maximum clock depth.
    SIXETY_PLUS_SIXETY: Tuple[int, int] = (60, 60)


@dataclass(frozen=True)
class ActiveColor:
    """Canonical color values shared by the engine, clock, and events."""

    #: Python-chess value representing the white side.
    WHITE: chess.Color = chess.WHITE
    #: Python-chess value representing the black side.
    BLACK: chess.Color = chess.BLACK


@dataclass(frozen=True)
class AppSettings:
    """Persisted user preferences that drive board, gameplay, and clock behavior.

    The dataclass is frozen so callers cannot silently mutate settings behind
    the controller. Use :meth:`updated` to validate changes and return a new
    instance that can be emitted through the signal bus.
    """

    #: Whether selectable pieces show legal destination markers.
    show_legal_moves: bool = True
    #: Whether tapped or dragged squares briefly change color for feedback.
    show_tap_feedback: bool = True
    #: Whether the board reverses after each move so the active player faces up.
    auto_flip_board: bool = True
    #: Whether file/rank coordinate labels are rendered on board edges.
    show_coordinates: bool = True

    #: Animation speed key used by the board move animation duration map.
    move_animation: str = "normal"
    #: Whether each normal move must be confirmed before it is committed.
    confirm_moves: bool = False
    #: Promotion behavior: ``ask`` opens the picker; piece names auto-promote.
    promotion_default: str = "queen"

    #: Remaining seconds threshold at which the clock shows critical styling.
    critical_time_seconds: int = 10
    #: Whether critical-time clock display includes hundredths of a second.
    show_milliseconds_in_critical: bool = True
    #: Whether resignation opens a confirmation dialog before ending the game.
    confirm_resign: bool = True
    #: Whether draw agreement opens a confirmation dialog before ending the game.
    confirm_draw: bool = True

    #: Path to the Stockfish engine binary (empty string = not installed).
    stockfish_binary_path: str = ""
    #: Last known difficulty preset used for Stockfish games.
    stockfish_difficulty: str = "intermediate"

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings into JSON-compatible primitive values."""

        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AppSettings":
        """Build settings from untrusted persisted data.

        Args:
            payload: A dictionary loaded from storage, or ``None`` when storage
                is missing or unreadable.

        Returns:
            A valid settings object. Unknown keys, wrong types, and out-of-range
            numeric values are ignored so a bad preference file cannot break app
            startup.
        """

        if not isinstance(payload, dict):
            return cls()

        defaults = cls()
        values = defaults.to_dict()
        field_names = {field.name for field in fields(cls)}

        for key, value in payload.items():
            if key not in field_names:
                continue
            default_value = getattr(defaults, key)
            # Validate by the default value's type so newly added fields inherit
            # the same defensive loading behavior without a separate schema.
            if isinstance(default_value, bool):
                if isinstance(value, bool):
                    values[key] = value
            elif isinstance(default_value, int) and not isinstance(default_value, bool):
                if isinstance(value, int) and 0 <= value <= 60:
                    values[key] = value
            elif isinstance(default_value, str):
                if key == "move_animation" and value in MOVE_ANIMATION_OPTIONS:
                    values[key] = value
                elif key == "promotion_default" and value in PROMOTION_DEFAULT_OPTIONS:
                    values[key] = value
                elif key not in {"move_animation", "promotion_default"}:
                    values[key] = value

        return cls(**values)

    def updated(self, **changes: Any) -> "AppSettings":
        """Return a validated settings copy with the provided field changes."""

        return self.from_dict({**self.to_dict(), **changes})

class Arch(Enum):
    ARM64 = "arm64"
    ARM = "arm"
    X86_64 = "x86_64"
    X86 = "x86"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        labels = {
            Arch.ARM64: "ARM64 (AArch64)",
            Arch.ARM: "ARM (32-bit)",
            Arch.X86_64: "x86-64 (AMD64)",
            Arch.X86: "x86 (32-bit)",
            Arch.UNKNOWN: "Unknown",
        }
        return labels[self]


class Platform(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID = "android"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        labels = {
            Platform.WINDOWS: "Windows",
            Platform.LINUX: "Linux",
            Platform.MACOS: "macOS",
            Platform.ANDROID: "Android",
            Platform.UNKNOWN: "Unknown",
        }
        return labels[self]


class CpuSubarch(Enum):
    GENERIC = "generic"
    MODERN = "modern"
    AVX2 = "avx2"
    BMI2 = "bmi2"
    VNNI = "vnni"
    ARMV8 = "armv8"
    ARMV8_DOTPROD = "armv8_dotprod"
    APPLE_SILICON = "apple_silicon"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        labels = {
            CpuSubarch.GENERIC: "Generic",
            CpuSubarch.MODERN: "Modern",
            CpuSubarch.AVX2: "AVX2",
            CpuSubarch.BMI2: "BMI2",
            CpuSubarch.VNNI: "VNNI",
            CpuSubarch.ARMV8: "ARMv8",
            CpuSubarch.ARMV8_DOTPROD: "ARMv8 DotProd",
            CpuSubarch.APPLE_SILICON: "Apple Silicon",
            CpuSubarch.UNKNOWN: "Unknown",
        }
        return labels[self]


@dataclass(frozen=True)
class SystemInfo:
    arch: Arch
    platform: Platform
    subarch: CpuSubarch = CpuSubarch.UNKNOWN


@dataclass(frozen=True)
class StockfishAsset:
    name: str
    url: str
    size_bytes: int
    sha256: str
    platform: Platform
    arch: Arch
    subarch: CpuSubarch


@dataclass(frozen=True)
class DownloadedAsset:
    asset: StockfishAsset
    download_path: Path
    downloaded_at: str


@dataclass(frozen=True)
class AssetMatchResult:
    """Result of fetching and matching Stockfish release assets."""

    release_tag: str
    best_asset: StockfishAsset
    all_compatible: tuple[StockfishAsset, ...]


@dataclass(frozen=True)
class EngineConfig:
    depth: int = 10
    elo: Optional[int] = None
    skill_level: Optional[int] = None
    threads: int = 1
    hash_mb: int = 256


@dataclass(frozen=True)
class DifficultyPreset:
    name: str
    description: str
    elo_min: int
    elo_max: int
    skill_min: int
    skill_max: int
    depth_min: int
    depth_max: int


@dataclass
class StockfishGameConfig:
    use_preset: bool = True
    preset_name: str = "intermediate"
    elo: int = 1350
    skill_level: Optional[int] = None
    depth: int = 15
    threads: int = 1
    hash_mb: int = 256