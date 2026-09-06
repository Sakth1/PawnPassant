"""Inject NDK-built Stockfish binaries into built APKs' lib/<abi>/ dirs.

Wheels cannot reach the APK through pip: serious_python configures pip
for a single ABI, so any sibling-arch wheel hard-fails the build with
"not a supported wheel on this platform". Instead this script copies the
already ELF-gated ``libstockfish.so`` files straight into each APK:

    python scripts/inject_android_engine.py --apk app.apk --libdir dist/stockfish-android

``--libdir`` mirrors the build script layout: ``<android-abi>/libstockfish.so``.
APK ABIs are detected from the APK's own ``lib/<abi>/`` entries, so each
(split-)APK gets exactly its matching binary. Entries are stored
compressed: with ``legacy_packaging`` the installer extracts them to
``ANDROID_NATIVE_LIBRARY_DIR`` at install time. Must run BEFORE
zipalign/apksigner (our pipeline signs last).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

SONAME = "libstockfish.so"


def detect_apk_abis(apk: Path) -> list[str]:
    """ABIs present in the APK, read from its own lib/<abi>/ entries."""
    abis: list[str] = []
    with zipfile.ZipFile(apk) as zf:
        for name in zf.namelist():
            parts = name.split("/")
            if len(parts) >= 3 and parts[0] == "lib" and parts[1] not in abis:
                abis.append(parts[1])
    return abis


def inject_engine(apk: Path, libdir: Path) -> list[str]:
    """Inject matching engine binaries into the APK. Returns injected ABIs."""
    abis = detect_apk_abis(apk)
    if not abis:
        print(f"ERROR: no lib/<abi>/ entries in {apk}", file=sys.stderr)
        raise SystemExit(1)
    injected: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pawnpassant_apk_") as tmp:
        staged = Path(tmp) / apk.name
        shutil.copy2(str(apk), str(staged))
        with zipfile.ZipFile(staged, "a", zipfile.ZIP_DEFLATED) as zf:
            for abi in abis:
                binary = libdir / abi / SONAME
                if not binary.is_file():
                    print(f"  [{abi}] no engine binary at {binary}, skipping")
                    continue
                entry = f"lib/{abi}/{SONAME}"
                if entry in zf.namelist():
                    print(f"  [{abi}] replacing existing {entry}")
                else:
                    print(f"  [{abi}] adding {entry}")
                zf.write(str(binary), entry, compress_type=zipfile.ZIP_DEFLATED)
                injected.append(abi)
        shutil.copy2(str(staged), str(apk))
    return injected


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject engine .so files into APKs")
    parser.add_argument("--apk", required=True, action="append", help="APK file (repeatable)")
    parser.add_argument(
        "--libdir", required=True,
        help="Engine lib dir (<android-abi>/libstockfish.so layout)",
    )
    args = parser.parse_args()

    total = 0
    for apk_str in args.apk:
        apk = Path(apk_str)
        print(f"=== {apk} ===")
        injected = inject_engine(apk, Path(args.libdir))
        total += len(injected)
        if not injected:
            print(
                f"WARNING: no engine binary injected into {apk} "
                f"(APK ABIs: {detect_apk_abis(apk)})",
            )
    if total == 0:
        print("ERROR: no engine binary injected into any APK", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
