"""Stockfish binary download and asset matching.

Two-phase API:

1. **Query** — :meth:`query_release` fetches the latest release from GitHub
   and returns an :class:`~utils.models.AssetMatchResult` with the best
   matching asset for the current system (name + size + version). No file
   is downloaded during this phase.

2. **Download** — :meth:`download` writes the selected asset to disk.
   Progress is tracked via :meth:`get_progress` which the caller polls.

:meth:`download_async` runs the actual HTTP I/O in a thread-pool thread,
keeping the Flet event loop fully responsive.
"""

import asyncio
import logging
import os
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, Self

import httpx

from utils.constants import STOCKFISH_DIR
from utils.events import StockfishDownloadFailedEvent
from utils.models import (
    Arch,
    AssetMatchResult,
    CpuSubarch,
    DownloadedAsset,
    Platform,
    StockfishAsset,
)
from utils.signals import bus
from utils.system import get_sys_arch, get_sys_platform

logger = logging.getLogger(__name__)

_STOCKFISH_API = (
    "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest"
)

_ASSET_PATTERN = re.compile(
    r"^stockfish-"
    r"(?P<os>windows|linux|macos|android)-"
    r"(?:(?P<arch>x86-64|arm64|i686)-)?"
    r"(?P<variant>avx2|modern|bmi2|vnni|apple-silicon|armv8)?"
    r"(?:\..+)?$",
)

_ARCH_FROM_ASSET = {
    "x86-64": Arch.X86_64,
    "arm64": Arch.ARM64,
    "armv8": Arch.ARM64,
    "i686": Arch.X86,
}

_PLATFORM_FROM_ASSET = {
    "windows": Platform.WINDOWS,
    "linux": Platform.LINUX,
    "macos": Platform.MACOS,
    "android": Platform.ANDROID,
}

_SUBARCH_FROM_ASSET = {
    "avx2": CpuSubarch.AVX2,
    "modern": CpuSubarch.MODERN,
    "bmi2": CpuSubarch.BMI2,
    "vnni": CpuSubarch.VNNI,
    "apple-silicon": CpuSubarch.APPLE_SILICON,
    "armv8": CpuSubarch.ARMV8,
}

_INFERRED_ARCH = {
    "armv8": Arch.ARM64,
    "apple-silicon": Arch.ARM64,
}

_SUBARCH_PRIORITY = {
    CpuSubarch.VNNI: 6,
    CpuSubarch.BMI2: 5,
    CpuSubarch.AVX2: 4,
    CpuSubarch.APPLE_SILICON: 4,
    CpuSubarch.MODERN: 3,
    CpuSubarch.ARMV8: 2,
    CpuSubarch.GENERIC: 1,
    CpuSubarch.UNKNOWN: 0,
}

#: Chunk size for streaming downloads (bytes).
_CHUNK_SIZE = 8192


def _parse_asset_name(name: str) -> tuple[Platform, Arch, CpuSubarch] | None:
    m = _ASSET_PATTERN.match(name)
    if not m:
        return None
    os_str = m.group("os")
    arch_str = m.group("arch")
    variant_str = m.group("variant")

    platform_val = _PLATFORM_FROM_ASSET.get(os_str)
    if platform_val is None:
        return None

    if arch_str:
        arch_val = _ARCH_FROM_ASSET.get(arch_str, Arch.UNKNOWN)
        subarch_val = (
            _SUBARCH_FROM_ASSET.get(variant_str, CpuSubarch.UNKNOWN)
            if variant_str
            else CpuSubarch.GENERIC
        )
    else:
        arch_val = _INFERRED_ARCH.get(variant_str, Arch.UNKNOWN)
        subarch_val = (
            _SUBARCH_FROM_ASSET.get(variant_str, CpuSubarch.UNKNOWN)
            if variant_str
            else CpuSubarch.GENERIC
        )

    return platform_val, arch_val, subarch_val


