"""Chessboard UI control that coordinates game state, rendering, and interactions."""

import asyncio
from typing import Optional

import flet as ft
from chess import (BISHOP, FILE_NAMES, KNIGHT, QUEEN, RANK_NAMES, ROOK, Color,
                   Move, Piece, parse_square, square, square_name)

from Constants import CASTLING_ROOK_END_SQUARE, CASTLING_ROOK_START_SQUARE
from Core.Engine import Game
from Core.MoveType import MoveType
from Ui.chess_piece import ChessPiece
from Ui.square import Square


class ChessBoard(ft.Container):
    """Interactive chessboard widget with move highlighting and promotion UI."""

    PROMOTION_OPTIONS = [QUEEN, ROOK, BISHOP, KNIGHT]
    MOVE_ANIMATION_DURATION_MS = 120

    TEST_POSITIONS: dict[str, Optional[str]] = {
        "Start Position": None,
        "Castle Test": "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "En Passant Test": "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "Promotion Test": "4k3/4P3/8/8/8/8/3p4/4K3 w - - 0 1",
        "Mate In One": "6k1/5ppp/8/8/8/8/6PP/5RK1 w - - 0 1",
    }

    def __init__(self):
        super().__init__()
        self.game = Game()
        self.highlighted_squares: set[str] = set()
        self.is_flipped = False
        self.square_size = 60
        self.board_side_px = self.square_size * 8
        self.promotion_lane_px = self.square_size
        self.pending_promotion_move: Optional[Move] = None
        self.pending_promotion_color_is_white: Optional[Color] = None
        self.selected_square: Optional[str] = None
        self.active_tap_feedback_square: Optional[str] = None

        self.board_frame = ft.GridView(
            runs_count=8,
            controls=self._create_squares(),
            expand=False,
            spacing=0,
            run_spacing=0,
            padding=0,
            width=self.board_side_px,
            height=self.board_side_px,
        )

        self.margin = 0
        self.alignment = ft.Alignment.CENTER
        self.height = self.board_side_px + self.promotion_lane_px
        self.width = self.board_side_px

        self.board_layer = ft.Container(
            left=0,
            top=self.promotion_lane_px,
            width=self.board_side_px,
            height=self.board_side_px,
            content=self.board_frame,
        )
        self.promotion_overlay = ft.Container(
            visible=False,
            left=0,
            top=0,
            width=self.square_size * 4,
            height=self.square_size,
            border=ft.Border.all(2, ft.Colors.BLACK_54),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.97, ft.Colors.GREEN_50),
            shadow=ft.BoxShadow(
                blur_radius=14,
                color=ft.Colors.BLACK_38,
                offset=ft.Offset(0, 2),
            ),
            content=ft.Row(spacing=0, controls=[]),
        )
        self.move_animation_overlay = ft.Container(
            visible=False,
            left=0,
            top=0,
            width=self.square_size,
            height=self.square_size,
            animate_position=ft.Animation(
                self.MOVE_ANIMATION_DURATION_MS, curve=ft.AnimationCurve.EASE_IN_OUT
            ),
        )
        self.content = ft.Stack(
            controls=[
                self.board_layer,
                self.promotion_overlay,
                self.move_animation_overlay,
            ],
            width=self.width,
            height=self.height,
            clip_behavior=ft.ClipBehavior.NONE,
        )
        self.clip_behavior = ft.ClipBehavior.NONE
        self._setup_pieces()

    def _render_board_state(self):
        """Repaint every square from the current board position."""

        self._clear_interaction_state(clear_tap_feedback=True, refresh=False)
        for sq in self.squares:
            sq.update_content(None)
        self._setup_pieces()
        self._safe_update(self.board_frame)

    def load_position(self, fen: Optional[str] = None):
        """Load a specific FEN position or reset to the standard starting board."""

        if fen:
            self.game.set_board_fen(fen)
        else:
            self.game.reset_board()
        self._hide_promotion_overlay(refresh=False)
        self.is_flipped = False
        self.board_frame.controls = self.squares
        self._render_board_state()
        self._safe_update(self)

    def _create_squares(self) -> list[Square]:
        """Create the board squares in top-to-bottom visual order."""

        self.squares: list[Square] = []
        self.square_map: dict[str, Square] = {}
        reversed_rank = list(reversed(RANK_NAMES))

        for i in range(len(RANK_NAMES)):
            rank_idx = RANK_NAMES.index(reversed_rank[i])
            for j in range(len(FILE_NAMES)):
                file_idx = FILE_NAMES.index(FILE_NAMES[j])
                coords = f"{FILE_NAMES[file_idx]}{RANK_NAMES[rank_idx]}"
                sq = Square(
                    file=file_idx,
                    rank=rank_idx,
                    coordinate=coords,
                    color="b" if (file_idx + rank_idx) % 2 == 0 else "w",
                    on_square_click=self._handle_square_click,
                    on_square_drop=self._handle_square_drop,
                    on_piece_drag_start=self._handle_piece_drag_start,
                    on_piece_drag_complete=self._handle_piece_drag_complete,
                    size=self.square_size,
                )
                self.squares.append(sq)
                self.square_map[coords] = sq
        return self.squares

    def _setup_pieces(self):
        """Populate the square controls with the pieces from the current position."""

        for rank_idx in range(len(RANK_NAMES)):
            for file_idx in range(len(FILE_NAMES)):
                coords = f"{FILE_NAMES[file_idx]}{RANK_NAMES[rank_idx]}"
                piece = self.game.piece_at_square(square(file_idx, rank_idx))
                if piece is not None:
                    self.square_map[coords].update_content(ChessPiece(piece))

    def _flip_board(self):
        """Reverse the visible square order so the side to move faces the player."""

        self.is_flipped = not self.is_flipped
        self.board_frame.controls = (
            self.squares[::-1] if self.is_flipped else self.squares
        )
        self._safe_update(self.board_frame)

    def _clear_move_highlights(self, refresh: bool = True):
        """Remove any currently shown legal-move markers."""

        for coord in list(self.highlighted_squares):
            sq = self.square_map.get(coord)
            if sq is not None:
                sq.set_highlight(False, None, refresh=refresh)
        self.highlighted_squares.clear()

    def _clear_tap_feedback(self, refresh: bool = True):
        """Remove transient feedback from the last interacted square."""

        if self.active_tap_feedback_square is None:
            return

        previous_square = self.square_map.get(self.active_tap_feedback_square)
        self.active_tap_feedback_square = None
        if previous_square is not None:
            previous_square.set_tap_feedback(False, refresh=refresh)

    def _clear_interaction_state(
        self,
        clear_tap_feedback: bool = False,
        refresh: bool = True,
    ):
        """Reset current selection and any move hints shown on the board."""

        self.selected_square = None
        self._clear_move_highlights(refresh=refresh)
        if clear_tap_feedback:
            self._clear_tap_feedback(refresh=refresh)

    def _set_tap_feedback(self, square_cords: str, refresh: bool = True):
        """Apply fast local feedback to the tapped square before broader refreshes."""

        if self.active_tap_feedback_square == square_cords:
            return

        previous_square = None
        if self.active_tap_feedback_square is not None:
            previous_square = self.square_map.get(self.active_tap_feedback_square)
        if previous_square is not None:
            previous_square.set_tap_feedback(False, refresh=refresh)

        current_square = self.square_map.get(square_cords)
        if current_square is not None:
            current_square.set_tap_feedback(True, refresh=refresh)
            self.active_tap_feedback_square = square_cords
        else:
            self.active_tap_feedback_square = None

    def _is_selectable_square(self, square_cords: str) -> bool:
        """Return whether the square holds a piece for the side to move."""

        piece_color = self.game.color_of_piece_at_square(parse_square(square_cords))
        return piece_color is not None and piece_color == self.game.board.turn

    def _get_legal_targets(self, from_cords: str) -> list[str]:
        """Collect legal destination coordinates for a piece on the given square."""

        from_sq = parse_square(from_cords)
        return [
            square_name(move.to_square)
            for move in self.game.board.legal_moves
            if move.from_square == from_sq
        ]

    def _select_square(self, square_cords: str):
        """Select a piece square and reveal its current legal move targets."""

        self.selected_square = square_cords
        self._clear_move_highlights(refresh=True)
        for target in self._get_legal_targets(square_cords):
            sq = self.square_map.get(target)
            if sq is not None:
                sq.set_highlight(True, square_cords, refresh=True)
                self.highlighted_squares.add(target)

    def _handle_square_click(self, square_instance: Square, click_cords: str):
        """Either play a highlighted move or reveal legal targets for the clicked square."""

        if self.promotion_overlay.visible:
            return

        self._set_tap_feedback(click_cords)

        if square_instance.highlighted_metadata.get("highlighted"):
            from_cords = square_instance.highlighted_metadata.get("parent_piece_square")
            if from_cords is not None:
                self._animate_piece_and_move(
                    from_cords=from_cords, to_cords=click_cords
                )
            return

        if self.selected_square == click_cords:
            self._clear_move_highlights(refresh=True)
            self.selected_square = None
            return

        if square_instance.has_piece and self._is_selectable_square(click_cords):
            self._select_square(click_cords)
            return

        self.selected_square = None
        self._clear_move_highlights(refresh=True)

    def _handle_piece_drag_start(self, from_cords: str):
        """Show legal moves as soon as a draggable piece starts moving."""

        if self.promotion_overlay.visible or not self._is_selectable_square(from_cords):
            return

        self._set_tap_feedback(from_cords)
        self._select_square(from_cords)

    def _handle_piece_drag_complete(self, from_cords: str):
        """Clear drag-only selection state when a drag ends without a move."""

        if self.selected_square == from_cords:
            self._clear_interaction_state(clear_tap_feedback=True)

    def _handle_square_drop(self, from_cords: str, to_cords: str):
        """Handle a piece being dropped onto a square."""

        if self.promotion_overlay.visible:
            return

        self._clear_interaction_state(clear_tap_feedback=True)
        if from_cords == to_cords:
            return

        self.move_piece(from_cords=from_cords, to_cords=to_cords)

    def _is_legal_move(self, requested_move: Move) -> bool:
        """Return whether a requested move is currently legal."""

        if requested_move in self.game.board.legal_moves:
            return True

        if requested_move.promotion is None:
            for legal_move in self.game.board.legal_moves:
                if (
                    legal_move.from_square == requested_move.from_square
                    and legal_move.to_square == requested_move.to_square
                ):
                    return True

        return False

    def _en_passant_capture(self):
        """Apply the extra board cleanup required for an en passant capture."""

        self._update_last_move_on_board()
        last_move = self.game.get_last_move()
        piece_color_is_white: Optional[Color] = self.game.color_of_piece_at_square(
            last_move.to_square
        )
        if piece_color_is_white is True:
            opponent_pawn_direction = -1
        else:
            opponent_pawn_direction = 1
        squarename = square_name(last_move.to_square)
        # The captured pawn remains behind the destination square, not on it.
        squarename = squarename[0] + str(int(squarename[1]) + opponent_pawn_direction)
        self.square_map[squarename].update_content(None)

    def _update_last_move_on_board(self):
        """Move the active piece control from the source square to the destination square."""

        last_move = self.game.get_last_move()
        self.square_map[square_name(last_move.from_square)].update_content(None)
        self.square_map[square_name(last_move.to_square)].update_content(
            ChessPiece(self.game.piece_at_square(last_move.to_square))
        )

    def _get_piece_at_square(self, square: Square) -> Optional[ChessPiece]:
        """Return the UI piece object currently stored on a square."""

        return square.piece_container

    def _queen_side_castling(self):
        """Reposition the rook after a queen-side castle."""

        last_move = self.game.get_last_move()
        piece_color_is_white: Optional[Color] = self.game.color_of_piece_at_square(
            last_move.to_square
        )
        if piece_color_is_white is True:
            rook = self._get_piece_at_square(
                self.square_map.get(CASTLING_ROOK_START_SQUARE.get("QUEEN_SIDE_WHITE"))
            )
            self.square_map[
                CASTLING_ROOK_START_SQUARE.get("QUEEN_SIDE_WHITE")
            ].update_content(None)
            self.square_map[
                CASTLING_ROOK_END_SQUARE.get("QUEEN_SIDE_WHITE")
            ].update_content(rook)
        else:
            rook = self._get_piece_at_square(
                self.square_map.get(CASTLING_ROOK_START_SQUARE.get("QUEEN_SIDE_BLACK"))
            )
            self.square_map[
                CASTLING_ROOK_START_SQUARE.get("QUEEN_SIDE_BLACK")
            ].update_content(None)
            self.square_map[
                CASTLING_ROOK_END_SQUARE.get("QUEEN_SIDE_BLACK")
            ].update_content(rook)

    def _king_side_castling(self):
        """Reposition the rook after a king-side castle."""

        last_move = self.game.get_last_move()
        piece_color_is_white: Optional[Color] = self.game.color_of_piece_at_square(
            last_move.to_square
        )
        if piece_color_is_white is True:
            rook = self._get_piece_at_square(
                self.square_map.get(CASTLING_ROOK_START_SQUARE.get("KING_SIDE_WHITE"))
            )
            self.square_map[
                CASTLING_ROOK_START_SQUARE.get("KING_SIDE_WHITE")
            ].update_content(None)
            self.square_map[
                CASTLING_ROOK_END_SQUARE.get("KING_SIDE_WHITE")
            ].update_content(rook)

        else:
            rook = self._get_piece_at_square(
                self.square_map.get(CASTLING_ROOK_START_SQUARE.get("KING_SIDE_BLACK"))
            )
            self.square_map[
                CASTLING_ROOK_START_SQUARE.get("KING_SIDE_BLACK")
            ].update_content(None)
            self.square_map[
                CASTLING_ROOK_END_SQUARE.get("KING_SIDE_BLACK")
            ].update_content(rook)

    def _complete_move(self, requested_move: Move, movement_type: MoveType):
        """Commit a legal move and update the UI according to its special behavior."""

        if not self._is_legal_move(requested_move):
            return

        self._clear_interaction_state(clear_tap_feedback=True, refresh=False)
        self._hide_promotion_overlay(refresh=False)
        self.game.move(requested_move)
        match movement_type:
            case MoveType.NORMAL | MoveType.CAPTURE:
                self._update_last_move_on_board()
            case MoveType.EN_PASSANT:
                self._en_passant_capture()
            case MoveType.QUEEN_SIDE_CASTLING:
                self._queen_side_castling()
            case MoveType.KING_SIDE_CASTLING:
                self._king_side_castling()
            case MoveType.PROMOTION:
                self._update_last_move_on_board()
            case _:
                pass
        self._flip_board()

    def _show_promotion_dialog(self, move: Move):
        """Render the promotion picker near the destination square."""

        page = self._safe_page()
        if page is None:
            # Headless tests and detached controls fall back to queen promotion.
            promoted_move = Move(
                from_square=move.from_square,
                to_square=move.to_square,
                promotion=QUEEN,
            )
            self._complete_move(promoted_move, MoveType.PROMOTION)
            return

        piece_color_is_white = self.game.color_of_piece_at_square(move.from_square)
        if piece_color_is_white is None:
            promoted_move = Move(
                from_square=move.from_square,
                to_square=move.to_square,
                promotion=QUEEN,
            )
            self._complete_move(promoted_move, MoveType.PROMOTION)
            return

        self.pending_promotion_move = move
        self.pending_promotion_color_is_white = piece_color_is_white
        self.promotion_overlay.content = ft.Row(
            spacing=0,
            controls=[
                self._build_promotion_option_control(piece_type)
                for piece_type in self.PROMOTION_OPTIONS
            ],
        )

        to_cords = square_name(move.to_square)
        visual_row, visual_col = self._get_visual_row_col(to_cords)
        self.promotion_overlay.left = self._get_promotion_left(visual_col)
        self.promotion_overlay.top = self._get_promotion_top(visual_row)
        self.promotion_overlay.visible = True
        self._safe_update(self)

    def _get_visual_row_col(self, square_cords: str) -> tuple[int, int]:
        """Translate algebraic square coordinates into the current visual grid position."""

        target_square = self.square_map[square_cords]
        visual_idx = self.board_frame.controls.index(target_square)
        return visual_idx // 8, visual_idx % 8

    def _get_center_pixel_of_square(self, square_cords: str) -> tuple[int, int]:
        """Get the center pixel of a square in the current visual grid position."""

        visual_row, visual_col = self._get_visual_row_col(square_cords)
        center_x = (visual_col * self.square_size) + (self.square_size / 2)
        center_y = (
            self.promotion_lane_px
            + (visual_row * self.square_size)
            + (self.square_size / 2)
        )

        return center_x, center_y

    def _get_promotion_left(self, visual_col: int) -> int:
        """Clamp the promotion overlay horizontally so it stays inside the board."""

        unclamped_left = visual_col * self.square_size
        max_left = self.board_side_px - (4 * self.square_size)
        return min(max(unclamped_left, 0), max_left)

    def _get_promotion_top(self, visual_row: int) -> int:
        """Place the promotion overlay one square above the promoted pawn."""

        return self.promotion_lane_px + ((visual_row - 1) * self.square_size)

    def _hide_promotion_overlay(self, refresh: bool = True):
        """Dismiss the promotion picker and clear any pending promotion state."""

        self.pending_promotion_move = None
        self.pending_promotion_color_is_white = None
        self.promotion_overlay.visible = False
        self.promotion_overlay.content = ft.Row(spacing=0, controls=[])
        if refresh:
            self._safe_update(self)

    def _build_promotion_option_control(self, piece_type: int) -> ft.Control:
        """Create one clickable option inside the promotion overlay."""

        if self.pending_promotion_color_is_white is None:
            return ft.Container(width=self.square_size, height=self.square_size)

        option_piece = Piece(piece_type, self.pending_promotion_color_is_white)
        return ft.Container(
            width=self.square_size,
            height=self.square_size,
            padding=4,
            bgcolor=ft.Colors.with_opacity(0.34, ft.Colors.GREEN_200),
            border=ft.Border.all(1, ft.Colors.BLACK_38),
            content=ChessPiece(option_piece).to_control(),
            on_click=lambda _, promotion_piece=piece_type: self._handle_promotion_pick(
                promotion_piece
            ),
        )

    def _handle_promotion_pick(self, promotion_piece: int):
        """Finish a pending promotion using the chosen piece type."""

        if self.pending_promotion_move is None:
            self._hide_promotion_overlay(refresh=True)
            return

        move = self.pending_promotion_move
        promoted_move = Move(
            from_square=move.from_square,
            to_square=move.to_square,
            promotion=promotion_piece,
        )
        self._hide_promotion_overlay(refresh=False)
        self._complete_move(promoted_move, MoveType.PROMOTION)

    def _safe_page(self):
        """Return the attached page when available, otherwise `None`."""

        try:
            return self.page
        except RuntimeError:
            return None

    @staticmethod
    def _safe_update(control: ft.Control):
        """Update a control when attached to a page, ignoring detached-control errors."""

        try:
            control.update()
        except RuntimeError:
            pass

    def _animate_move(
        self,
        piece: Optional[ft.Control],
        from_cords: str,
        to_cords: str,
        requested_move: Move,
        movement_type: MoveType,
    ):
        """Animate a move from board coordinates and dispatch it through the UI flow."""
        page = self._safe_page()
        if page is None or piece is None:
            self._complete_move(requested_move, movement_type)
            return

        from_pixel = self._get_center_pixel_of_square(from_cords)
        to_pixel = self._get_center_pixel_of_square(to_cords)

        from_square = self.square_map.get(from_cords)
        if from_square is not None:
            from_square.update_content(None)
            self._safe_update(from_square)

        self.move_animation_overlay.content = piece
        self.move_animation_overlay.left = from_pixel[0] - (self.square_size / 2)
        self.move_animation_overlay.top = from_pixel[1] - (self.square_size / 2)
        self.move_animation_overlay.visible = True
        self._safe_update(self)

        async def finish_animation():
            await asyncio.sleep(0.01)
            self.move_animation_overlay.left = to_pixel[0] - (self.square_size / 2)
            self.move_animation_overlay.top = to_pixel[1] - (self.square_size / 2)
            self._safe_update(self)

            await asyncio.sleep(self.MOVE_ANIMATION_DURATION_MS / 1000)
            self.move_animation_overlay.visible = False
            self.move_animation_overlay.content = None
            self._complete_move(requested_move, movement_type)
            self._safe_update(self)

        page.run_task(finish_animation)

    def _animate_piece_and_move(self, from_cords: str, to_cords: str):
        requested_move = Move(parse_square(from_cords), parse_square(to_cords))
        self._clear_interaction_state(clear_tap_feedback=True)
        if not self._is_legal_move(requested_move):
            return
        movement_type = self.game.get_move_type(requested_move)
        if movement_type == MoveType.PROMOTION:
            self.move_piece(from_cords, to_cords)
            return

        self._animate_move(
            self.square_map[from_cords].piece_control,
            from_cords,
            to_cords,
            requested_move,
            movement_type,
        )

    def move_piece(self, from_cords: str, to_cords: str):
        """Create a move from board coordinates and dispatch it through the UI flow."""

        requested_move = Move(parse_square(from_cords), parse_square(to_cords))
        self._clear_interaction_state(clear_tap_feedback=True)
        if not self._is_legal_move(requested_move):
            return
        movement_type = self.game.get_move_type(requested_move)
        if movement_type == MoveType.PROMOTION:
            self._show_promotion_dialog(requested_move)
            return

        self._complete_move(requested_move, movement_type)
