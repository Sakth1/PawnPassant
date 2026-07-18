"""Download Stockfish Android binaries from latest dev prerelease.

Official release builds use static linking (non-PIE) which is rejected by
modern Android. Dev builds (post PR #6081) use dynamic linking and produce
PIE-compatible executables.

Downloads and extracts the arm64-v8a and armeabi-v7a binaries into
bundled/stockfish/android/<abi>/stockfish.

Usage:
    python scripts/fetch_stockfish_android.py [--abi arm64-v8a|armeabi-v7a|all]

Default: all
"""
import argparse
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

GITHUB_API_LIST = "https://api.github.com/repos/official-stockfish/Stockfish/releases?per_page=10"

ASSET_MAP = {
    "arm64-v8a": "stockfish-android-arm64-universal.tar.gz",
    "armeabi-v7a": "stockfish-android-armv7-neon.tar.gz",
}

BUNDLED_ROOT = Path(__file__).resolve().parent.parent / "bundled" / "stockfish" / "android"


def _api_get(url: str) -> list | dict:
    req = Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PawnPassant/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _latest_prerelease(data: list) -> dict | None:
    for r in data:
        if r.get("prerelease", False) and not r.get("draft", False):
            return r
    return None


def _find_asset(release: dict, name_filter: str) -> str | None:
    for a in release.get("assets", []):
        if a["name"] == name_filter:
            return a["browser_download_url"]
    return None


def download_and_extract(abi: str, url: str) -> None:
    print(f"Downloading {abi}...")
    with tempfile.TemporaryDirectory(prefix="stockfish_") as tmp:
        tar_path = Path(tmp) / f"{abi}.tar.gz"
        req = Request(url, headers={"User-Agent": "PawnPassant/1.0"})
        with urlopen(req, timeout=300) as resp:
            with open(tar_path, "wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir()
        with tarfile.open(tar_path, "r:gz") as tf:
            tf.extractall(str(extract_dir))

        binary_candidates = list(extract_dir.rglob("stockfish*"))
        if not binary_candidates:
            raise FileNotFoundError(f"No stockfish binary found in {abi} archive")
        binary = binary_candidates[0]

        dest_dir = BUNDLED_ROOT / abi
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "stockfish"
        shutil.copy2(str(binary), str(dest))
        dest.chmod(dest.stat().st_mode | 0o111)
        print(f"  -> {dest} ({dest.stat().st_size} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Download Stockfish Android binaries")
    parser.add_argument("--abi", default="all", choices=["arm64-v8a", "armeabi-v7a", "all"])
    args = parser.parse_args()

    data = _api_get(GITHUB_API_LIST)
    if not isinstance(data, list):
        print("ERROR: Expected a list from releases endpoint", file=sys.stderr)
        return 1

    release = _latest_prerelease(data)
    if not release:
        print("ERROR: No prerelease found among recent releases", file=sys.stderr)
        return 1

    tag = release.get("tag_name", "unknown")
    print(f"Latest dev build: {tag}")

    abis = ["arm64-v8a", "armeabi-v7a"] if args.abi == "all" else [args.abi]

    for abi in abis:
        asset_name = ASSET_MAP[abi]
        url = _find_asset(release, asset_name)
        if not url:
            print(f"ERROR: Asset {asset_name} not found in release {tag}", file=sys.stderr)
            continue
        download_and_extract(abi, url)


if __name__ == "__main__":
    sys.exit(main() or 0)
