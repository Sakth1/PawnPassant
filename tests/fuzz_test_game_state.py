"""State-machine fuzz tests for GameState — random mutation sequences."""

from hypothesis import given
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

import chess

from utils.game_state import GameAgainst, GamePhase, GameState


class GameStateFuzz(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.state = GameState()

    @rule(ga=...)
    def set_game_against(self, ga: GameAgainst):
        self.state.game_against = ga

    @rule(gp=...)
    def set_game_phase(self, gp: GamePhase):
        self.state.game_phase = gp

    @rule(color=...)
    def set_active_color(self, color):
        self.state.active_color = color

    @rule(tc=...)
    def set_time_control(self, tc):
        self.state.time_control = tc

    @rule(game_over=...)
    def set_game_over(self, game_over: bool):
        self.state.game_over = game_over

    @rule()
    def reset_state(self):
        self.state.reset()

    @invariant()
    def game_against_is_enum(self):
        assert isinstance(self.state.game_against, GameAgainst)

    @invariant()
    def game_phase_is_enum(self):
        assert isinstance(self.state.game_phase, GamePhase)

    @invariant()
    def active_color_is_bool(self):
        assert isinstance(self.state.active_color, bool)

    @invariant()
    def time_control_is_2_tuple(self):
        assert isinstance(self.state.time_control, tuple)
        assert len(self.state.time_control) == 2

    @invariant()
    def game_over_is_bool(self):
        assert isinstance(self.state.game_over, bool)


TestGameStateFuzz = GameStateFuzz.TestCase
