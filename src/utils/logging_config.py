"""Application logging configuration with cross-platform log storage.

Architecture
------------
* ``configure_logging()`` — called once at startup from ``main.py`` (no Flet
  page yet). Uses the home-directory fallback log path.
* ``reconfigure_logging(page)`` — called later from ``ChessApp.__init__`` once
  the Flet page exists. Re-resolves the log directory via StoragePaths
  (guaranteed writable sandbox on Android) and replaces file handlers if the
  path differs from the initial fallback.
* Both the main log and the crash-rotation log use
  :class:`logging.handlers.RotatingFileHandler` to keep disk usage bounded.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import uuid
from pathlib import Path

from utils.paths import get_log_dir

LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
DEFAULT_LOG_LEVEL = "INFO"

#: Keep up to 3 rotated main-log files of 5 MB each.
MAIN_LOG_MAX_BYTES = 5 * 1024 * 1024
MAIN_LOG_BACKUP_COUNT = 3

#: Keep up to 2 rotated crash-log files of 5 MB each (ERROR+ only).
CRASH_LOG_MAX_BYTES = 5 * 1024 * 1024
CRASH_LOG_BACKUP_COUNT = 2

logger = logging.getLogger(__name__)


class SessionFilter(logging.Filter):
    """Injects a unique session ID into every log record.

    The session ID is generated once per process and stays constant so
    readers can correlate all log lines from a single app launch.
    """

    _session_id: str | None = None

    def filter(self, record: logging.LogRecord) -> bool:
        if self._session_id is None:
            self._session_id = uuid.uuid4().hex[:8]
        record.session_id = self._session_id
        return True


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)


def _build_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    return handler


def _build_main_file_handler(
    log_dir: Path, formatter: logging.Formatter,
) -> logging.handlers.RotatingFileHandler | None:
    """Create a rotating file handler for the main application log."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=MAIN_LOG_MAX_BYTES,
            backupCount=MAIN_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        return handler
    except Exception as exc:
        print(f"Warning: Could not initialise main log file: {exc}")
        return None


def _build_crash_file_handler(
    log_dir: Path, formatter: logging.Formatter,
) -> logging.handlers.RotatingFileHandler | None:
    """Create a rotating file handler capturing ERROR and above only."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_dir / "crash.log",
            maxBytes=CRASH_LOG_MAX_BYTES,
            backupCount=CRASH_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        return handler
    except Exception as exc:
        print(f"Warning: Could not initialise crash log file: {exc}")
        return None


def configure_logging() -> None:
    """Configure process-wide logging once for app and library modules.

    Called early in ``main.py`` before the Flet page exists.  Logs go to
    ``~/.pawnpassant/logs/`` until :func:`reconfigure_logging` switches
    to a platform-appropriate path.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    level_name = os.getenv("PAWNPASSANT_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = _build_formatter()

    handlers: list[logging.Handler] = [_build_console_handler(formatter)]

    log_dir = get_log_dir(page=None)
    main_handler = _build_main_file_handler(log_dir, formatter)
    if main_handler is not None:
        handlers.append(main_handler)

    crash_handler = _build_crash_file_handler(log_dir, formatter)
    if crash_handler is not None:
        handlers.append(crash_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    root.addFilter(SessionFilter())

    _configure_flet_logging()

    logger.info(
        "Logging initialised level=%s dir=%s",
        level_name,
        log_dir,
    )


def reconfigure_logging(page) -> None:
    """Re-resolve the log directory now that the Flet page is available.

    On Android (and packaged desktop apps) the StoragePaths support
    directory differs from ``~/.pawnpassant/logs/``.  This call replaces
    the initial file handlers so logs land in the correct sandboxed path.
    Safe to call multiple times — no-op when the path hasn't changed.
    """
    new_dir = get_log_dir(page)
    root = logging.getLogger()

    # Collect current file‑handler paths.
    current_dirs: set[Path] = set()
    for h in root.handlers:
        if isinstance(h, logging.handlers.RotatingFileHandler):
            try:
                current_dirs.add(Path(h.baseFilename).parent)
            except Exception:
                pass

    if new_dir in current_dirs:
        logger.debug("Log directory unchanged (%s), skipping reconfigure", new_dir)
        return

    formatter = _build_formatter()

    new_handlers: list[logging.Handler] = []
    for h in root.handlers:
        if isinstance(h, (logging.StreamHandler,)):
            new_handlers.append(h)
        elif isinstance(h, logging.handlers.RotatingFileHandler):
            try:
                h.close()
                root.removeHandler(h)
            except Exception:
                pass

    main_handler = _build_main_file_handler(new_dir, formatter)
    if main_handler is not None:
        new_handlers.append(main_handler)
        root.addHandler(main_handler)

    crash_handler = _build_crash_file_handler(new_dir, formatter)
    if crash_handler is not None:
        new_handlers.append(crash_handler)
        root.addHandler(crash_handler)

    # Replace the handler list on the root logger via basicConfig.
    # We keep existing non-file handlers (console) and add new file handlers.
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.handlers.RotatingFileHandler)]
    for h in [main_handler, crash_handler]:
        if h is not None:
            root.addHandler(h)

    logger.info("Logging reconfigured dir=%s", new_dir)


def _configure_flet_logging() -> None:
    """Enable Flet internal logging for session lifecycle diagnostics."""
    flet_level_name = os.getenv("PAWNPASSANT_FLET_LOG_LEVEL", "DEBUG").upper()
    flet_level = getattr(logging, flet_level_name, logging.DEBUG)
    logging.getLogger("flet").setLevel(flet_level)
