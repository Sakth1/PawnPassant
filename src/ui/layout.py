"""Responsive layout helpers shared by the Pawn Passant UI."""

from __future__ import annotations

from dataclasses import dataclass

MOBILE_BREAKPOINT = 700
TABLET_BREAKPOINT = 1100
MIN_SQUARE_SIZE = 34
MAX_SQUARE_SIZE = 96


@dataclass(frozen=True)
class AppLayout:
    """Resolved responsive metrics for the current page size."""

    breakpoint: str
    width: float
    height: float
    padding: int
    gap: int
    compact: bool
    stacked: bool
    board_square_size: int
    board_side: int
    piece_col: int
    board_col: int
    clock_col: int
    piece_panel_width: int
    clock_width: int
    timer_font_size: int
    timer_ms_size: int
    timer_padding: int
    timer_radius: int
    divider_extent: int
    dev_control_width: int

    @property
    def spacing_scale(self) -> float:
        return self.board_square_size / 60


def resolve_app_layout(page_width: float, page_height: float) -> AppLayout:
    """Return a responsive layout tuned to the available viewport."""

    width = max(float(page_width or 0), 320.0)
    height = max(float(page_height or 0), 480.0)

    if width < MOBILE_BREAKPOINT:
        breakpoint = "mobile"
        padding = 12
        gap = 12
        stacked = True
        compact = True
    elif width < TABLET_BREAKPOINT:
        breakpoint = "tablet"
        padding = 18
        gap = 16
        stacked = False
        compact = False
    else:
        breakpoint = "desktop"
        padding = 24
        gap = 20
        stacked = False
        compact = False

    available_width = max(width - (padding * 2), 220.0)
    available_height = max(height - (padding * 2), 280.0)

    if stacked:
        board_space_width = available_width
        board_space_height = available_height * 0.62
        piece_panel_width = int(min(max(available_width, 220.0), 420.0))
        clock_width = int(min(max(available_width, 220.0), 420.0))
    else:
        piece_panel_width = int(min(max(available_width * 0.24, 180.0), 300.0))
        clock_width = int(min(max(available_width * 0.16, 140.0), 220.0))
        board_space_width = max(
            220.0, available_width - piece_panel_width - clock_width - (gap * 2)
        )
        board_space_height = available_height

    board_square_size = int(
        max(
            MIN_SQUARE_SIZE,
            min(
                MAX_SQUARE_SIZE,
                board_space_width / 8,
                board_space_height / 9,
            ),
        )
    )
    board_side = board_square_size * 8

    timer_font_size = max(24, int(board_square_size * 0.5))
    timer_ms_size = max(12, int(timer_font_size * 0.48))
    timer_padding = max(8, int(board_square_size * 0.22))
    timer_radius = max(12, int(board_square_size * 0.26))
    divider_extent = max(56, int(clock_width * 0.58))
    dev_control_width = int(min(max(available_width, 220.0), 360.0))

    return AppLayout(
        breakpoint=breakpoint,
        width=width,
        height=height,
        padding=padding,
        gap=gap,
        compact=compact,
        stacked=stacked,
        board_square_size=board_square_size,
        board_side=board_side,
        piece_col=12 if stacked else 3,
        board_col=12 if stacked else 7,
        clock_col=12 if stacked else 2,
        piece_panel_width=piece_panel_width,
        clock_width=clock_width,
        timer_font_size=timer_font_size,
        timer_ms_size=timer_ms_size,
        timer_padding=timer_padding,
        timer_radius=timer_radius,
        divider_extent=divider_extent,
        dev_control_width=dev_control_width,
    )
