"""Read, parse, and format application log entries for in-app display and
clipboard export.

Works with the rotating log files written by :mod:`utils.logging_config`.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from utils.paths import get_log_dir
from utils.system import get_system_info

logger = logging.getLogger(__name__)

#: Regex matching the log format used by logging_config:
#: ``%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s``
_LOG_PATTERN = re.compile(
    r"^(\S+)\s+-\s+(\w+)\s+-\s+\[([^:]+?)(?::(\d+))?\]\s+-\s+(.*)$",
)

#: Known severity levels ordered by priority.
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def get_app_version() -> str:
    """Read the app version from ``pyproject.toml``."""
    try:
        toml_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        for line in toml_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("version"):
                raw = line.split("=", 1)[1].strip().strip("\"'")
                return raw
    except Exception:
        pass
    return "unknown"


def get_log_path(page=None) -> Path | None:
    """Resolve the path to the current active ``app.log`` file.

    Returns ``None`` when the log directory cannot be determined.
    """
    try:
        log_dir = get_log_dir(page)
        if log_dir is None:
            return None
        return log_dir / "app.log"
    except Exception:
        logger.debug("Could not resolve log path", exc_info=True)
        return None


def parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse a single log line into a structured dictionary.

    Expected format::

        asctime - LEVEL - [module:lineno] - message

    Returns ``None`` for lines that do not match (e.g. stack traces).
    """
    if not line or not line.strip():
        return None
    match = _LOG_PATTERN.match(line.strip())
    if not match:
        return None
    return {
        "timestamp": match.group(1),
        "level": match.group(2),
        "module": match.group(3),
        "lineno": int(match.group(4)) if match.group(4) else 0,
        "message": match.group(5),
        "raw": line.rstrip("\n"),
    }


def read_recent_logs(
    max_lines: int = 200,
    page=None,
    min_level: str | None = None,
) -> list[dict[str, Any]]:
    """Read up to *max_lines* of the most recent log entries.

    Parameters
    ----------
    max_lines:
        Maximum number of entries to return (reads from the end).
    page:
        Optional Flet page for log-directory resolution.
    min_level:
        If set (e.g. ``"WARNING"``), only entries at or above this severity
        are returned.

    Returns
    -------
    A list of parsed log-entry dicts, most recent last.
    """
    log_path = get_log_path(page)
    if log_path is None or not log_path.exists():
        return []

    min_index = _level_index(min_level) if min_level else 0

    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.warning("Could not read log file %s", log_path)
        return []

    lines = text.splitlines()
    entries: list[dict[str, Any]] = []
    current_tb: list[str] = []
    for line in lines:
        parsed = parse_log_line(line)
        if parsed is not None:
            if current_tb:
                parsed["_tb"] = current_tb
                current_tb = []
            if _level_index(parsed["level"]) >= min_index:
                entries.append(parsed)
        else:
            stripped = line.strip()
            if stripped:
                current_tb.append(line)

    if current_tb and entries:
        entries[-1].setdefault("_tb", []).extend(current_tb)

    result = entries[-max_lines:]
    if len(result) < 10 and log_path is not None:
        logger.debug(
            "read_recent_logs returned only %d entries (requested %d) from %s",
            len(result), max_lines, log_path,
        )
    return result


def _level_index(level_name: str) -> int:
    """Return a numeric priority for *level_name* (0 = DEBUG … 4 = CRITICAL)."""
    try:
        return LEVELS.index(level_name.upper())
    except ValueError:
        return 0


def build_error_report(
    error_msg: str,
    extra_info: dict[str, str] | None = None,
    page=None,
    recent_lines: int = 20,
) -> str:
    """Build a complete copyable error report.

    Includes system info, the error message, and the last *recent_lines*
    log entries.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sys_info = get_system_info()
    version = get_app_version()

    lines = [
        "PawnPassant Error Report",
        "========================",
        f"Time:       {timestamp}",
        f"Version:    {version}",
        f"Platform:   {sys_info.platform.label}",
        f"Arch:       {sys_info.arch.value}",
        f"CPU:        {sys_info.subarch.value}",
        "",
    ]
    if extra_info:
        for key, value in extra_info.items():
            lines.append(f"{key}: {value}")
        lines.append("")

    lines.append("Error:")
    lines.append(f"  {error_msg}")
    lines.append("")

    recent = read_recent_logs(max_lines=recent_lines, page=page)
    if recent:
        lines.append(f"Recent log entries (last {len(recent)}):")
        lines.append("----------------------------------------")
        for entry in recent:
            lines.append(entry["raw"])
            tb_lines = entry.get("_tb")
            if tb_lines:
                lines.append("")
                lines.extend(tb_lines)
                lines.append("")
    else:
        lines.append("(No recent log entries found.)")

    lines.append("")
    lines.append("--- End of report ---")
    return "\n".join(lines)
