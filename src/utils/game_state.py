"""Mutable game session state shared across all Pawn Passant modules.

This module provides a singleton ``game_state`` object that any module can
import and mutate. Changes are immediately visible to every module that holds
a reference to the singleton — no additional notification calls are required.

The :class:`GameState` class is deliberately **not** frozen or reactive.
Callers mutate attributes in place::

    game_state.game_phase = GamePhase.PLAYING
    game_state.active_color = chess.BLACK

UI re-rendering is a separate concern handled by the signal bus
(:mod:`utils.signals`).
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Tuple

import chess


class GameAgainst(IntEnum):
    """Identity of the opponent in the current or upcoming game."""

    COMPUTER = 1
    LOCAL = 2
    ONLINE = 3


class GamePhase(Enum):
    """Lifecycle stage of the current chess game session."""

    NOT_STARTED = "not_started"
    PLAYING = "playing"
    ENDED = "ended"


class GameState:
    """Mutable holder for cross-cutting game session variables.

    Every public attribute can be written by any module.  Consumers read
    the singleton imported from this module and observe mutations made by
    other parts of the app without any extra wiring.
    """

    __slots__ = (
        "game_against",
        "game_phase",
        "active_color",
        "time_control",
        "game_over",
    )

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Restore all fields to their default values (before a new game)."""

        self.game_against: GameAgainst = GameAgainst.LOCAL
        self.game_phase: GamePhase = GamePhase.NOT_STARTED
        self.active_color: chess.Color = chess.WHITE
        self.time_control: Tuple[int, int] = (3, 2)
        self.game_over: bool = False


#: Singleton — single shared instance. Import this from any module that needs
#: read/write access to game session state.
#:
#: Usage::
#:
#:     from utils.game_state import game_state
#:     game_state.game_phase = GamePhase.PLAYING
game_state = GameState()
