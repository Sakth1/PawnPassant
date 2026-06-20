"""Standalone download worker for Stockfish binary.

Spawned as a subprocess by the Flet app so the main Python process
stays responsive to Flet heartbeats during large downloads.

Usage:
    python download_asset.py <url> <dest_path> <status_file>
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import requests

CHUNK_SIZE = 8192
PROGRESS_INTERVAL = 100 * 1024


def _write_status(filepath: str, **kw: object) -> None:
    with open(filepath, "w") as f:
        json.dump(kw, f)


def main() -> None:
    url = sys.argv[1]
    dest_path = sys.argv[2]
    status_file = sys.argv[3]

    dest_dir = os.path.dirname(dest_path)
    os.makedirs(dest_dir, exist_ok=True)

    fd, tmp_path_str = tempfile.mkstemp(
        dir=dest_dir,
        prefix=".stockfish_",
        suffix=".part",
    )
    os.close(fd)
    tmp_path = tmp_path_str

    error: Exception | None = None
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        last_report = 0

        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)

                if downloaded - last_report >= PROGRESS_INTERVAL:
                    _write_status(
                        status_file,
                        downloaded=downloaded,
                        total=total,
                        done=False,
                    )
                    last_report = downloaded

        os.replace(tmp_path, dest_path)
        tmp_path = None

        _write_status(
            status_file,
            done=True,
            dest_path=dest_path,
            downloaded=total,
            total=total,
        )

    except Exception as exc:
        error = exc
        _write_status(status_file, error=str(exc))

    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if error:
        sys.exit(1)


if __name__ == "__main__":
    main()
