"""State-machine fuzz tests for AppSettings — random update sequences."""

from hypothesis import given
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

from utils.models import AppSettings
from tests.property_strategies import move_animation_options, promotion_options


class AppSettingsFuzz(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings()

    @rule(v=...)
    def set_show_legal_moves(self, v: bool):
        self.settings = self.settings.updated(show_legal_moves=v)

    @rule(v=...)
    def set_show_tap_feedback(self, v: bool):
        self.settings = self.settings.updated(show_tap_feedback=v)

    @rule(v=...)
    def set_auto_flip_board(self, v: bool):
        self.settings = self.settings.updated(auto_flip_board=v)

    @rule(v=...)
    def set_show_coordinates(self, v: bool):
        self.settings = self.settings.updated(show_coordinates=v)

    @rule(v=move_animation_options)
    def set_move_animation(self, v: str):
        self.settings = self.settings.updated(move_animation=v)

    @rule(v=...)
    def set_confirm_moves(self, v: bool):
        self.settings = self.settings.updated(confirm_moves=v)

    @rule(v=promotion_options)
    def set_promotion_default(self, v: str):
        self.settings = self.settings.updated(promotion_default=v)

    @rule(v=...)
    def set_critical_time(self, v: int):
        self.settings = self.settings.updated(critical_time_seconds=v)

    @rule(v=...)
    def set_show_ms_critical(self, v: bool):
        self.settings = self.settings.updated(show_milliseconds_in_critical=v)

    @rule(v=...)
    def set_confirm_resign(self, v: bool):
        self.settings = self.settings.updated(confirm_resign=v)

    @rule(v=...)
    def set_confirm_draw(self, v: bool):
        self.settings = self.settings.updated(confirm_draw=v)

    @rule()
    def reset_defaults(self):
        self.settings = AppSettings()

    @invariant()
    def show_legal_moves_is_bool(self):
        assert isinstance(self.settings.show_legal_moves, bool)

    @invariant()
    def show_tap_feedback_is_bool(self):
        assert isinstance(self.settings.show_tap_feedback, bool)

    @invariant()
    def auto_flip_board_is_bool(self):
        assert isinstance(self.settings.auto_flip_board, bool)

    @invariant()
    def show_coordinates_is_bool(self):
        assert isinstance(self.settings.show_coordinates, bool)

    @invariant()
    def move_animation_is_valid(self):
        assert self.settings.move_animation in ("off", "fast", "normal", "slow")

    @invariant()
    def promotion_default_is_valid(self):
        assert self.settings.promotion_default in ("ask", "queen", "rook", "bishop", "knight")

    @invariant()
    def critical_time_is_int(self):
        assert isinstance(self.settings.critical_time_seconds, int)

    @invariant()
    def roundtrip_stable(self):
        d = self.settings.to_dict()
        restored = AppSettings.from_dict(d)
        assert self.settings == restored


TestAppSettingsFuzz = AppSettingsFuzz.TestCase
