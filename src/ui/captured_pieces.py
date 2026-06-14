"""Captured-pieces panel and drag/drop reordering support."""

import logging
import random

import flet as ft
from chess import WHITE, BLACK

from ui.layout import AppLayout, resolve_app_layout
from ui.square import InvisibleSquare
from utils.dialogs import safe_update
from utils.events import PieceCapturedEvent
from utils.models import ActiveColor
from utils.signals import bus

logger = logging.getLogger(__name__)


class CaputredPieces(ft.Container):
    """Display captured pieces in separate white/black grids.

    The class name is intentionally preserved for compatibility with existing
    imports. Captures arrive through :class:`utils.events.PieceCapturedEvent`,
    and pieces can be rearranged within their color grid by drag/drop.
    """

    def __init__(self):
        super().__init__()
        #: Last applied responsive layout metrics.
        self.layout = resolve_app_layout(960, 800)
        self.bgcolor = "#1F1F1F"
        self.border_radius = 16
        self.padding = 12
        self.alignment = ft.Alignment.CENTER

        #: Slots used to display captured black pieces.
        self.black_squares: list[InvisibleSquare] = self._create_invisible_squares(
            "black", BLACK
        )
        #: Slots used to display captured white pieces.
        self.white_squares: list[InvisibleSquare] = self._create_invisible_squares(
            "white", WHITE
        )
        #: Empty white-grid slot indexes available for future captures.
        self.available_white_squares: list[int] = list(range(len(self.white_squares)))
        #: Empty black-grid slot indexes available for future captures.
        self.available_black_squares: list[int] = list(range(len(self.black_squares)))
        self.black_grid: ft.GridView = self._build_square_grid(self.black_squares)
        self.white_grid: ft.GridView = self._build_square_grid(self.white_squares)
        self.divider = ft.Container(
            height=1,
            bgcolor=ft.Colors.WHITE_24,
        )
        self.content = ft.Column(
            controls=[
                self.black_grid,
                self.divider,
                self.white_grid,
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )
        bus.connect(
            PieceCapturedEvent, lambda event: self._handle_piece_captured(event)
        )
        self.apply_layout(self.layout)

    def _invisible_square(self, prefix, position, piece_colors) -> InvisibleSquare:
        """Create one captured-piece slot for a color-specific drag group."""

        return InvisibleSquare(
            coordinate=str(position),
            color=piece_colors,
            drag_drop_group=(
                "captured-chess-piece-white"
                if piece_colors
                else "captured-chess-piece-black"
            ),
            on_square_drop=self._handle_square_drop,
            on_piece_drag_start=self._handle_piece_drag_start,
            on_piece_drag_complete=self._handle_piece_drag_complete,
            size=60,
        )

    def _create_invisible_squares(
        self, prefix: str, piece_colors
    ) -> list[InvisibleSquare]:
        """Create the initial 16 captured-piece slots for one side."""

        squares: list[InvisibleSquare] = []
        for i in range(16):
            squares.append(self._invisible_square(prefix, i, piece_colors))
        return squares

    def _build_square_grid(self, squares: list[InvisibleSquare]) -> ft.GridView:
        """Build the fixed 4-column grid that holds captured-piece slots."""

        return ft.GridView(
            runs_count=4,
            controls=squares,
            expand=False,
            spacing=4,
            run_spacing=4,
            padding=4,
        )

    def apply_layout(self, layout: AppLayout):
        """Resize captured-piece grids to match the main board layout."""

        self.layout = layout
        self.width = layout.piece_panel_width
        self.padding = max(8, int(layout.gap * 0.75))
        self.border_radius = max(12, int(layout.timer_radius * 0.8))

        # Use same square size as main board
        capture_square_size = layout.board_square_size * 0.97
        for square in self.black_squares + self.white_squares:
            square.apply_size(capture_square_size)

        # Use 4x4 grid layout for captured pieces
        grid_spacing = max(4, int(layout.gap * 0.35))
        runs_count = 4

        for grid in (self.black_grid, self.white_grid):
            grid.runs_count = runs_count
            grid.spacing = grid_spacing
            grid.run_spacing = grid_spacing

        self.divider.width = max(80, int(layout.piece_panel_width * 0.72))
        self.content.spacing = max(10, int(layout.gap * 0.65))
        safe_update(self)

    def _get_random_available_position(self, is_white_capture: ActiveColor):
        """Pick an empty slot for a newly captured piece.

        Random placement gives the captured-piece panel a loose tabletop feel
        while the available-slot lists still prevent accidental overwrite.
        """

        available_squares: list[int] = (
            self.available_white_squares
            if is_white_capture
            else self.available_black_squares
        )
        if available_squares != []:
            return random.choice(available_squares)
        else:
            if is_white_capture:
                return len(self.white_squares) + 1
            else:
                return len(self.black_squares) + 1

    def _handle_piece_captured(self, event: PieceCapturedEvent):
        """Place a captured piece into the capturing side's panel."""

        is_white_capture: ActiveColor = event.color
        random_available_pos: int = self._get_random_available_position(
            is_white_capture
        )
        logger.info(
            "Captured piece received color=%s slot=%s",
            "white" if is_white_capture else "black",
            random_available_pos,
        )
        if is_white_capture:
            try:
                self.white_squares[random_available_pos].update_content(event.piece)
                self.available_white_squares.remove(random_available_pos)
            except IndexError:
                self.white_squares.append(
                    self._invisible_square("white", random_available_pos, WHITE)
                )
                self.white_squares[-1].update_content(event.piece)
        else:
            try:
                self.black_squares[random_available_pos].update_content(event.piece)
                self.available_black_squares.remove(random_available_pos)
            except IndexError:
                self.black_squares.append(
                    self._invisible_square("black", random_available_pos, BLACK)
                )
                self.black_squares[-1].update_content(event.piece)

        safe_update(self)

    def _handle_piece_drag_start(self, _from_cords: str):
        """Reserved hook for future captured-piece drag feedback."""

        pass

    def _handle_piece_drag_complete(self, _from_cords: str, piece_color):
        """Reserved hook for future captured-piece drag completion feedback."""

        pass

    def _handle_square_drop(
        self,
        from_cords: str,
        to_cords: str,
        piece_color,
        source_color: int | None = None,
    ):
        """Move a captured piece between empty slots in its own color grid."""

        try:
            if ":" in str(from_cords):
                # Drag data includes color because white and black grids can use
                # the same numeric slot coordinate.
                parsed_source_color, parsed_from_cords = (
                    InvisibleSquare.parse_drag_data(str(from_cords))
                )
                from_cords = parsed_from_cords
                if source_color is None:
                    source_color = parsed_source_color

            if from_cords == to_cords:
                return
            moved = self.move_piece(
                from_cords=str(from_cords),
                to_cords=str(to_cords),
                source_color=source_color,
            )
            if not moved:
                return
            from_cords = int(from_cords)
            to_cords = int(to_cords)
            if piece_color:
                self.available_white_squares.append(from_cords)
                self.available_white_squares.remove(to_cords)
            else:
                self.available_black_squares.append(from_cords)
                self.available_black_squares.remove(to_cords)
        except Exception:
            logger.exception(
                "Failed to move captured piece from=%s to=%s source_color=%s",
                from_cords,
                to_cords,
                source_color,
            )

    def move_piece(
        self, from_cords: str, to_cords: str, source_color: int | None = None
    ) -> bool:
        """Move a captured piece control from one slot to another.

        Returns:
            ``True`` when a piece was moved; otherwise ``False`` when the source
            is empty, the target is occupied, or the color/coordinate is invalid.
        """

        source_square = self._find_square(from_cords, color=source_color)
        target_square = self._find_square(to_cords, color=source_color)
        if source_square is None or target_square is None or target_square.has_piece:
            logger.debug(
                "Captured piece move rejected from=%s to=%s source_color=%s",
                from_cords,
                to_cords,
                source_color,
            )
            return False

        chess_piece = source_square.piece_container
        if chess_piece is None:
            logger.debug("Captured piece move rejected empty_source=%s", from_cords)
            return False
        source_square.update_content(None)
        target_square.update_content(chess_piece)
        logger.info(
            "Captured piece moved from=%s to=%s source_color=%s",
            source_square.coordinate,
            target_square.coordinate,
            source_color,
        )
        return True

    def _find_square(
        self, coordinate: str, color: int | None = None
    ) -> InvisibleSquare | None:
        """Find a captured-piece slot by coordinate and optional color group."""

        if color == WHITE:
            squares = self.white_squares
        elif color == BLACK:
            squares = self.black_squares
        else:
            squares = self.black_squares + self.white_squares

        for square in squares:
            if square.coordinate == coordinate:
                return square
        return None


