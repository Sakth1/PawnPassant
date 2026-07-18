from __future__ import annotations

import logging
import os
import platform as _platform
import threading
from collections.abc import Callable

import chess

from core.engine_manager import EngineManager
from utils.events import PieceMovedEvent
from utils.game_state import GameAgainst, game_state
from utils.models import StockfishGameConfig
from utils.signals import bus

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(
        self,
        engine_path: str,
        config: StockfishGameConfig | None = None,
        on_bot_move: Callable[[str], None] | None = None,
        page=None,
    ):
        self._config = config or StockfishGameConfig()
        self._on_bot_move = on_bot_move
        self._engine_path = engine_path
        self._page = page
        self._search_lock = threading.Lock()

        self.engine = EngineManager(
            engine_path=engine_path,
        )
        self._started = False

    def start(self) -> bool:
        if self._started:
            return True
        ok = self.engine.start()
        if ok:
            self.engine.configure_stockfish(
                elo=self._config.elo,
                threads=self._config.threads,
                hash_mb=self._config.hash_mb,
            )
            self._started = True
            bus.connect(PieceMovedEvent, self._on_piece_moved)
            logger.info("BotManager started with engine=%s", self._engine_path)
        return ok

    def _on_piece_moved(self, event: PieceMovedEvent) -> None:
        if game_state.game_against != GameAgainst.COMPUTER:
            return
        if event.active_color == chess.WHITE:
            return
        if not self._started or not self.engine.is_ready():
            return

        if not self._search_lock.acquire(blocking=False):
            logger.debug("Bot search already in progress, skipping move event")
            return

        threading.Thread(
            target=self._do_search,
            args=(event.board_fen,),
            daemon=True,
        ).start()

    def _do_search(self, fen: str) -> None:
        try:
            self.engine.set_fen(fen)

            tc = game_state.time_control
            if tc:
                minutes, increment = tc
                wtime = btime = (minutes * 60 * 1000) // 40
                winc = binc = increment * 1000
                best_move = self.engine.go_with_time(
                    wtime=wtime,
                    btime=btime,
                    winc=winc,
                    binc=binc,
                )
            else:
                best_move = self.engine.go_with_time(time=5.0)

            if best_move and self._on_bot_move:
                logger.info("Bot plays %s", best_move)
                if self._page:
                    self._page.run_task(self._async_apply_bot_move, best_move)
                else:
                    self._on_bot_move(best_move)
        except Exception:
            logger.exception("Bot search failed")
        finally:
            self._search_lock.release()

    async def _async_apply_bot_move(self, uci: str) -> None:
        if self._on_bot_move:
            self._on_bot_move(uci)

    def set_config(self, config: StockfishGameConfig) -> None:
        self._config = config
        self.engine.configure_stockfish(
            elo=config.elo,
            threads=config.threads,
            hash_mb=config.hash_mb,
        )

    def stop(self) -> None:
        if self._started:
            self._started = False
            self.engine.stop()
