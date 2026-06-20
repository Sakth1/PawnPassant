from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def verify_stockfish_binary(path: str) -> tuple[bool, str]:
    """Verify that the given path points to a valid Stockfish executable.

    Returns:
        A tuple of ``(valid, version_string_or_error)``.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("Binary not found at path=%s", path)
        return False, "File not found."
    if not p.is_file():
        logger.warning("Path is not a file path=%s", path)
        return False, "Not a file."

    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        logger.error("Binary not found when executing path=%s", path)
        return False, "Executable not found."
    except subprocess.TimeoutExpired:
        logger.error("Binary execution timed out path=%s", path)
        return False, "Binary execution timed out."
    except OSError as exc:
        logger.error("OS error running binary path=%s error=%s", path, exc)
        return False, f"OS error: {exc}"

    output = (result.stdout or "") + "\n" + (result.stderr or "")
    for line in output.splitlines():
        if "Stockfish" in line:
            version = line.strip()
            logger.info(
                "Verified Stockfish binary version=%s path=%s", version, path
            )
            return True, version

    logger.warning(
        "Binary executed but no version string found path=%s output=%s",
        path,
        output[:200],
    )
    return False, "No version string found in output."
