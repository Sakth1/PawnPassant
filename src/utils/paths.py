"""Platform-aware storage paths for Stockfish binaries and app data.

Follows the same pattern as :mod:`utils.settings` — resolves storage
directories based on the running platform so that desktop builds store
binaries alongside bundled assets while mobile builds use the app sandbox.
"""

from pathlib import Path

from utils.constants import STOCKFISH_DIR
from utils.system import get_sys_platform


def get_stockfish_dir(page=None) -> Path:
    """Return the platform-appropriate directory for Stockfish binaries.

    Args:
        page: Optional Flet page object for more accurate platform detection
              (matches the pattern used by :class:`utils.settings.SettingsController`).
              When ``None``, falls back to :func:`utils.system.get_sys_platform`.

    Returns:
        A writable directory path. The directory may not exist yet — callers
        should create it with ``mkdir(parents=True, exist_ok=True)``.
    """
    from utils.models import Platform

    platform_name = _resolve_platform(page)

    if platform_name == Platform.ANDROID.value:
        return Path.home() / ".pawnpassant" / "stockfish"

    return STOCKFISH_DIR


def _resolve_platform(page) -> str:
    """Extract the normalized platform name, favouring Flet's runtime value."""
    if page is not None:
        platform = getattr(page, "platform", None)
        if platform is not None:
            value = getattr(platform, "value", platform)
            return str(value).strip().lower()

    return get_sys_platform().value
