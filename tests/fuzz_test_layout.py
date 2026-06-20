"""State-machine fuzz tests for responsive layout — resize sequences."""

from hypothesis import given
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition

from ui.layout import resolve_app_layout


class LayoutFuzz(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.width = 800.0
        self.height = 600.0
        self.layout = resolve_app_layout(self.width, self.height)

    @rule(w=..., h=...)
    def resize(self, w: float, h: float):
        self.width = max(200.0, w)
        self.height = max(200.0, h)
        self.layout = resolve_app_layout(self.width, self.height)

    @invariant()
    def board_side_multiple_of_8(self):
        assert self.layout.board_side % 8 == 0

    @invariant()
    def board_square_size_within_bounds(self):
        assert 30 <= self.layout.board_square_size <= 80

    @invariant()
    def timer_font_size_min_24(self):
        assert self.layout.timer_font_size >= 24

    @invariant()
    def breakpoint_is_valid(self):
        assert self.layout.breakpoint in ("mobile", "tablet", "desktop")

    @invariant()
    def board_side_equals_square_size_times_8(self):
        assert self.layout.board_side == self.layout.board_square_size * 8


TestLayoutFuzz = LayoutFuzz.TestCase
