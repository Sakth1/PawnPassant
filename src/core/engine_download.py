from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
CHUNK_SIZE = 64 * 1024

ARCHIVE_EXTRACT_DIR = "extracted"


@dataclass
class EngineAsset:
    name: str
    url: str
    size: int
    sha256: str | None = None


@dataclass
class EngineDownloadConfig:
    github_repo: str
    asset_name_filter: str
    binary_name: str
    archive_binary_name: str
    archive_extra_files: dict[str, str | None] = field(default_factory=dict)
    label: str = ""
    description: str = ""


def _build_github_api_url(repo: str, endpoint: str) -> str:
    return f"{GITHUB_API}/repos/{repo}/{endpoint.lstrip('/')}"


def _github_api_get(url: str) -> dict | list:
    logger.debug("GitHub API GET %s", url)
    req = Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PawnPassant/1.0"})
    with urlopen(req, timeout=30) as resp:
        body = resp.read()
    return json.loads(body)


def _parse_sha256_from_body(body: str) -> str | None:
    for line in body.splitlines():
        line = line.strip()
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            try:
                int(parts[0], 16)
                return parts[0]
            except ValueError:
                continue
    return None


def _fetch_sha256(asset: EngineAsset) -> str | None:
    if asset.sha256:
        return asset.sha256
    checksum_name = asset.name.rsplit(".", 1)[0] + ".sha256"
    checksum_name_alt = asset.name + ".sha256"
    for candidate in [checksum_name, checksum_name_alt]:
        checksum_url = f"{asset.url.rsplit('/', 1)[0]}/{candidate}"
        try:
            req = Request(checksum_url, headers={"User-Agent": "PawnPassant/1.0"})
            with urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            sha = _parse_sha256_from_body(body)
            if sha:
                logger.debug("Found SHA256 for %s: %s", asset.name, sha)
                return sha
        except Exception as exc:
            logger.debug("No SHA256 found at %s: %s", checksum_url, exc)
    return None


def _release_from_api(data: dict | list) -> dict | None:
    if isinstance(data, list):
        for r in data:
            if not r.get("draft", False):
                return r
        return data[0] if data else None
    return data


def get_release_assets(config: EngineDownloadConfig) -> list[EngineAsset]:
    endpoint = "releases?per_page=5"
    url = _build_github_api_url(config.github_repo, endpoint)
    try:
        data = _github_api_get(url)
    except Exception as exc:
        logger.error("Failed to fetch releases: %s", exc)
        return []

    release = _release_from_api(data)
    if not release:
        logger.error("No suitable release found for %s", config.github_repo)
        return []

    tag = release.get("tag_name", "unknown")
    logger.info("Found release %s for %s", tag, config.github_repo)

    assets: list[EngineAsset] = []
    for a in release.get("assets", []):
        name = a.get("name", "")
        if config.asset_name_filter and config.asset_name_filter not in name:
            continue
        asset = EngineAsset(
            name=name,
            url=a["browser_download_url"],
            size=a.get("size", 0),
        )
        assets.append(asset)

    for asset in assets:
        asset.sha256 = _fetch_sha256(asset)

    return assets


def get_all_release_assets(repo: str) -> tuple[str, list[EngineAsset]]:
    endpoint = "releases?per_page=5"
    url = _build_github_api_url(repo, endpoint)
    try:
        data = _github_api_get(url)
    except Exception as exc:
        logger.error("Failed to fetch releases: %s", exc)
        return ("unknown", [])

    release = _release_from_api(data)
    if not release:
        return ("unknown", [])

    tag = release.get("tag_name", "unknown")
    logger.info("Found release %s for %s", tag, repo)

    assets: list[EngineAsset] = []
    for a in release.get("assets", []):
        name = a.get("name", "")
        asset = EngineAsset(
            name=name,
            url=a["browser_download_url"],
            size=a.get("size", 0),
        )
        assets.append(asset)

    for asset in assets:
        asset.sha256 = _fetch_sha256(asset)

    return tag, assets


