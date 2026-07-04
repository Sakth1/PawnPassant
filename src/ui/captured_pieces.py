"""Compact captured-pieces panel.

Displays captured pieces as a horizontal row of small icons sorted by value,
matching the style used by Chess.com and Lichess — minimal, compact, and
non-dominant.
"""

from __future__ import annotations

import logging
from collections import Counter

import chess
import flet as ft

from ui.chess_piece import ChessPiece
from utils.dialogs import safe_update
from utils.events import PieceCapturedEvent
from utils.signals import bus

logger = logging.getLogger(__name__)

PIECE_SORT_ORDER = {
    chess.QUEEN: 0,
    chess.ROOK: 1,
    chess.BISHOP: 2,
    chess.KNIGHT: 3,
    chess.PAWN: 4,
}


class CaputredPieces(ft.Container):
    """Compact horizontal strip of captured piece icons.

    When *capturing_side* is ``None`` all captures are shown. When set to
    ``chess.WHITE`` or ``chess.BLACK`` only captures by that side are
    displayed — used by the split-layout game page.
    """

    def __init__(self, capturing_side: int | None = None):
        super().__init__()
        self._capturing_side = capturing_side
        self._captured: list[chess.Piece] = []

        self._icon_size = 20

        self._piece_row = ft.Row(spacing=2, controls=[])
        self._label = ft.Text(
            "Captures" if capturing_side is None else "",
            size=10,
            color=ft.Colors.GREY_500,
            visible=False,
        )

        self.content = ft.Column(
            spacing=2,
            controls=[self._label, self._piece_row],
        )

        bus.connect(
            PieceCapturedEvent, lambda event: self._handle_piece_captured(event)
        )

    def apply_layout(self, _layout) -> None:
        pass

    def _make_small_icon(self, piece: chess.Piece) -> ft.Container:
        cp = ChessPiece(piece)
        cp.square_size = self._icon_size
        return ft.Container(
            content=cp.to_control(),
            width=self._icon_size + 2,
            height=self._icon_size + 2,
        )

    def _handle_piece_captured(self, event: PieceCapturedEvent) -> None:
        if self._capturing_side is not None and event.color != self._capturing_side:
            return
        self._captured.append(event.piece.piece)
        self._rebuild_display()
        safe_update(self)

    def _rebuild_display(self) -> None:
        if not self._captured:
            self._piece_row.controls = []
            self._label.visible = False
            return

        counts: Counter[tuple[int, bool]] = Counter()
        for p in self._captured:
            counts[(p.piece_type, p.color)] += 1

        sorted_keys = sorted(
            counts.keys(),
            key=lambda k: (PIECE_SORT_ORDER.get(k[0], 99), k[1]),
        )

        controls: list[ft.Control] = []
        for piece_type, color in sorted_keys:
            count = counts[(piece_type, color)]
            controls.append(self._make_small_icon(chess.Piece(piece_type, color)))
            if count > 1:
                controls.append(
                    ft.Container(
                        ft.Text(
                            f"\u00d7{count}",
                            size=9,
                            color=ft.Colors.GREY_400,
                        ),
                        margin=ft.Margin(0, 0, 4, 0),
                    )
                )

        self._piece_row.controls = controls
        self._label.visible = True

    def reset(self) -> None:
        self._captured.clear()
        self._rebuild_display()
