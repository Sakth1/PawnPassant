from __future__ import annotations

import logging
import os
import platform as _platform
from collections.abc import Callable

import chess

from core.engine_manager import EngineManager
from core.lc0_config import Lc0Options, recommend_backends_for_system
from utils.events import PieceMovedEvent
from utils.game_state import GameAgainst, game_state
from utils.models import Lc0GameConfig
from utils.signals import bus

logger = logging.getLogger(__name__)


def _android_linker_prefix(engine_path: str) -> list[str] | None:
    if "ANDROID_ROOT" not in os.environ:
        return None
    machine = _platform.machine()
    linker = "/system/bin/linker64" if "64" in machine else "/system/bin/linker"
    return [linker]


def _engine_env(engine_path: str) -> dict[str, str] | None:
    engine_dir = os.path.dirname(os.path.abspath(engine_path))
    env = dict(os.environ)
    ld_paths = [engine_dir]
    existing = env.get("LD_LIBRARY_PATH", "")
    if existing:
        ld_paths.insert(0, existing)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(ld_paths)
    return env


class BotManager:
    def __init__(
        self,
        engine_path: str,
        config: Lc0GameConfig | None = None,
        on_bot_move: Callable[[str], None] | None = None,
    ):
        self._config = config or Lc0GameConfig()
        self._on_bot_move = on_bot_move
        self._engine_path = engine_path

        lc0_opts = Lc0Options()
        if self._config.network_path:
            lc0_opts.weights_file = self._config.network_path
        lc0_opts.backend = self._config.backend
        lc0_opts.threads = self._config.threads
        lc0_opts.minibatch_size = self._config.minibatch_size
        lc0_opts.temperature = self._config.temperature
        lc0_opts.cpuct = self._config.cpuct

        extra_args = _android_linker_prefix(engine_path) or []
        env = _engine_env(engine_path)

        self.engine = EngineManager(
            engine_path=engine_path,
            options=lc0_opts.to_uci_options(),
            extra_args=extra_args,
            env=env,
        )
        self._started = False

    def start(self) -> bool:
        if self._started:
            return True
        ok = self.engine.start()
        if ok:
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

        self.engine.set_fen(event.board_fen)
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
            best_move = self.engine.go_with_time(movetime=5000)

        if best_move and self._on_bot_move:
            logger.info("Bot plays %s", best_move)
            self._on_bot_move(best_move)

    def set_config(self, config: Lc0GameConfig) -> None:
        self._config = config
        uci_opts = {}
        if config.network_path:
            uci_opts["WeightsFile"] = config.network_path
        if config.backend:
            uci_opts["Backend"] = config.backend
        if config.threads > 1:
            uci_opts["Threads"] = str(config.threads)
        if config.minibatch_size != 256:
            uci_opts["MinibatchSize"] = str(config.minibatch_size)
        self.engine.configure(uci_opts)

    def stop(self) -> None:
        if self._started:
            self._started = False
            self.engine.stop()
