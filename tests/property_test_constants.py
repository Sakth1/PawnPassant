"""Property-based tests for utils.constants — invariants across all definitions."""

from hypothesis import given

from utils.constants import (
    BOARD_SIZE,
    MAX_CAPTURES,
    MOVE_ANIMATION_OPTIONS,
    PROMOTION_DEFAULT_OPTIONS,
    SYMBOL_MAP,
)
from tests.property_strategies import move_animation_options, promotion_options


class TestConstantsInvariants:
    def test_board_size_8(self):
        assert BOARD_SIZE == 8

    def test_max_captures_16(self):
        assert MAX_CAPTURES == 16

    def test_symbol_map_covers_all_pieces(self):
        assert len(SYMBOL_MAP) == 12

    def test_promotion_options_5(self):
        assert len(PROMOTION_DEFAULT_OPTIONS) == 5

    @given(move_animation_options)
    def test_any_animation_option_in_definitions(self, option):
        assert option in ("off", "fast", "normal", "slow")

    @given(promotion_options)
    def test_any_promotion_option_in_defaults(self, option):
        assert option in PROMOTION_DEFAULT_OPTIONS
