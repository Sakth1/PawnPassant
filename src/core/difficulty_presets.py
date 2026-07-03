"""Difficulty presets with randomized parameter ranges.

Each preset defines min/max ranges for ELO, skill level, and depth.
At game start, the actual parameters are randomly selected within each range.
"""

from utils.models import DifficultyPreset

DIFFICULTY_PRESETS: dict[str, DifficultyPreset] = {
    "beginner": DifficultyPreset(
        name="Beginner",
        description="Perfect for new players learning the game.",
        elo_min=100,
        elo_max=300,
        skill_min=0,
        skill_max=2,
        depth_min=1,
        depth_max=5,
    ),
    "intermediate": DifficultyPreset(
        name="Intermediate",
        description="For casual players with basic experience.",
        elo_min=800,
        elo_max=1200,
        skill_min=5,
        skill_max=8,
        depth_min=8,
        depth_max=12,
    ),
    "advanced": DifficultyPreset(
        name="Advanced",
        description="For experienced club-level players.",
        elo_min=1500,
        elo_max=1800,
        skill_min=12,
        skill_max=15,
        depth_min=12,
        depth_max=16,
    ),
    "expert": DifficultyPreset(
        name="Expert",
        description="Strong competition-level play.",
        elo_min=2000,
        elo_max=2500,
        skill_min=16,
        skill_max=20,
        depth_min=16,
        depth_max=20,
    ),
    "master": DifficultyPreset(
        name="Master",
        description="Maximum engine strength with full analysis depth.",
        elo_min=2500,
        elo_max=3190,
        skill_min=20,
        skill_max=20,
        depth_min=20,
        depth_max=24,
    ),
}


def get_preset(name: str) -> DifficultyPreset | None:
    return DIFFICULTY_PRESETS.get(name)


def preset_options() -> list[tuple[str, str]]:
    return [(key, p.name) for key, p in DIFFICULTY_PRESETS.items()]
