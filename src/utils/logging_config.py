"""Application logging configuration."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
DEFAULT_LOG_LEVEL = "INFO"


def configure_logging() -> None:
    """Configure process-wide logging once for app and library modules."""

    if logging.getLogger().handlers:
        return

    level_name = os.getenv("PAWNPASSANT_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [console_handler]

    # Main Application Log
    log_file_env = os.getenv("PAWNPASSANT_LOG_FILE", "").strip()
    project_root = Path(__file__).resolve().parent.parent.parent
    default_log_dir = project_root / "logs"

    if log_file_env:
        log_path = Path(log_file_env)
    else:
        log_path = default_log_dir / "app.log"

    if os.getenv("PAWNPASSANT_DEV", "").lower() == "true":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_path.with_name(f"{log_path.stem}_{timestamp}{log_path.suffix}")

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not initialize application log file: {e}")

    # Crash Log (Errors and Criticals)
    try:
        # Use Path.home() which is OS-agnostic. 
        # 'Documents' is the standard folder name on Windows, macOS, and most Linux distros.
        crash_dir = Path.home() / "Documents" / "pawn passant crash log"
        crash_log_path = crash_dir / "pawnpassant_crash.log"
        crash_dir.mkdir(parents=True, exist_ok=True)
        crash_handler = logging.FileHandler(crash_log_path, encoding="utf-8")
        crash_handler.setLevel(logging.ERROR)
        crash_handler.setFormatter(formatter)
        handlers.append(crash_handler)
    except Exception as e:
        print(f"Warning: Could not initialize crash logger: {e}")

    logging.basicConfig(level=level, handlers=handlers)

