import asyncio
import glob
import logging
import os
from pathlib import Path

from utils.constants import ENGINE_DIR
from utils.system import get_sys_platform

logger = logging.getLogger(__name__)

_ENV_ENGINE_OVERRIDE_KEY = "ENGINE_BINARY_DIR"


def get_engine_dir(page=None) -> Path:
    env_dir = os.environ.get(_ENV_ENGINE_OVERRIDE_KEY)
    if env_dir:
        return Path(env_dir)
    from utils.models import Platform
    platform_name = _resolve_platform(page)
    if platform_name == Platform.ANDROID.value:
        return _android_engine_dir(page)
    return ENGINE_DIR


def _android_engine_dir(page) -> Path:
    env_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if env_data:
        return Path(env_data) / "pawnpassant" / "engine"
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
                    return Path(path_str) / "pawnpassant" / "engine"
            except (RuntimeError, Exception):
                logger.debug("Could not resolve StoragePaths for engine", exc_info=True)
    return Path.home() / ".pawnpassant" / "engine"


def get_log_dir(page=None) -> Path:
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


def get_active_engine_path(
    page=None,
    source: str = "bundled",
    downloaded_path: str = "",
    engine_name: str = "stockfish",
) -> Path | None:
    if source == "bundled":
        bundled = get_bundled_engine_path(page, engine_name)
        if bundled is not None:
            return bundled
    elif source == "downloaded" and downloaded_path:
        p = Path(downloaded_path)
        if p.exists():
            return p.resolve()
    downloaded = get_downloaded_engine_path(page, engine_name)
    if downloaded is not None:
        return downloaded
    return get_bundled_engine_path(page, engine_name)


def get_bundled_engine_path(page=None, engine_name: str = "stockfish") -> Path | None:
    android_path = _extract_android_asset_engine(page, engine_name)
    if android_path:
        return android_path

    env_lib = os.environ.get("FLET_APP_LIB_DIR")
    so_name = f"lib{engine_name}.so"
    if env_lib:
        candidate = Path(env_lib) / so_name
        if candidate.exists():
            return candidate.resolve()
    for p in [
        f"/data/app/*/lib/arm64/{so_name}",
        f"/data/app/*/lib/arm/{so_name}",
        f"/data/app/*/lib/*/{so_name}",
    ]:
        matches = sorted(glob.glob(p))
        for m in matches:
            return Path(m).resolve()
    desktop = ENGINE_DIR / so_name
    if desktop.exists():
        return desktop.resolve()
    return None


def _extract_android_asset_engine(page=None, engine_name: str = "stockfish") -> Path | None:
    """Copy bundled engine from APK assets to writable engine dir on Android."""
    from core.stockfish_config import is_android
    if not is_android():
        return None

    assets_dir = os.environ.get("FLET_ASSETS_DIR")
    if not assets_dir:
        return None

    import platform as _platform
    machine = _platform.machine()
    abi = "arm64-v8a" if "64" in machine else "armeabi-v7a"

    asset_binary = Path(assets_dir) / "stockfish" / "android" / abi / engine_name
    if not asset_binary.exists():
        asset_binary = Path(assets_dir) / "stockfish" / "android" / abi / f"{engine_name}.exe"
        if not asset_binary.exists():
            return None

    engine_dir = _android_engine_dir(page)
    engine_dir.mkdir(parents=True, exist_ok=True)
    dest = engine_dir / engine_name

    if not dest.exists():
        import shutil
        logger.info("Copying bundled engine from %s to %s", asset_binary, dest)
        try:
            shutil.copy2(str(asset_binary), str(dest))
            dest.chmod(0o755)
        except OSError as exc:
            logger.warning("Failed to extract bundled engine: %s", exc)
            return None

    if dest.exists():
        return dest.resolve()
    return None


def get_downloaded_engine_path(page=None, engine_name: str = "stockfish") -> Path | None:
    eng_dir = get_engine_dir(page)
    exe_name = f"{engine_name}.exe" if os.name == "nt" else engine_name
    candidate = eng_dir / exe_name
    if candidate.exists():
        return candidate.resolve()
    return None


def _resolve_platform(page) -> str:
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
