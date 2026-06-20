"""Property-based tests for utils.game_state — GameState mutation invariants."""

from hypothesis import given, strategies as st

import chess

from utils.game_state import GameAgainst, GamePhase, GameState

game_against_strategy = st.sampled_from(list(GameAgainst))
game_phase_strategy = st.sampled_from(list(GamePhase))
color_strategy = st.sampled_from([chess.WHITE, chess.BLACK])
time_control_strategy = st.tuples(
    st.integers(min_value=0, max_value=180),
    st.integers(min_value=0, max_value=60),
)


class TestGameStateMutation:
    @given(game_against_strategy)
    def test_set_game_against_preserves_type(self, ga):
        state = GameState()
        state.game_against = ga
        assert isinstance(state.game_against, GameAgainst)

    @given(game_phase_strategy)
    def test_set_game_phase_preserves_type(self, gp):
        state = GameState()
        state.game_phase = gp
        assert isinstance(state.game_phase, GamePhase)

    @given(color_strategy)
    def test_set_active_color(self, color):
        state = GameState()
        state.active_color = color
        assert state.active_color == color

    @given(time_control_strategy)
    def test_set_time_control(self, tc):
        state = GameState()
        state.time_control = tc
        assert state.time_control == tc
        assert len(state.time_control) == 2

    def test_reset_clears_all_fields(self):
        state = GameState()
        state.game_against = GameAgainst.COMPUTER
        state.game_phase = GamePhase.PLAYING
        state.active_color = chess.BLACK
        state.time_control = (10, 5)
        state.game_over = True
        state.reset()
        assert state.game_against == GameAgainst.LOCAL
        assert state.game_phase == GamePhase.NOT_STARTED
        assert state.active_color == chess.WHITE
        assert state.time_control == (3, 2)
        assert not state.game_over
