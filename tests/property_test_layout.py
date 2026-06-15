"""Property-based tests for ui.layout — layout invariants across page sizes."""

from hypothesis import given, strategies as st

from ui.layout import resolve_app_layout
from tests.property_strategies import page_dimensions


class TestLayoutInvariants:
    @given(width=page_dimensions, height=page_dimensions)
    def test_board_side_always_multiple_of_8(self, width, height):
        layout = resolve_app_layout(width, height)
        assert layout.board_side % 8 == 0

    @given(width=page_dimensions, height=page_dimensions)
    def test_square_size_within_bounds(self, width, height):
        layout = resolve_app_layout(width, height)
        assert 30 <= layout.board_square_size <= 80

    @given(width=page_dimensions, height=page_dimensions)
    def test_piece_clock_cols_sum_less_than_13(self, width, height):
        layout = resolve_app_layout(width, height)
        assert layout.piece_col + layout.board_col + layout.clock_col <= 22

    @given(width=page_dimensions, height=page_dimensions)
    def test_timer_font_size_at_least_24(self, width, height):
        layout = resolve_app_layout(width, height)
        assert layout.timer_font_size >= 24

    @given(width=page_dimensions, height=page_dimensions)
    def test_spacing_scale_non_negative(self, width, height):
        layout = resolve_app_layout(width, height)
        assert layout.spacing_scale >= 0

    @given(width=page_dimensions, height=page_dimensions)
    def test_breakpoint_one_of_three(self, width, height):
        layout = resolve_app_layout(width, height)
        assert layout.breakpoint in ("mobile", "tablet", "desktop")