def _make_executable(path: Path) -> None:
    """Ensure the binary has executable permissions (Unix/macOS/Android)."""
    try:
        current = path.stat().st_mode
        path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        logger.warning("Could not set executable permission on %s", path)


def _resolve_archive(path: Path) -> Path:
    """If *path* is a zip/tar archive, extract it and return the inner binary.

    For plain binaries (not archives), returns *path* unchanged.
    The archive is deleted after extraction; the binary is moved to
    ``path.parent / stockfish[.exe]``.
    """
    suffix = path.suffix.lower()
    is_tar_gz = suffix == ".gz" and path.name.lower().endswith(".tar.gz")
    is_tgz = suffix == ".tgz"

    if suffix not in (".zip", ".gz", ".tgz") and not is_tar_gz:
        return path

    if not path.exists():
        logger.warning("Archive not found: %s", path)
        return path

    tmp_dir = Path(tempfile.mkdtemp(prefix="stockfish_extract_"))
    logger.info("Extracting %s -> %s", path, tmp_dir)

    try:
        if suffix == ".zip":
            with zipfile.ZipFile(str(path), "r") as zf:
                zf.extractall(str(tmp_dir))
        elif is_tar_gz or is_tgz:
            with tarfile.open(str(path), "r:gz") as tf:
                tf.extractall(str(tmp_dir))
        else:
            return path

        candidates = [
            f
            for f in tmp_dir.rglob("*")
            if f.is_file()
            and "stockfish" in f.name.lower()
            and not f.name.startswith(".")
        ]

        if not candidates:
            logger.warning("No stockfish binary found in archive %s", path)
            return path

        # Prefer .exe on Windows, no-extension on Unix; then pick largest
        if sys.platform == "win32":
            exe_files = [f for f in candidates if f.suffix == ".exe"]
            if exe_files:
                candidates = exe_files
        else:
            noext_files = [f for f in candidates if not f.suffix]
            if noext_files:
                candidates = noext_files

        best = max(candidates, key=lambda f: f.stat().st_size)
        exe_name = "stockfish.exe" if sys.platform == "win32" else "stockfish"
        exe_path = path.parent / exe_name

        shutil.move(str(best), str(exe_path))
        _make_executable(exe_path)

        logger.info("Extracted %s -> %s", best.name, exe_path)
        path.unlink(missing_ok=True)
        logger.info("Deleted archive: %s", path)

        return exe_path.resolve()

    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        logger.error("Extraction failed for %s: %s", path, exc)
        return path

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class StockfishDownloadManager:
    """Two-phase download manager for Stockfish engine binaries.

    **Phase 1 — Query** (:meth:`query_release`)
        Fetch release metadata from GitHub and determine which asset best
        matches the current system. Returns an :class:`AssetMatchResult` with
        the release tag, best asset (name/size/subarch), and all compatible
        assets. No files are downloaded.

    **Phase 2 — Download** (:meth:`download`)
        Write the chosen asset to disk. Progress is tracked via
        :meth:`get_progress` which the caller polls on the main thread
        to emit :class:`~utils.events.StockfishDownloadProgressEvent`.
    """

    def __init__(self):
        self._arch = get_sys_arch()
        self._platform = get_sys_platform()
        self._assets: list[StockfishAsset] = []
        self._release_tag: str = ""
        self._storage_dir: Path | None = None
        self._last_match: AssetMatchResult | None = None
        self._progress_downloaded: int = 0
        self._progress_total: int = 0
        self._progress_started: float = 0.0
        logger.info(
            "Initialized arch=%s platform=%s",
            self._arch.value,
            self._platform.value,
        )

    # ── Phase 1: Query ────────────────────────────────────────────────────

    def query_release(self) -> AssetMatchResult:
        """Fetch release info and return the best asset match for this system.

        This is the **query phase** — no file is downloaded. The result
        contains the release tag, the best-matching asset (name/size/subarch),
        and all compatible assets sorted by subarch priority.

        Raises:
            httpx.HTTPError: On network or API errors.
            RuntimeError: When no compatible asset exists for the current
                platform/architecture.
        """
        self._fetch_release()
        asset = self._find_best_asset()
        if asset is None:
            raise RuntimeError(
                f"No matching Stockfish asset for "
                f"{self._platform.value}/{self._arch.value}"
            )

        all_compatible = self._find_all_matching_assets()
        result = AssetMatchResult(
            release_tag=self._release_tag,
            best_asset=asset,
            all_compatible=tuple(all_compatible),
        )
        self._last_match = result
        logger.info(
            "Query result: tag=%s best=%s (%d bytes, %s)",
            result.release_tag,
            result.best_asset.name,
            result.best_asset.size_bytes,
            result.best_asset.subarch.value,
        )
        return result

    # ── Phase 2: Download ─────────────────────────────────────────────────

    def download(
        self,
        asset: StockfishAsset | None = None,
        dest_dir: Path | None = None,
    ) -> DownloadedAsset:
        """Download the given (or best-matching) asset to disk.

        Args:
            asset: The specific asset to download. If ``None``, uses the
                best asset from the last :meth:`query_release` call.
            dest_dir: Target directory. Defaults to :data:`STOCKFISH_DIR`
                (desktop) or the platform-appropriate path (mobile).

        Returns:
            A :class:`DownloadedAsset` with the resolved download path.

        Raises:
            RuntimeError: When no asset is specified and no query result exists.
            httpx.HTTPError: On download errors.
        """
        if asset is None:
            if self._last_match is None:
                raise RuntimeError(
                    "No asset specified and no prior query_release() result. "
                    "Call query_release() first or pass an asset explicitly."
                )
            asset = self._last_match.best_asset

        dest_dir = Path(dest_dir or self._storage_dir or STOCKFISH_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)

        existing = sorted(dest_dir.glob("stockfish*"))
        for f in existing:
            if f.stat().st_size > 0:
                cached = f.resolve()
                logger.info("Using cached Stockfish binary at %s", cached)
                return DownloadedAsset(
                    asset=asset,
                    download_path=cached,
                    downloaded_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                )
            logger.warning("Removing stale 0-byte cached file %s", f)
            f.unlink(missing_ok=True)

        dest = dest_dir / asset.name
        logger.info("Downloading %s (%d B) -> %s", asset.name, asset.size_bytes, dest)

        dest.parent.mkdir(parents=True, exist_ok=True)
        total = asset.size_bytes or 0
        self._progress_downloaded = 0
        self._progress_total = total
        self._progress_started = time.time()

        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            with client.stream("GET", asset.url, follow_redirects=True) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
                        self._progress_downloaded += len(chunk)

        _make_executable(dest)
        downloaded_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        result = DownloadedAsset(
            asset=asset,
            download_path=dest.resolve(),
            downloaded_at=downloaded_at,
        )
        logger.info("Downloaded %s (%d bytes)", dest.name, asset.size_bytes)
        return result

    # ── Async variants (zero-thread, runs on Flet event loop) ────────────

    async def query_release_async(self) -> AssetMatchResult:
        """Async fetch + match. Zero threads."""
        await self._fetch_release_async()
        asset = self._find_best_asset()
        if asset is None:
            raise RuntimeError(
                f"No matching Stockfish asset for "
                f"{self._platform.value}/{self._arch.value}"
            )
        all_compatible = self._find_all_matching_assets()
        result = AssetMatchResult(
            release_tag=self._release_tag,
            best_asset=asset,
            all_compatible=tuple(all_compatible),
        )
        self._last_match = result
        logger.info(
            "Query result: tag=%s best=%s (%d bytes, %s)",
            result.release_tag,
            result.best_asset.name,
            result.best_asset.size_bytes,
            result.best_asset.subarch.value,
        )
        return result

    async def download_async(
        self,
        asset: StockfishAsset | None = None,
        dest_dir: Path | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadedAsset:
        """Async download with progress callbacks.

        The actual download runs in a thread-pool thread via
        :meth:`_download_sync` so the Flet event loop never blocks.
        """
        if asset is None:
            if self._last_match is None:
                raise RuntimeError(
                    "No asset specified and no prior query_release() result. "
                    "Call query_release() first or pass an asset explicitly."
                )
            asset = self._last_match.best_asset

        dest_dir = Path(dest_dir or self._storage_dir or STOCKFISH_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)

        existing = sorted(dest_dir.glob("stockfish*"))
        for f in existing:
            if f.stat().st_size > 0:
                cached = f.resolve()
                logger.info("Using cached Stockfish binary at %s", cached)
                if progress_callback:
                    progress_callback(f.stat().st_size, f.stat().st_size)
                return DownloadedAsset(
                    asset=asset,
                    download_path=cached,
                    downloaded_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                )
            logger.warning("Removing stale 0-byte cached file %s", f)
            f.unlink(missing_ok=True)

        dest = dest_dir / asset.name
        logger.info(
            "Downloading %s (%d B) -> %s", asset.name, asset.size_bytes, dest
        )

        logger.info(
            "Delegating download to thread pool: %s -> %s",
            asset.url,
            dest,
        )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            self._download_sync,
            asset,
            dest_dir,
            progress_callback,
        )
        logger.info("Downloaded %s (%d bytes)", dest.name, asset.size_bytes)
        return result

    # ── Internal: async helpers ──────────────────────────────────────────

    async def _fetch_release_async(self) -> Self:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=httpx.Timeout(30.0)
        ) as client:
            resp = await client.get(_STOCKFISH_API)
            resp.raise_for_status()
            data = resp.json()
            self._release_tag = data.get("tag_name", "")
            raw_assets: list[dict] = data.get("assets", [])

            self._assets.clear()
            for raw in raw_assets:
                parsed = _parse_asset_name(raw["name"])
                if parsed is None:
                    logger.debug(
                        "Skipping unrecognised asset %s", raw["name"]
                    )
                    continue
                platform_val, arch_val, subarch_val = parsed
                self._assets.append(
                    StockfishAsset(
                        name=raw["name"],
                        url=raw.get("browser_download_url", ""),
                        size_bytes=raw.get("size", 0),
                        platform=platform_val,
                        arch=arch_val,
                        subarch=subarch_val,
                    )
                )
            logger.info(
                "Fetched %s — %d parseable assets",
                self._release_tag,
                len(self._assets),
            )
        return self

    # ── Progress ─────────────────────────────────────────────────────────

    def get_progress(self) -> tuple[int, int]:
        """Return (bytes_downloaded, total_bytes) for the current download."""
        return self._progress_downloaded, self._progress_total

    # ── Convenience ───────────────────────────────────────────────────────

    def ensure_stockfish(self, dest_dir: Path | None = None) -> Path | None:
        """Single-shot convenience: query + download + return path.

        Useful for non-UI contexts (tests, CLI) where the two-phase
        separation is unnecessary.

        Returns:
            The resolved binary path, or ``None`` if no matching asset
            could be found or downloaded.
        """
        try:
            self.query_release()
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.error("ensure_stockfish query failed: %s", exc)
            return None

        try:
            downloaded = self.download(dest_dir=dest_dir)
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.error("ensure_stockfish download failed: %s", exc)
            bus.emit(StockfishDownloadFailedEvent(error_message=str(exc)))
            return None

        return downloaded.download_path

    def set_storage_dir(self, path: Path) -> None:
        """Override the default storage directory."""
        self._storage_dir = path

    # ── Internal helpers ──────────────────────────────────────────────────

    def _fetch_release(self) -> Self:
        with httpx.Client(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
            resp = client.get(_STOCKFISH_API)
            resp.raise_for_status()
            data = resp.json()
        self._release_tag = data.get("tag_name", "")
        raw_assets: list[dict] = data.get("assets", [])

        self._assets.clear()
        for raw in raw_assets:
            parsed = _parse_asset_name(raw["name"])
            if parsed is None:
                logger.debug("Skipping unrecognised asset %s", raw["name"])
                continue
            platform_val, arch_val, subarch_val = parsed
            self._assets.append(
                StockfishAsset(
                    name=raw["name"],
                    url=raw.get("browser_download_url", ""),
                    size_bytes=raw.get("size", 0),
                    platform=platform_val,
                    arch=arch_val,
                    subarch=subarch_val,
                )
            )
        logger.info(
            "Fetched %s — %d parseable assets",
            self._release_tag,
            len(self._assets),
        )
        return self

    def _find_best_asset(self) -> StockfishAsset | None:
        candidates = [
            a
            for a in self._assets
            if a.platform == self._platform and a.arch == self._arch
        ]
        if not candidates:
            logger.warning(
                "No matching asset for %s/%s",
                self._platform.value,
                self._arch.value,
            )
            return None
        candidates.sort(
            key=lambda a: _SUBARCH_PRIORITY.get(a.subarch, 0),
            reverse=True,
        )
        best = candidates[0]
        logger.info(
            "Best asset: %s (subarch=%s, %d bytes)",
            best.name,
            best.subarch.value,
            best.size_bytes,
        )
        return best

    def _find_all_matching_assets(self) -> list[StockfishAsset]:
        candidates = [
            a
            for a in self._assets
            if a.platform == self._platform and a.arch == self._arch
        ]
        candidates.sort(
            key=lambda a: _SUBARCH_PRIORITY.get(a.subarch, 0),
            reverse=True,
        )
        return candidates

    # ── Synchronous download (runs in thread pool) ─────────────────────────
    # Uses httpx streaming so the calling thread blocks on network I/O but the
    # Flet event loop is never blocked — callers always offload to a thread.

    def _download_sync(
        self,
        asset: StockfishAsset,
        dest_dir: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadedAsset:
        """Download *asset* using httpx streaming.

        Runs entirely in the calling thread (usually a thread-pool thread).
        Progress is reported via *progress_callback* with ``(downloaded, total)``.
        """
        dest = dest_dir / asset.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        total = asset.size_bytes or 0
        self._progress_downloaded = 0
        self._progress_total = total
        self._progress_started = time.time()

        logger.info("Downloading %s -> %s", asset.url, dest)

        downloaded = 0
        with httpx.Client(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
            with client.stream("GET", asset.url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
                        downloaded += len(chunk)
                        self._progress_downloaded = downloaded
                        if progress_callback:
                            progress_callback(downloaded, total)

        logger.info("Download completed: %s (%d bytes)", dest.name, downloaded)

        _make_executable(dest)
        resolved = _resolve_archive(dest)
        return DownloadedAsset(
            asset=asset,
            download_path=resolved.resolve(),
            downloaded_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    # ── Public properties ─────────────────────────────────────────────────

    @property
    def assets(self) -> list[StockfishAsset]:
        """All parsed assets from the last fetch."""
        return list(self._assets)

    @property
    def release_tag(self) -> str:
        """GitHub release tag from the last fetch, e.g. ``"sf_17"``."""
        return self._release_tag

    @property
    def matched_arch(self) -> Arch:
        return self._arch

    @property
    def matched_platform(self) -> Platform:
        return self._platform

    @property
    def last_query(self) -> AssetMatchResult | None:
        """Result of the most recent :meth:`query_release` call, or ``None``."""
        return self._last_match

    @property
    def storage_dir(self) -> Path | None:
        """Current overridden storage directory, or ``None`` if default."""
        return self._storage_dir
    

if __name__ == "__main__":  # pragma: no cover
    manager = StockfishDownloadManager()
    print(manager.ensure_stockfish())