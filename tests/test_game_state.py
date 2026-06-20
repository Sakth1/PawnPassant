"""Unit tests for utils.game_state — GameState, GamePhase, GameAgainst."""

import unittest
import chess

from utils.game_state import GameAgainst, GamePhase, GameState, game_state


class TestGameAgainst(unittest.TestCase):
    def test_computer_is_1(self):
        self.assertEqual(GameAgainst.COMPUTER.value, 1)

    def test_local_is_2(self):
        self.assertEqual(GameAgainst.LOCAL.value, 2)

    def test_online_is_3(self):
        self.assertEqual(GameAgainst.ONLINE.value, 3)

    def test_int_enum_comparison(self):
        self.assertEqual(GameAgainst.COMPUTER, 1)
        self.assertEqual(GameAgainst.LOCAL, 2)
        self.assertEqual(GameAgainst.ONLINE, 3)


class TestGamePhase(unittest.TestCase):
    def test_not_started_value(self):
        self.assertEqual(GamePhase.NOT_STARTED.value, "not_started")

    def test_playing_value(self):
        self.assertEqual(GamePhase.PLAYING.value, "playing")

    def test_ended_value(self):
        self.assertEqual(GamePhase.ENDED.value, "ended")

    def test_ordering(self):
        phases = list(GamePhase)
        self.assertEqual(
            phases, [GamePhase.NOT_STARTED, GamePhase.PLAYING, GamePhase.ENDED]
        )


class TestGameState(unittest.TestCase):
    def setUp(self):
        self.state = GameState()

    def test_default_game_against(self):
        self.assertEqual(self.state.game_against, GameAgainst.LOCAL)

    def test_default_game_phase(self):
        self.assertEqual(self.state.game_phase, GamePhase.NOT_STARTED)

    def test_default_active_color(self):
        self.assertTrue(self.state.active_color)

    def test_default_time_control(self):
        self.assertEqual(self.state.time_control, (3, 2))

    def test_default_game_over(self):
        self.assertFalse(self.state.game_over)

    def test_mutate_game_against(self):
        self.state.game_against = GameAgainst.COMPUTER
        self.assertEqual(self.state.game_against, GameAgainst.COMPUTER)

    def test_mutate_game_phase(self):
        self.state.game_phase = GamePhase.PLAYING
        self.assertEqual(self.state.game_phase, GamePhase.PLAYING)

    def test_mutate_active_color(self):
        self.state.active_color = chess.BLACK
        self.assertFalse(self.state.active_color)

    def test_mutate_time_control(self):
        self.state.time_control = (10, 0)
        self.assertEqual(self.state.time_control, (10, 0))

    def test_mutate_game_over(self):
        self.state.game_over = True
        self.assertTrue(self.state.game_over)

    def test_reset_restores_defaults(self):
        self.state.game_against = GameAgainst.COMPUTER
        self.state.game_phase = GamePhase.PLAYING
        self.state.active_color = chess.BLACK
        self.state.time_control = (10, 0)
        self.state.game_over = True

        self.state.reset()

        self.assertEqual(self.state.game_against, GameAgainst.LOCAL)
        self.assertEqual(self.state.game_phase, GamePhase.NOT_STARTED)
        self.assertTrue(self.state.active_color)
        self.assertEqual(self.state.time_control, (3, 2))
        self.assertFalse(self.state.game_over)


class TestGameStateSingleton(unittest.TestCase):
    def test_singleton_is_same_object(self):
        from utils.game_state import game_state as gs1
        from utils.game_state import game_state as gs2

        self.assertIs(gs1, gs2)

    def test_singleton_mutation_visible_across_imports(self):
        original = game_state.game_phase
        game_state.game_phase = GamePhase.PLAYING
        from utils.game_state import game_state as gs2

        self.assertEqual(gs2.game_phase, GamePhase.PLAYING)
        game_state.game_phase = original


if __name__ == "__main__":
    unittest.main()
