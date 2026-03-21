"""Board-square control with piece rendering and move-highlight support."""

import traceback
from typing import Optional

import flet as ft

from Ui.chess_piece import ChessPiece


class Square(ft.Container):
    """Represents one clickable chessboard square in the Flet UI."""

    LONG_PRESS_DURATION_SECONDS = 0.25

    DRAG_GROUP = "chess-piece"

    def __init__(
        self,
        file,
        rank,
        coordinate,
        color,
        on_square_click=None,
        on_square_drop=None,
        size=60,
    ):
        super().__init__(expand=True)
        self.file = file
        self.rank = rank
        self.coordinate = coordinate
        self.color = color
        self.on_square_click = on_square_click
        self.on_square_drop = on_square_drop

        dot_size = size * 0.3
        ring_size = size * 0.8

        self.square_dot = ft.Container(
            width=dot_size,
            height=dot_size,
            border_radius=dot_size / 2,
            bgcolor=ft.Colors.BLACK_45,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.BLACK_45,
                offset=ft.Offset(0, 0),
            ),
        )

        self.square_ring = ft.Container(
            width=ring_size,
            height=ring_size,
            border_radius=ring_size / 2,
            border=ft.Border.all(3, ft.Colors.BLACK_54),
            bgcolor=ft.Colors.TRANSPARENT,
        )

        self.base_bgcolor = (
            ft.Colors.GREEN_100 if self.color == "w" else ft.Colors.GREEN_900
        )
        self.bgcolor = self.base_bgcolor
        self.width = size
        self.height = size
        self.piece_control: Optional[ft.Control] = None
        self.piece_container: Optional[ChessPiece] = None
        self.has_piece = False
        self.highlighted_metadata: dict[str, bool | str | None] = {
            "highlighted": False,
            "parent_piece_square": None,
        }
        self.stack = ft.Stack(controls=[], expand=True, alignment=ft.Alignment.CENTER)
        self.interactive_surface = ft.Container(
            content=self.stack,
            on_click=self._handle_click,
        )
        self.drag_target = ft.DragTarget(
            group=self.DRAG_GROUP,
            on_accept=self._handle_drag_accept,
            content=self.interactive_surface,
        )
        self.content = self.drag_target
        self.margin = 0

    def _handle_click(self, _event=None):
        """Forward click events to the board controller with square context."""

        print("click at", self.coordinate)
        if self.on_square_click is not None:
            self.on_square_click(self, self.coordinate)

    def _handle_drag_accept(self, event: ft.DragTargetEvent):
        """Forward accepted drops to the board controller."""

        if self.on_square_drop is None or event.src is None:
            return

        from_coordinate = event.src.data
        if isinstance(from_coordinate, str):
            self.on_square_drop(from_coordinate, self.coordinate)

    def set_highlight(self, highlighted: bool, parent_piece_square=None):
        """Toggle the move highlight marker shown on the square."""

        self.highlighted_metadata["highlighted"] = highlighted
        self.highlighted_metadata["parent_piece_square"] = parent_piece_square
        self._rebuild_stack()
        self.update()

    def update_content(self, piece: Optional[ChessPiece] = None):
        """Replace the visible piece control and refresh the square overlay."""

        try:
            if piece is None:
                content = None
                self.has_piece = False
                self.piece_container = None
            elif isinstance(piece, ChessPiece):
                content = self._build_draggable_piece(piece)
                self.piece_container = piece
                self.has_piece = True
            else:
                content = ft.Text(
                    "ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED
                )
                self.has_piece = False
                self.piece_container = None
        except Exception:
            traceback.print_exc()
            content = ft.Text("ERROR", align=ft.Alignment.CENTER, color=ft.Colors.RED)
            self.has_piece = False
            self.piece_container = None

        self.piece_control = content
        self._rebuild_stack()

    def _build_draggable_piece(self, piece: ChessPiece) -> ft.Draggable:
        """Render the piece as a native drag source for smoother pointer tracking."""

        return ft.Draggable(
            group=self.DRAG_GROUP,
            data=self.coordinate,
            max_simultaneous_drags=1,
            content=self._build_piece_shell(piece.to_control()),
            content_when_dragging=ft.Container(
                width=self.width,
                height=self.height,
                opacity=0.18,
            ),
            content_feedback=ft.Container(
                width=self.width,
                height=self.height,
                alignment=ft.Alignment.CENTER,
                scale=1.08,
                opacity=0.96,
                shadow=ft.BoxShadow(
                    blur_radius=12,
                    color=ft.Colors.BLACK_38,
                    offset=ft.Offset(0, 4),
                ),
                content=ChessPiece(piece.piece).to_control(),
            ),
        )

    def _build_piece_shell(self, control: ft.Control) -> ft.Container:
        return ft.Container(
            width=self.width,
            height=self.height,
            alignment=ft.Alignment.CENTER,
            content=control,
        )

    def _rebuild_stack(self):
        """Recompose the square so highlights sit above the base board color."""

        controls: list[ft.Control] = []
        if self.piece_control is not None:
            controls.append(self.piece_control)

        if self.highlighted_metadata.get("highlighted"):
            if self.piece_control is None:
                controls.append(self.square_dot)
            else:
                controls.append(self.square_ring)

        self.stack.controls = controls

    def _animate_piece_bob_when_clicked(self):
        """Animate the piece when the square is clicked. only to be used on click events."""

        if not self.has_piece or self.piece_container is None:
            return

        self.piece_container._animate_click()

    @staticmethod
    def _safe_update(control: ft.Control):
        try:
            control.update()
        except RuntimeError:
            pass
