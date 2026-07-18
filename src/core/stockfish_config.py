from __future__ import annotations

import os
import platform as _platform
from dataclasses import dataclass
from enum import Enum


ELO_MIN = 1320
ELO_MAX = 3190


STOCKFISH_ELO_PRESETS: dict[str, int] = {
    "beginner": 1320,
    "casual": 1500,
    "intermediate": 1800,
    "advanced": 2100,
    "expert": 2500,
    "master": 2800,
    "grandmaster": 3190,
}


def elo_label(elo: int) -> str:
    if elo >= 3190:
        return "Grandmaster"
    if elo >= 2800:
        return "Master"
    if elo >= 2500:
        return "Expert"
    if elo >= 2100:
        return "Advanced"
    if elo >= 1800:
        return "Intermediate"
    if elo >= 1500:
        return "Casual"
    return "Beginner"


def preset_name_for_elo(elo: int) -> str:
    rev = sorted(STOCKFISH_ELO_PRESETS.items(), key=lambda x: -x[1])
    for name, preset_elo in rev:
        if elo >= preset_elo:
            return name
    return "beginner"


def preset_elo(name: str) -> int | None:
    return STOCKFISH_ELO_PRESETS.get(name)


def preset_options() -> list[tuple[str, str]]:
    rev = sorted(STOCKFISH_ELO_PRESETS.items(), key=lambda x: x[1])
    return [(name, f"{name.title()} ({elo})") for name, elo in rev]


def rating_context(elo: int) -> str:
    sep = "  \u00b7  "
    return f"Lichess ~{elo}{sep}Chess.com ~{max(100, elo - 200)}"


class EloLevel(Enum):
    BEGINNER = (1320, "Beginner")
    CASUAL = (1500, "Casual")
    INTERMEDIATE = (1800, "Intermediate")
    ADVANCED = (2100, "Advanced")
    EXPERT = (2500, "Expert")
    MASTER = (2800, "Master")
    GRANDMASTER = (3190, "Grandmaster")

    def __new__(cls, elo: int, label: str):
        obj = object.__new__(cls)
        obj._value_ = elo
        obj.label = label
        return obj

    @property
    def elo(self) -> int:
        return self._value_


ELO_LEVELS: list[tuple[str, int]] = [(lvl.label, lvl.elo) for lvl in EloLevel]


def elo_label(elo: int) -> str:
    label = "Grandmaster"
    for lvl in EloLevel:
        if elo <= lvl.elo:
            label = lvl.label
            break
    return label


STOCKFISH_GITHUB_REPO = "official-stockfish/Stockfish"


WINDOWS_ASSET_FILTER = "windows-x86-64"
WINDOWS_BINARY_NAME = "stockfish.exe"
WINDOWS_ARCHIVE_BINARY_NAME = "stockfish.exe"


ANDROID_ARM64_ASSET_FILTER = "android-arm64-universal"
ANDROID_ARM64_BINARY_NAME = "stockfish"
ANDROID_ARM64_ARCHIVE_BINARY_NAME = "stockfish"

ANDROID_ARMv7_ASSET_FILTER = "android-armv7-neon"
ANDROID_ARMv7_BINARY_NAME = "stockfish"
ANDROID_ARMv7_ARCHIVE_BINARY_NAME = "stockfish"


@dataclass(frozen=True)
class StockfishDownloadConfig:
    github_repo: str = STOCKFISH_GITHUB_REPO
    asset_name_filter: str = ""
    binary_name: str = ""
    archive_binary_name: str = ""
    label: str = ""
    description: str = ""


WINDOWS_DOWNLOAD_CONFIG = StockfishDownloadConfig(
    github_repo=STOCKFISH_GITHUB_REPO,
    asset_name_filter=WINDOWS_ASSET_FILTER,
    binary_name=WINDOWS_BINARY_NAME,
    archive_binary_name=WINDOWS_ARCHIVE_BINARY_NAME,
    label="Windows x86-64 (Universal)",
    description="Auto-selects best instruction set for your CPU.",
)

ANDROID_ARM64_DOWNLOAD_CONFIG = StockfishDownloadConfig(
    github_repo=STOCKFISH_GITHUB_REPO,
    asset_name_filter=ANDROID_ARM64_ASSET_FILTER,
    binary_name=ANDROID_ARM64_BINARY_NAME,
    archive_binary_name=ANDROID_ARM64_ARCHIVE_BINARY_NAME,
    label="Android ARM64",
    description="For 64-bit ARM Android devices.",
)

ANDROID_ARMv7_DOWNLOAD_CONFIG = StockfishDownloadConfig(
    github_repo=STOCKFISH_GITHUB_REPO,
    asset_name_filter=ANDROID_ARMv7_ASSET_FILTER,
    binary_name=ANDROID_ARMv7_BINARY_NAME,
    archive_binary_name=ANDROID_ARMv7_ARCHIVE_BINARY_NAME,
    label="Android ARMv7",
    description="For 32-bit ARM Android devices.",
)


def get_platform_string() -> str:
    if "ANDROID_ROOT" in os.environ:
        return "android"
    system = _platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return system


def is_android() -> bool:
    return get_platform_string() == "android"


def is_windows() -> bool:
    return get_platform_string() == "windows"


def get_windows_download_config() -> StockfishDownloadConfig:
    return WINDOWS_DOWNLOAD_CONFIG


def get_android_download_configs() -> list[StockfishDownloadConfig]:
    return [ANDROID_ARM64_DOWNLOAD_CONFIG, ANDROID_ARMv7_DOWNLOAD_CONFIG]


def get_platform_download_configs() -> list[StockfishDownloadConfig]:
    if is_android():
        return get_android_download_configs()
    if is_windows():
        return [WINDOWS_DOWNLOAD_CONFIG]
    return []


def android_asset_path(engine_name: str = "stockfish") -> str:
    import platform as _platform
    machine = _platform.machine()
    abi = "arm64-v8a" if "64" in machine else "armeabi-v7a"
    return f"stockfish/android/{abi}/{engine_name}"
