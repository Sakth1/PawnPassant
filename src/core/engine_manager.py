from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Callable

logger = logging.getLogger(__name__)

UCI_RESPONSE_TIMEOUT = 30.0
GO_TIMEOUT = 600.0
READER_POLL_INTERVAL = 0.05

_INFO_LINE_RE = re.compile(
    r"info"
    r"(?:\s+depth\s+(?P<depth>\d+))?"
    r"(?:\s+seldepth\s+(?P<seldepth>\d+))?"
    r"(?:\s+multipv\s+(?P<multipv>\d+))?"
    r"(?:\s+score\s+(?P<score_type>cp|mate)\s+(?P<score_value>-?\d+))?"
    r"(?:\s+lowerbound\s+(?P<lowerbound>lowerbound))?"
    r"(?:\s+upperbound\s+(?P<upperbound>upperbound))?"
    r"(?:\s+nodes\s+(?P<nodes>\d+))?"
    r"(?:\s+seldepth\s+(?P<seldepth2>\d+))?"
    r"(?:\s+time\s+(?P<time_ms>\d+))?"
    r"(?:\s+nps\s+(?P<nps>\d+))?"
    r"(?:\s+hashfull\s+(?P<hashfull>\d+))?"
    r"(?:\s+tbhits\s+(?P<tbhits>\d+))?"
    r"(?:\s+cpuload\s+(?P<cpuload>\d+))?"
    r"(?:\s+pv\s+(?P<pv>.+))?"
)


def _parse_info_line(line: str) -> dict | None:
    m = _INFO_LINE_RE.search(line)
    if not m:
        return None
    info = {}
    for key, val in m.groupdict().items():
        if val is not None:
            cleaned_key = key.rstrip("2")
            if cleaned_key in info:
                continue
            info[cleaned_key] = val
    if "score_type" in info:
        info["score"] = {"type": info.pop("score_type"), "value": int(info.pop("score_value"))}
    if "pv" in info:
        info["pv"] = info["pv"].strip()
    return info if info else None


THREAD_INDEFINITE = 0


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

        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._output_queue: Queue[str] = Queue()
        self._reader_thread: threading.Thread | None = None
        self._ready = False
        self._engine_name = ""
        self._engine_author = ""
        self._engine_options: dict[str, str] = {}

    def start(self) -> bool:
        with self._lock:
            if self._proc:
                return True
            try:
                self._proc = subprocess.Popen(
                    [self._engine_path] + self._extra_args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=self._env,
                )
            except OSError as exc:
                logger.error("Failed to start engine %s: %s", self._engine_path, exc)
                self._proc = None
                return False

        self._stopped.clear()
        self._reader_thread = threading.Thread(target=_reader_loop, args=(self,), daemon=True)
        self._reader_thread.start()

        ok = self._uci_init()
        if not ok:
            self.stop()
            return False
        return True

    def _uci_init(self) -> bool:
        lines = self._communicate("uci", "uciok", timeout=UCI_RESPONSE_TIMEOUT)
        if not lines:
            logger.error("UCI init failed: no uciok response")
            return False

        for line in lines:
            if line.startswith("id name "):
                self._engine_name = line[len("id name "):].strip()
            elif line.startswith("id author "):
                self._engine_author = line[len("id author "):].strip()
            elif line.startswith("option name "):
                self._parse_option_line(line)

        logger.info("Engine: %s by %s", self._engine_name, self._engine_author)

        for key, val in self._options.items():
            self._write(f"setoption name {key} value {val}")

        ready = self._communicate("isready", "readyok", timeout=UCI_RESPONSE_TIMEOUT)
        if not ready:
            logger.error("UCI init failed: engine not ready")
            return False

        self._ready = True
        return True

    def _parse_option_line(self, line: str) -> None:
        rest = line[len("option name "):]
        parts = rest.split(" type ")
        if len(parts) >= 2:
            name = parts[0].strip()
            self._engine_options[name] = parts[1].strip()

    def configure(self, options: dict[str, str]) -> None:
        with self._lock:
            self._options.update(options)
            if self._proc:
                for key, val in options.items():
                    self._write(f"setoption name {key} value {val}")

    def set_fen(self, fen: str) -> None:
        with self._lock:
            self._write(f"position fen {fen}")

    def set_startpos(self, moves: list[str] | None = None) -> None:
        with self._lock:
            if moves:
                self._write("position startpos moves " + " ".join(moves))
            else:
                self._write("position startpos")

    def go(self, **params) -> str | None:
        go_cmd = "go"
        if params:
            go_cmd += " " + " ".join(f"{k} {v}" for k, v in params.items())
        lines = self._communicate(go_cmd, "bestmove", timeout=GO_TIMEOUT)

        for line in lines:
            if line.startswith("bestmove "):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return None

    def go_with_time(
        self,
        wtime: int = 0,
        btime: int = 0,
        winc: int = 0,
        binc: int = 0,
        movestogo: int = 0,
        depth: int | None = None,
        nodes: int | None = None,
        movetime: int | None = None,
        ponder: bool = False,
    ) -> str | None:
        params = {}
        if wtime > 0:
            params["wtime"] = wtime
        if btime > 0:
            params["btime"] = btime
        if winc > 0:
            params["winc"] = winc
        if binc > 0:
            params["binc"] = binc
        if movestogo > 0:
            params["movestogo"] = movestogo
        if depth is not None:
            params["depth"] = depth
        if nodes is not None:
            params["nodes"] = nodes
        if movetime is not None:
            params["movetime"] = movetime
        if ponder:
            params["ponder"] = ""
        return self.go(**params)

    def stop_search(self) -> None:
        with self._lock:
            if self._proc:
                self._write("stop")

    def new_game(self) -> None:
        with self._lock:
            self._write("ucinewgame")

    def is_ready(self) -> bool:
        return self._ready and self._proc is not None and self._proc.poll() is None

    def get_engine_info(self) -> dict:
        return {
            "name": self._engine_name,
            "author": self._engine_author,
            "options": dict(self._engine_options),
        }

    def stop(self) -> None:
        self._stopped.set()
        with self._lock:
            if self._proc:
                try:
                    self._write("quit")
                except Exception:
                    pass
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait()
                self._proc = None
            self._ready = False

    def _write(self, cmd: str) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("Engine process not running")
        logger.debug("Engine << %s", cmd)
        self._proc.stdin.write(cmd + "\n")
        self._proc.stdin.flush()

    def _communicate(self, cmd: str, marker: str, timeout: float = 10.0) -> list[str]:
        lines: list[str] = []
        with self._lock:
            if self._proc:
                self._write(cmd)
            else:
                return lines

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self._stopped.is_set():
                    break
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    line = self._output_queue.get(timeout=min(0.1, remaining))
                except Empty:
                    continue
                lines.append(line)
                if marker in line:
                    return lines
        return lines


def _reader_loop(mgr: EngineManager) -> None:
    proc = mgr._proc
    if not proc or not proc.stdout:
        return
    try:
        for raw_line in proc.stdout:
            if mgr._stopped.is_set():
                break
            line = raw_line.rstrip("\n\r")
            if not line:
                continue
            logger.debug("Engine >> %s", line)
            mgr._output_queue.put(line)
            if mgr._info_callback and line.startswith("info "):
                parsed = _parse_info_line(line)
                if parsed:
                    try:
                        mgr._info_callback(parsed)
                    except Exception as exc:
                        logger.warning("Info callback error: %s", exc)
    except ValueError:
        pass
    except OSError:
        pass
    logger.debug("Engine reader thread exiting")
