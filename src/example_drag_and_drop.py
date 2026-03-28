import flet as ft
import time
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────────
GRID_SIZE   = 8
CELL_SIZE   = 80
SPACING     = 2
THROTTLE_MS = 16
LIGHT       = "#F0D9B5"
DARK        = "#B58863"

PIECES = {
    "K": ("♔", "♚"),
    "Q": ("♕", "♛"),
    "R": ("♖", "♜"),
    "B": ("♗", "♝"),
    "N": ("♘", "♞"),
    "P": ("♙", "♟"),
}

# ── Initial board state ────────────────────────────────────────────────────────
def make_initial_board() -> dict:
    b = {}
    back = ["R", "N", "B", "Q", "K", "B", "N", "R"]
    for col, piece in enumerate(back):
        b[(0, col)] = piece.lower()
        b[(1, col)] = "p"
        b[(6, col)] = "P"
        b[(7, col)] = piece
    for row in range(2, 6):
        for col in range(8):
            b[(row, col)] = None
    return b

# ── Global state ───────────────────────────────────────────────────────────────
board: dict = make_initial_board()

_holders: dict = {}

_drag_state: dict = {
    "active":        False,
    "src":           None,
    "overlay_piece": None,
    "grid_offset_x": None,
    "grid_offset_y": None,
    "last_update":   0.0,
    "page":          None,
}

# ── Piece rendering ────────────────────────────────────────────────────────────

def piece_char(code: str) -> str:
    upper = code.upper()
    is_white = code.isupper()
    return PIECES[upper][0 if is_white else 1]

def make_piece_text(code: str, size: int = 48) -> ft.Text:
    is_white = code.isupper()
    return ft.Text(
        value=piece_char(code),
        size=size,
        color="#FFFFFF" if not is_white else "#DDDDDD",
    )

# ── CellHolder ─────────────────────────────────────────────────────────────────