def get_all_platform_assets(configs: list[EngineDownloadConfig]) -> dict[str, list[EngineAsset]]:
    result: dict[str, list[EngineAsset]] = {}
    seen_repos: set[str] = set()
    for cfg in configs:
        if cfg.github_repo in seen_repos:
            continue
        seen_repos.add(cfg.github_repo)
        _, all_assets = get_all_release_assets(cfg.github_repo)
        for other_cfg in configs:
            if other_cfg.github_repo != cfg.github_repo:
                continue
            filtered = [a for a in all_assets if other_cfg.asset_name_filter in a.name]
            if filtered:
                result[other_cfg.asset_name_filter] = filtered
    return result


def download_asset(
    asset: EngineAsset,
    dest: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    logger.info("Downloading %s -> %s", asset.url, dest)

    req = Request(asset.url, headers={"User-Agent": "PawnPassant/1.0"})
    with urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get("Content-Length", asset.size))
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

    if asset.sha256:
        calc = hashlib.sha256()
        with open(tmp, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                calc.update(chunk)
        if calc.hexdigest() != asset.sha256:
            tmp.unlink()
            raise ValueError(
                f"SHA256 mismatch for {asset.name}: "
                f"expected {asset.sha256}, got {calc.hexdigest()}"
            )
        logger.info("SHA256 verified for %s", asset.name)

    shutil.move(str(tmp), str(dest))
    logger.info("Downloaded %s (%d bytes)", asset.name, dest.stat().st_size)
    return dest


def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
    calc = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            calc.update(chunk)
    return calc.hexdigest() == expected_sha256


def _is_apk(path: Path) -> bool:
    return path.suffix.lower() == ".apk"


def _is_zip(path: Path) -> bool:
    return path.suffix.lower() in {".zip", ".apk"}


def _is_targz(path: Path) -> bool:
    return path.suffix.lower() in {".gz", ".tgz"} or str(path).endswith(".tar.gz")


def _is_tar(path: Path) -> bool:
    return path.suffix.lower() == ".tar" and not _is_targz(path)


def _is_archive(path: Path) -> bool:
    return _is_zip(path) or _is_targz(path) or _is_tar(path)


def _normalise_archive_entry_name(entry_name: str) -> str:
    return Path(entry_name).name


def _find_entry_in_zip(zf: zipfile.ZipFile, target_name: str) -> str | None:
    target_basename = Path(target_name).name
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        if Path(name).name == target_basename:
            return name
    return None


def _find_entry_in_tar(tf: tarfile.TarFile, target_name: str) -> str | None:
    target_basename = Path(target_name).name
    for member in tf.getmembers():
        if not member.isfile():
            continue
        if Path(member.name).name == target_basename:
            return member.name
    return None


def _find_entry_zip(zf: zipfile.ZipFile, name: str) -> str | None:
    if name in zf.namelist():
        return name
    return _find_entry_in_zip(zf, name)


def _find_entry_tar(tf: tarfile.TarFile, name: str) -> str | None:
    try:
        tf.getmember(name)
        return name
    except KeyError:
        pass
    return _find_entry_in_tar(tf, name)


def extract_archive(
    archive_path: Path,
    config: EngineDownloadConfig,
    dest_dir: Path,
) -> dict[str, Path]:
    extracted: dict[str, Path] = {}
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not _is_archive(archive_path):
        raise ValueError(f"Unsupported archive format: {archive_path.suffix}")

    if _is_zip(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            if config.archive_extra_files:
                for internal_name, rename in config.archive_extra_files.items():
                    _extract_zip_entry(zf, internal_name, dest_dir, rename, extracted)
                _extract_zip_entry(zf, config.archive_binary_name, dest_dir, config.binary_name, extracted)
            else:
                _extract_all_zip(zf, dest_dir, config.binary_name, extracted)
    elif _is_targz(archive_path):
        with tarfile.open(archive_path, "r:gz") as tf:
            if config.archive_extra_files:
                for internal_name, rename in config.archive_extra_files.items():
                    _extract_tar_entry(tf, internal_name, dest_dir, rename, extracted)
                _extract_tar_entry(tf, config.archive_binary_name, dest_dir, config.binary_name, extracted)
            else:
                _extract_all_tar(tf, dest_dir, config.binary_name, extracted)
    elif _is_tar(archive_path):
        with tarfile.open(archive_path, "r:") as tf:
            if config.archive_extra_files:
                for internal_name, rename in config.archive_extra_files.items():
                    _extract_tar_entry(tf, internal_name, dest_dir, rename, extracted)
                _extract_tar_entry(tf, config.archive_binary_name, dest_dir, config.binary_name, extracted)
            else:
                _extract_all_tar(tf, dest_dir, config.binary_name, extracted)

    if config.binary_name not in extracted:
        prefix = config.binary_name + "-"
        for key in list(extracted):
            if key.startswith(prefix):
                src = extracted[key]
                dst = src.parent / config.binary_name
                if dst.exists():
                    dst.unlink()
                shutil.copy2(src, dst)
                _make_executable(dst)
                src.unlink()
                extracted[config.binary_name] = dst
                del extracted[key]
                break

    if config.binary_name not in extracted:
        raise FileNotFoundError(
            f"Binary '{config.binary_name}' not found in archive {archive_path.name}. "
            f"Extracted: {list(extracted.keys())}"
        )

    return extracted


def _extract_zip_entry(
    zf: zipfile.ZipFile,
    internal_name: str,
    dest_dir: Path,
    rename: str | None,
    extracted: dict[str, Path],
) -> None:
    entry = _find_entry_zip(zf, internal_name)
    if entry is None:
        logger.warning("Entry '%s' not found in ZIP archive", internal_name)
        return
    target_name = rename or Path(entry).name
    target_path = dest_dir / target_name
    with zf.open(entry) as src:
        with open(target_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    _make_executable(target_path)
    extracted[target_name] = target_path
    logger.debug("Extracted %s -> %s", entry, target_path)


def _extract_tar_entry(
    tf: tarfile.TarFile,
    internal_name: str,
    dest_dir: Path,
    rename: str | None,
    extracted: dict[str, Path],
) -> None:
    entry = _find_entry_tar(tf, internal_name)
    if entry is None:
        logger.warning("Entry '%s' not found in tar archive", internal_name)
        return
    target_name = rename or Path(entry).name
    target_path = dest_dir / target_name
    member = tf.getmember(entry)
    with tf.extractfile(member) as src:
        if src is None:
            logger.warning("Could not extract '%s' (not a regular file)", entry)
            return
        with open(target_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    _make_executable(target_path)
    extracted[target_name] = target_path
    logger.debug("Extracted %s -> %s", entry, target_path)


def _extract_all_zip(
    zf: zipfile.ZipFile,
    dest_dir: Path,
    binary_name: str,
    extracted: dict[str, Path],
) -> None:
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        target_name = Path(name).name
        target_path = dest_dir / target_name
        with zf.open(name) as src, open(target_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        _make_executable(target_path)
        extracted[target_name] = target_path
        logger.debug("Extracted %s -> %s", name, target_path)


def _extract_all_tar(
    tf: tarfile.TarFile,
    dest_dir: Path,
    binary_name: str,
    extracted: dict[str, Path],
) -> None:
    for member in tf.getmembers():
        if not member.isfile():
            continue
        target_name = Path(member.name).name
        target_path = dest_dir / target_name
        with tf.extractfile(member) as src:
            if src is None:
                continue
            with open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
        _make_executable(target_path)
        extracted[target_name] = target_path
        logger.debug("Extracted %s -> %s", member.name, target_path)


def _make_executable(path: Path) -> None:
    try:
        current = path.stat().st_mode
        path.chmod(current | 0o111)
    except OSError:
        pass


def download_and_extract(
    asset: EngineAsset,
    config: EngineDownloadConfig,
    dest_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Path]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="pawnpassant_dl_"))
    try:
        archive_path = tmp_dir / asset.name
        download_asset(asset, archive_path, progress_callback=progress_callback)
        return extract_archive(archive_path, config, dest_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
