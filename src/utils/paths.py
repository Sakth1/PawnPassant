"""Platform-aware storage paths for Stockfish binaries and app data.

Follows the same pattern as :mod:`utils.settings` — resolves storage
directories based on the running platform so that desktop builds store
binaries alongside bundled assets while mobile builds use the app sandbox.
"""

import asyncio
import logging
import os
from pathlib import Path

from utils.constants import STOCKFISH_DIR
from utils.system import get_sys_platform

logger = logging.getLogger(__name__)

_ENV_OVERRIDE_KEY = "STOCKFISH_BINARY_DIR"


def get_stockfish_dir(page=None) -> Path:
    """Return the platform-appropriate directory for Stockfish binaries.

    Resolution order:
      1. ``STOCKFISH_BINARY_DIR`` environment variable (escape hatch).
      2. Android → Flet StoragePaths or ``~/.pawnpassant/stockfish``.
      3. Desktop → ``STOCKFISH_DIR`` (bundled ``assets/stockfish``).

    Args:
        page: Optional Flet page object for more accurate platform detection
              (matches the pattern used by :class:`utils.settings.SettingsController`).
              When ``None``, falls back to :func:`utils.system.get_sys_platform`.

    Returns:
        A writable directory path. The directory may not exist yet — callers
        should create it with ``mkdir(parents=True, exist_ok=True)``.
    """
    env_dir = os.environ.get(_ENV_OVERRIDE_KEY)
    if env_dir:
        resolved = Path(env_dir)
        logger.info("Using %s override: %s", _ENV_OVERRIDE_KEY, resolved)
        return resolved

    from utils.models import Platform

    platform_name = _resolve_platform(page)

    if platform_name == Platform.ANDROID.value:
        path = _android_stockfish_dir(page)
        logger.info("Android Stockfish directory -> %s", path)
        return path

    logger.info("Desktop Stockfish directory -> %s", STOCKFISH_DIR)
    return STOCKFISH_DIR


def _android_stockfish_dir(page) -> Path:
    """Return a writable directory for Stockfish binaries on Android.

    Resolution order:
      1. ``FLET_APP_STORAGE_DATA`` environment variable (Flet sandbox,
         always writable on Android).
      2. Flet's ``StoragePaths.get_application_support_directory()``.
      3. ``~/.pawnpassant/stockfish`` (last resort).
    """
    env_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if env_data:
        return Path(env_data) / "pawnpassant" / "stockfish"

    if page is not None:
        storage_paths = getattr(page, "StoragePaths", None)
        if storage_paths is not None and hasattr(
            storage_paths, "get_application_support_directory"
        ):
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    storage_paths.get_application_support_directory(), loop
                )
                path_str = future.result(timeout=5)
                if path_str:
                    return Path(path_str) / "pawnpassant" / "stockfish"
            except (RuntimeError, Exception):
                logger.debug("Could not resolve StoragePaths", exc_info=True)

    return Path.home() / ".pawnpassant" / "stockfish"


def get_log_dir(page=None) -> Path:
    """Return the platform-appropriate directory for application log files.

    Resolution order:
      1. ``FLET_APP_STORAGE_DATA`` environment variable (Flet sandbox,
         always writable on Android).
      2. Flet's ``StoragePaths.get_application_support_directory()``.
      3. ``~/.pawnpassant/logs`` (last resort).

    Args:
        page: Optional Flet page for accurate platform detection.
              Pass ``None`` during early initialisation (before the page
              exists); the directory will be re-resolved later when the
              page is available.

    Returns:
        A writable directory path. The directory may not exist yet —
        callers should create it with ``mkdir(parents=True, exist_ok=True)``.
    """
    env_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if env_data:
        return Path(env_data) / "pawnpassant" / "logs"

    if page is not None:
        storage_paths = getattr(page, "StoragePaths", None)
        if storage_paths is not None and hasattr(
            storage_paths, "get_application_support_directory"
        ):
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    storage_paths.get_application_support_directory(), loop
                )
                path_str = future.result(timeout=5)
                if path_str:
                    return Path(path_str) / "pawnpassant" / "logs"
            except (RuntimeError, Exception):
                logger.debug("Could not resolve StoragePaths for logs", exc_info=True)

    return Path.home() / ".pawnpassant" / "logs"


def _resolve_platform(page) -> str:
    """Extract the normalized platform name, favouring the system platform when
    Flet's runtime value is inconsistent with the detected system platform
    (e.g., Android label on a non-Android kernel) to avoid writing to
    non-writable paths.
    """
    from utils.models import Platform

    if page is not None:
        platform = getattr(page, "platform", None)
        if platform is not None:
            value = getattr(platform, "value", platform)
            flet_platform = str(value).strip().lower()

            if flet_platform == Platform.ANDROID.value:
                sys_platform = get_sys_platform()
                if sys_platform != Platform.ANDROID:
                    logger.warning(
                        "Flet platform=%s contradicts system=%s, preferring system",
                        flet_platform,
                        sys_platform.value,
                    )
                    return sys_platform.value

            return flet_platform

    return get_sys_platform().value
