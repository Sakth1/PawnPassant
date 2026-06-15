"""Hypothesis strategies for property-based tests throughout the codebase."""

from hypothesis import strategies as st

from utils.models import AppSettings, TimeControl


time_control_presets = st.sampled_from(
    [v for v in vars(TimeControl).values() if isinstance(v, tuple) and len(v) == 2]
)


non_negative_ints = st.integers(min_value=0, max_value=2**31 - 1)


move_animation_options = st.sampled_from(
    ["off", "fast", "normal", "slow"]
)


promotion_options = st.sampled_from(
    ["ask", "queen", "rook", "bishop", "knight"]
)


app_settings = st.builds(
    AppSettings,
    show_legal_moves=st.booleans(),
    show_tap_feedback=st.booleans(),
    auto_flip_board=st.booleans(),
    show_coordinates=st.booleans(),
    move_animation=move_animation_options,
    confirm_moves=st.booleans(),
    promotion_default=promotion_options,
    critical_time_seconds=st.integers(min_value=1, max_value=120),
    show_milliseconds_in_critical=st.booleans(),
    confirm_resign=st.booleans(),
    confirm_draw=st.booleans(),
)


page_dimensions = st.floats(
    min_value=200.0, max_value=2000.0, allow_nan=False, allow_infinity=False
)
