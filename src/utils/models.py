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
    ONE_PLUS_ZERO: Tuple[int, int] = (1, 0)
    ONE_PLUS_ONE: Tuple[int, int] = (1, 1)
    TWO_PLUS_ONE: Tuple[int, int] = (2, 1)
    THREE_PLUS_ZERO: Tuple[int, int] = (3, 0)
    THREE_PLUS_TWO: Tuple[int, int] = (3, 2)
    FIVE_PLUS_ZERO: Tuple[int, int] = (5, 0)
    FIVE_PLUS_THREE: Tuple[int, int] = (5, 3)
    TEN_PLUS_ZERO: Tuple[int, int] = (10, 0)
    TEN_PLUS_FIVE: Tuple[int, int] = (10, 5)
    FIFTEEN_PLUS_TEN: Tuple[int, int] = (15, 10)
    TWENTY_PLUS_TEN: Tuple[int, int] = (20, 10)
    THIRTY_PLUS_ZERO: Tuple[int, int] = (30, 0)
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

    engine_binary_path: str = ""
    engine_source: str = "bundled"
    engine_downloaded_path: str = ""
    engine_difficulty: str = "intermediate"
    engine_type: str = "stockfish"

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
                if key == "move_animation" and value in MOVE_ANIMATION_OPTIONS:
                    values[key] = value
                elif key == "promotion_default" and value in PROMOTION_DEFAULT_OPTIONS:
                    values[key] = value
                elif key not in {"move_animation", "promotion_default"}:
                    values[key] = value

        if not values.get("engine_binary_path") and payload.get("stockfish_binary_path"):
            values["engine_binary_path"] = payload["stockfish_binary_path"]
        if not values.get("engine_source") and payload.get("stockfish_source"):
            values["engine_source"] = payload["stockfish_source"]
        if not values.get("engine_downloaded_path") and payload.get("stockfish_downloaded_path"):
            values["engine_downloaded_path"] = payload["stockfish_downloaded_path"]
        if not values.get("engine_difficulty") and payload.get("stockfish_difficulty"):
            values["engine_difficulty"] = payload["stockfish_difficulty"]

        return cls(**values)

    def updated(self, **changes: Any) -> "AppSettings":
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
class Lc0GameConfig:
    use_preset: bool = True
    preset_name: str = "intermediate"
    network_name: str = "T1-256x10-distilled"
    network_path: str = ""
    backend: str = "blas"
    threads: int = 2
    minibatch_size: int = 256
    temperature: float = 0.0
    cpuct: float = 3.4
    elo: int = 1500
    max_playouts: int = 0


@dataclass
class Lc0DifficultyPreset:
    name: str
    description: str
    network: str
    temperature: float
    cpuct: float
    threads: int
    playouts: int


@dataclass
class StockfishGameConfig:
    elo: int = 1800
    threads: int = 2
    hash_mb: int = 256


@dataclass
class StockfishDifficultyPreset:
    name: str
    description: str
    elo: int
