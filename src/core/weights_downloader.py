from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from core.lc0_config import DEFAULT_NETWORKS, NetworkInfo

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024
WEIGHTS_DIR_NAME = "lc0_weights"
WEIGHTS_INDEX_URL = "https://lczero.org/networks/api/"
CACHE_INDEX_FILE = "network_index.json"


@dataclass
class CachedNetwork:
    name: str
    url: str
    sha256: str
    size_bytes: int
    local_path: str
    downloaded_at: str


def _fetch_network_index() -> dict | None:
    try:
        req = Request(WEIGHTS_INDEX_URL, headers={"User-Agent": "PawnPassant/1.0"})
        with urlopen(req, timeout=30) as resp:
            body = resp.read()
        return json.loads(body)
    except Exception as exc:
        logger.warning("Failed to fetch network index: %s", exc)
        return None


def _resolve_weights_dir(cache_dir: Path) -> Path:
    weights_dir = cache_dir / WEIGHTS_DIR_NAME
    weights_dir.mkdir(parents=True, exist_ok=True)
    return weights_dir


def get_available_networks(cache_dir: Path | None = None) -> list[NetworkInfo]:
    networks = list(DEFAULT_NETWORKS)

    index = _fetch_network_index()
    if index:
        for entry in index:
            name = entry.get("name", "")
            url = entry.get("url", "")
            sha256 = entry.get("sha256", "")
            size = entry.get("size", 0)
            desc = entry.get("description", "")
            if name and url:
                networks.append(NetworkInfo(
                    name=name,
                    url=url,
                    sha256=sha256,
                    size_bytes=size,
                    description=desc,
                ))

    seen = set()
    deduped = []
    for n in networks:
        if n.name not in seen:
            seen.add(n.name)
            deduped.append(n)
    return deduped


def download_network(
    network: NetworkInfo,
    cache_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    weights_dir = _resolve_weights_dir(cache_dir)
    dest = weights_dir / network.name

    if dest.exists() and dest.stat().st_size == network.size_bytes and network.sha256:
        if verify_sha256(dest, network.sha256):
            logger.info("Using cached weights: %s", dest)
            return dest

    tmp = dest.with_suffix(dest.suffix + ".part")
    logger.info("Downloading weights %s -> %s", network.url, dest)

    req = Request(network.url, headers={"User-Agent": "PawnPassant/1.0"})
    with urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get("Content-Length", network.size_bytes))
        downloaded = 0
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)

    if network.sha256:
        calc = hashlib.sha256()
        with open(tmp, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                calc.update(chunk)
        if calc.hexdigest() != network.sha256:
            tmp.unlink()
            raise ValueError(
                f"SHA256 mismatch for {network.name}: "
                f"expected {network.sha256}, got {calc.hexdigest()}"
            )

    tmp.rename(dest)
    logger.info("Downloaded weights %s (%d bytes)", network.name, dest.stat().st_size)
    return dest


def get_cached_networks(cache_dir: Path) -> list[CachedNetwork]:
    weights_dir = _resolve_weights_dir(cache_dir)
    cached: list[CachedNetwork] = []
    for f in sorted(weights_dir.iterdir()):
        if f.is_file() and not f.name.startswith(".") and f.name != CACHE_INDEX_FILE:
            cached.append(CachedNetwork(
                name=f.name,
                url="",
                sha256="",
                size_bytes=f.stat().st_size,
                local_path=str(f),
                downloaded_at="",
            ))
    return cached


def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
    calc = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            calc.update(chunk)
    return calc.hexdigest() == expected_sha256
