from __future__ import annotations

import logging
import os
from typing import Callable

import chess
from chess import engine as chess_engine

logger = logging.getLogger(__name__)


class EngineManager:
    def __init__(
        self,
        engine_path: str,
        options: dict[str, str] | None = None,
        extra_args: list[str] | None = None,
        env: dict[str, str] | None = None,
        info_callback: Callable[[dict], None] | None = None,
    ):
        self._engine_path = engine_path
        self._options = dict(options) if options else {}
        self._extra_args = list(extra_args) if extra_args else []
        self._env = dict(env) if env else None
        self._info_callback = info_callback

        self._engine: chess_engine.SimpleEngine | None = None
        self._engine_name = ""
        self._engine_author = ""
        self._engine_options: dict[str, str] = {}
        self._last_fen: str = ""

    def start(self) -> bool:
        if self._engine:
            return True

        cmd = list(self._extra_args) + [self._engine_path]
        env_updates = self._env or {}

        old_values: dict[str, str | None] = {}
        try:
            for key, val in env_updates.items():
                old_values[key] = os.environ.get(key)
                os.environ[key] = val

            self._engine = chess_engine.SimpleEngine.popen_uci(cmd)
        except Exception as exc:
            logger.error("Failed to start engine %s: %s", self._engine_path, exc)
            self._engine = None
            return False
        finally:
            for key in env_updates:
                if old_values.get(key) is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_values[key]

        if self._info_callback:
            self._engine.add_listener(self._on_info)

        for key, val in self._options.items():
            try:
                self._engine.configure({key: val})
            except Exception as exc:
                logger.warning("Failed to set option %s=%s: %s", key, val, exc)

        try:
            info = self._engine.id if hasattr(self._engine, "id") else {}
            self._engine_name = info.get("name", "")
            self._engine_author = info.get("author", "")
        except Exception:
            pass

        logger.info("Engine: %s by %s", self._engine_name, self._engine_author)
        return True

    def configure(self, options: dict[str, str]) -> None:
        self._options.update(options)
        if self._engine:
            for key, val in options.items():
                try:
                    self._engine.configure({key: val})
                except Exception as exc:
                    logger.warning("Failed to set option %s=%s: %s", key, val, exc)

    def set_fen(self, fen: str) -> None:
        self._last_fen = fen

    def set_startpos(self, moves: list[str] | None = None) -> None:
        board = chess.Board()
        if moves:
            for m in moves:
                board.push_uci(m)
        self._last_fen = board.fen()

    def go_with_time(
        self,
        wtime: int = 0,
        btime: int = 0,
        winc: int = 0,
        binc: int = 0,
        movestogo: int = 0,
        depth: int | None = None,
        nodes: int | None = None,
        time: float | None = None,
        ponder: bool = False,
    ) -> str | None:
        if not self._engine:
            return None

        board = chess.Board(self._last_fen) if self._last_fen else chess.Board()

        limit = chess_engine.Limit(
            white_clock=max(0.001, wtime / 1000.0) if wtime > 0 else None,
            black_clock=max(0.001, btime / 1000.0) if btime > 0 else None,
            white_inc=winc / 1000.0 if winc > 0 else None,
            black_inc=binc / 1000.0 if binc > 0 else None,
            depth=depth,
            nodes=nodes,
            time=time,
        )

        try:
            result = self._engine.play(board, limit)
            if result.move:
                return result.move.uci()
        except Exception as exc:
            logger.error("Engine play failed: %s", exc)
        return None

    def stop_search(self) -> None:
        if self._engine:
            try:
                self._engine.protocol.send_line("stop")
            except Exception:
                pass

    def new_game(self) -> None:
        pass

    def is_ready(self) -> bool:
        return self._engine is not None

    def get_engine_info(self) -> dict:
        return {
            "name": self._engine_name,
            "author": self._engine_author,
            "options": dict(self._engine_options),
        }

    def stop(self) -> None:
        if self._engine:
            try:
                self._engine.close()
            except Exception:
                pass
            self._engine = None

    def _on_info(self, info: chess_engine.InfoDict) -> None:
        if self._info_callback:
            try:
                self._info_callback(dict(info))
            except Exception as exc:
                logger.warning("Info callback error: %s", exc)