class CellHolder:
    def __init__(self, row: int, col: int, overlay: ft.Stack):
        self.row     = row
        self.col     = col
        self.overlay = overlay
        self.gesture:   Optional[ft.GestureDetector] = None
        self.container: Optional[ft.Container]       = None

    @property
    def piece(self) -> Optional[str]:
        return board.get((self.row, self.col))

    def _make_piece_gesture(self, code: str) -> ft.GestureDetector:
        return ft.GestureDetector(
            content=ft.Container(
                width=CELL_SIZE,
                height=CELL_SIZE,
                content=make_piece_text(code),
                alignment=ft.Alignment.CENTER,
            ),
            on_pan_start=self._on_drag_start,
            on_pan_update=self._on_drag_update,
            on_pan_end=self._on_drag_end,
        )

    def build(self) -> ft.Container:
        bg = LIGHT if (self.row + self.col) % 2 == 0 else DARK
        self.gesture = self._make_piece_gesture(self.piece) if self.piece else None

        self.container = ft.Container(
            content=self.gesture,
            width=CELL_SIZE,
            height=CELL_SIZE,
            bgcolor=bg,
            alignment=ft.Alignment.CENTER,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        return self.container

    def refresh(self):
        """Re-render this cell from board state. Caller must call page.update()."""
        code = self.piece
        if code:
            self.gesture = self._make_piece_gesture(code)
            self.container.content = self.gesture
        else:
            self.gesture = None
            self.container.content = None

    def set_piece_opacity(self, opacity: float):
        """Mark piece opacity dirty. Caller must call page.update()."""
        if self.gesture and self.gesture.content:
            self.gesture.content.opacity = opacity

    # ── drag handlers ──────────────────────────────────────────────────────────

    def _on_drag_start(self, e: ft.DragStartEvent):
        if not self.piece:
            return

        if _drag_state["grid_offset_x"] is None:
            step = CELL_SIZE + SPACING
            _drag_state["grid_offset_x"] = e.global_position.x - self.col * step - CELL_SIZE / 2
            _drag_state["grid_offset_y"] = e.global_position.y - self.row * step - CELL_SIZE / 2

        _drag_state["active"]      = True
        _drag_state["src"]         = self
        _drag_state["last_update"] = 0.0

        floating = ft.Container(
            left=e.global_position.x - CELL_SIZE / 2,
            top=e.global_position.y  - CELL_SIZE / 2,
            width=CELL_SIZE,
            height=CELL_SIZE,
            alignment=ft.Alignment.CENTER,
            content=make_piece_text(self.piece, size=52),
            shadow=ft.BoxShadow(
                blur_radius=16,
                color=ft.Colors.with_opacity(0.45, ft.Colors.BLACK),
                offset=ft.Offset(2, 4),
            ),
        )
        _drag_state["overlay_piece"] = floating

        self.set_piece_opacity(0)
        self.overlay.controls.append(floating)
        _drag_state["page"].update()

    def _on_drag_update(self, e: ft.DragUpdateEvent):
        if not _drag_state["active"]:
            return

        now = time.monotonic()
        if (now - _drag_state["last_update"]) * 1000 < THROTTLE_MS:
            return

        _drag_state["last_update"] = now
        f: ft.Container = _drag_state["overlay_piece"]
        f.left = e.global_position.x - CELL_SIZE / 2
        f.top  = e.global_position.y  - CELL_SIZE / 2
        _drag_state["page"].update()

    def _on_drag_end(self, e: ft.DragEndEvent):
        if not _drag_state["active"]:
            return

        _drag_state["active"] = False
        src: CellHolder = _drag_state["src"]

        self.overlay.controls.remove(_drag_state["overlay_piece"])
        _drag_state["overlay_piece"] = None

        dst = _hit_test(e.global_position.x, e.global_position.y)

        if dst is None or dst is src:
            src.set_piece_opacity(1)
            _drag_state["page"].update()
            return

        src_piece = board[(src.row, src.col)]
        dst_piece = board.get((dst.row, dst.col))
        if dst_piece and (src_piece.isupper() == dst_piece.isupper()):
            src.set_piece_opacity(1)
            _drag_state["page"].update()
            return

        board[(dst.row, dst.col)] = src_piece
        board[(src.row, src.col)] = None

        src.refresh()
        dst.refresh()
        _drag_state["page"].update()

# ── Hit-test ───────────────────────────────────────────────────────────────────

def _hit_test(gx: float, gy: float) -> Optional["CellHolder"]:
    ox = _drag_state["grid_offset_x"]
    oy = _drag_state["grid_offset_y"]
    if ox is None:
        return None
    step = CELL_SIZE + SPACING
    col = int((gx - ox) / step)
    row = int((gy - oy) / step)
    if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
        return _holders.get((row, col))
    return None

# ── Main ───────────────────────────────────────────────────────────────────────

def main(page: ft.Page):
    page.title         = "PawnPassant"
    page.bgcolor       = "#1A1A2E"
    page.padding       = 32
    page.window.width  = GRID_SIZE * (CELL_SIZE + SPACING) + 80
    page.window.height = GRID_SIZE * (CELL_SIZE + SPACING) + 120

    _drag_state["page"] = page

    overlay = ft.Stack(expand=True)

    rows = []
    for row in range(GRID_SIZE):
        cols = []
        for col in range(GRID_SIZE):
            holder = CellHolder(row, col, overlay)
            _holders[(row, col)] = holder
            cols.append(holder.build())
        rows.append(ft.Row(controls=cols, spacing=SPACING, tight=True))

    grid = ft.Column(controls=rows, spacing=SPACING, tight=True)

    page.add(
        ft.Stack(
            [
                ft.Column(
                    [
                        ft.Text(
                            "PawnPassant",
                            size=18,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE_70,
                        ),
                        ft.Container(
                            content=grid,
                            border_radius=ft.border_radius.all(4),
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            shadow=ft.BoxShadow(
                                blur_radius=32,
                                color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                                offset=ft.Offset(0, 8),
                            ),
                        ),
                    ],
                    spacing=12,
                    tight=True,
                ),
                overlay,
            ],
            expand=True,
        )
    )


ft.app(target=main)