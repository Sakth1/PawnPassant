from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_android() -> bool:
    return "ANDROID_ROOT" in os.environ


def _find_linker() -> str | None:
    for c in ["/system/bin/linker64", "/system/bin/linker"]:
        if os.path.exists(c):
            return c
    return None


def _verify_via_linker(linker: str, path: str) -> tuple[bool, str]:
    try:
        proc = subprocess.Popen(
            [linker, path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _ = proc.communicate(input="uci\nquit\n", timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("Linker/UCI verification failed for %s: %s", path, exc, exc_info=True)
        return False, f"Linker error: {exc}"
    for line in stdout.splitlines():
        if line.startswith("id name Stockfish"):
            return True, line.strip()
    return False, "No version string found in linker output."


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
        logger.error("Binary not found when executing path=%s", path, exc_info=True)
        return False, "Executable not found."
    except subprocess.TimeoutExpired:
        logger.error("Binary execution timed out path=%s", path, exc_info=True)
        return False, "Binary execution timed out."
    except OSError as exc:
        if _is_android():
            linker = _find_linker()
            if linker:
                logger.info("Retrying via Android linker linker=%s path=%s", linker, path)
                return _verify_via_linker(linker, path)
        logger.error("OS error running binary path=%s error=%s", path, exc, exc_info=True)
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
