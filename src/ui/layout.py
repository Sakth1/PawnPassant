"""Responsive layout helpers shared by the Pawn Passant UI.

The app has several independent Flet controls that must agree on board size,
panel widths, clock typography, and spacing. This module resolves those values
once from the page dimensions so controls can resize consistently without each
component inventing its own breakpoints.
"""

from __future__ import annotations
import logging

from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: Maximum viewport width, in pixels, treated as a stacked mobile layout.
MOBILE_BREAKPOINT = 700

#: Maximum viewport width, in pixels, treated as a tablet split layout.
TABLET_BREAKPOINT = 1100

#: Smallest legal chess square size so pieces and labels remain usable.
MIN_SQUARE_SIZE = 34

#: Largest chess square size so desktop layouts do not become oversized.
MAX_SQUARE_SIZE = 96


@dataclass(frozen=True)
class AppLayout:
    """Resolved responsive metrics for the current page size.

    The dataclass is frozen because it represents one layout calculation. When
    the page changes size, callers ask :func:`resolve_app_layout` for a new
    instance and pass it to each control.
    """

    #: Breakpoint label used by UI controls for coarse layout decisions.
    breakpoint: str
    #: Effective page width after fallback minimums are applied.
    width: float
    #: Effective page height after fallback minimums are applied.
    height: float
    #: Outer page padding used around the main content.
    padding: int
    #: Standard gap between major UI regions.
    gap: int
    #: Whether controls should use smaller typography and denser spacing.
    compact: bool
    #: Whether board, clock, and captured pieces stack vertically.
    stacked: bool
    #: Pixel size of one chessboard square.
    board_square_size: int
    #: Pixel size of the full 8x8 board.
    board_side: int
    #: ResponsiveRow column span allocated to the captured-pieces panel.
    piece_col: int
    #: ResponsiveRow column span allocated to the chessboard.
    board_col: int
    #: ResponsiveRow column span allocated to the clock panel.
    clock_col: int
    #: Pixel width of the captured-pieces panel.
    piece_panel_width: int
    #: Pixel width of the clock panel.
    clock_width: int
    #: Font size for the main minute/second timer text.
    timer_font_size: int
    #: Font size for critical-time millisecond text.
    timer_ms_size: int
    #: Padding inside timer containers.
    timer_padding: int
    #: Border radius used by timer surfaces.
    timer_radius: int
    #: Width of the visual divider inside the clock panel.
    divider_extent: int
    #: Width of the developer-only FEN selector dropdown.
    dev_control_width: int

    @property
    def spacing_scale(self) -> float:
        """Return a scale factor relative to the original 60px square design."""

        return self.board_square_size / 60


def resolve_app_layout(page_width: float, page_height: float) -> AppLayout:
    """Return a responsive layout tuned to the available viewport.

    Args:
        page_width: Current page width reported by Flet.
        page_height: Current page height reported by Flet.

    Returns:
        A complete immutable layout snapshot for board, clock, captured pieces,
        settings, home, and developer controls.
    """

    width = max(float(page_width or 0), 320.0)
    height = max(float(page_height or 0), 480.0)
    logger.debug("Resolving app layout: width=%s, height=%s", width, height)

    # Mobile gets a stacked layout because the board needs most of the width.
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
        # Leave vertical room for controls below the board while keeping the
        # board as large as possible on narrow screens.
        board_space_width = available_width
        board_space_height = available_height * 0.62
        piece_panel_width = int(min(max(available_width, 220.0), 420.0))
        clock_width = int(min(max(available_width, 220.0), 420.0))
    else:
        # Desktop/tablet split the row into captured pieces, board, and clock.
        piece_panel_width = int(min(max(available_width * 0.24, 180.0), 300.0))
        clock_width = int(min(max(available_width * 0.16, 140.0), 220.0))
        board_space_width = max(
            220.0, available_width - piece_panel_width - clock_width - (gap * 2)
        )
        board_space_height = available_height

    # The board needs nine vertical square units because the promotion picker
    # reserves a one-square lane above the board.
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
