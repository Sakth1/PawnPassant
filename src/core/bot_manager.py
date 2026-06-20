import logging
from collections.abc import Callable

import chess
from stockfish import Stockfish

from utils.events import PieceMovedEvent
from utils.game_state import GameAgainst, game_state
from utils.models import EngineConfig, StockfishGameConfig
from utils.signals import bus

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(
        self,
        engine_path: str,
        config: EngineConfig | StockfishGameConfig | None = None,
        on_bot_move: Callable[[str], None] | None = None,
    ):
        if isinstance(config, StockfishGameConfig):
            self._config = EngineConfig(
                depth=config.depth,
                elo=config.elo,
                skill_level=config.skill_level,
                threads=config.threads,
                hash_mb=config.hash_mb,
            )
        else:
            self._config = config or EngineConfig()
        self._on_bot_move = on_bot_move
        params: dict = {}
        if self._config.elo is not None:
            params["Elo"] = self._config.elo
        if self._config.skill_level is not None:
            params["Skill Level"] = self._config.skill_level
        if self._config.threads > 1:
            params["Threads"] = self._config.threads
        if self._config.hash_mb != 256:
            params["Hash"] = self._config.hash_mb
        self.stockfish = Stockfish(
            path=engine_path,
            depth=self._config.depth,
            parameters=params or None,
        )
        bus.connect(PieceMovedEvent, self._on_piece_moved)

    def _on_piece_moved(self, event: PieceMovedEvent) -> None:
        if game_state.game_against != GameAgainst.COMPUTER:
            return
        if event.active_color == chess.WHITE:
            return
        self.stockfish.set_fen_position(event.board_fen)
        best_move = self.stockfish.get_best_move()
        if best_move and self._on_bot_move:
            logger.info("Bot plays %s", best_move)
            self._on_bot_move(best_move)

    def set_depth(self, depth: int) -> None:
        self._config = EngineConfig(
            depth=depth,
            elo=self._config.elo,
            skill_level=self._config.skill_level,
            threads=self._config.threads,
            hash_mb=self._config.hash_mb,
        )
        self.stockfish.set_depth(depth)

    def set_elo(self, elo: int) -> None:
        self._config = EngineConfig(
            elo=elo,
            depth=self._config.depth,
            skill_level=self._config.skill_level,
            threads=self._config.threads,
            hash_mb=self._config.hash_mb,
        )
        self.stockfish.set_elo_rating(elo)

    def set_skill_level(self, skill_level: int) -> None:
        self._config = EngineConfig(
            skill_level=skill_level,
            depth=self._config.depth,
            elo=self._config.elo,
            threads=self._config.threads,
            hash_mb=self._config.hash_mb,
        )
        self.stockfish.set_skill_level(skill_level)
