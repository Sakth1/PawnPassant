"""Difficulty presets — re-exports from stockfish_config for backward compat.

Stockfish Elo levels map to UCI_Elo values (1320–3190).
UCI_LimitStrength must be enabled for Elo limiting to take effect.
"""

from core.stockfish_config import (
    STOCKFISH_ELO_PRESETS,
    elo_label as stockfish_elo_label,
    elo_label,
    preset_name_for_elo as stockfish_preset_name_for_elo,
    preset_elo as stockfish_preset_elo,
    preset_options as stockfish_preset_options,
    rating_context as stockfish_rating_context,
    rating_context,
)


# Legacy Lc0 stubs — kept for backward compat during migration
from utils.models import DifficultyPreset

DIFFICULTY_PRESETS: dict[str, DifficultyPreset] = {}
DIFFICULTY_LABELS: dict[str, tuple[int, int]] = {}


def elo_to_playouts(elo: int) -> int:
    return 0


def elo_to_temperature(elo: int) -> float:
    return 0.0


def get_preset(name: str) -> DifficultyPreset | None:
    return None


def preset_options() -> list[tuple[str, str]]:
    return []
