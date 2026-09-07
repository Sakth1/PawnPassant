"""Wrap NDK-built PIE Stockfish binaries as Android platform wheels.

``scripts/build_stockfish_android_pie.py`` produces
``<dist>/​<android-abi>/libstockfish.so``. This script gates each binary
through the ELF PIE check and wraps it in a minimal platform wheel per ABI::

    python scripts/package_android_engine.py --dist dist/stockfish-android \\
        --outdir dist/wheels --version 19.0.0

Install the wheel matching the device ABI before ``flet build`` (Flet
≥0.86.2 places its ``.so`` into the APK's ``lib/<abi>/`` keeping the
soname). With ``legacy_packaging`` the OS extracts it to
``ANDROID_NATIVE_LIBRARY_DIR``, the only executable location on
Android 10+.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ABI_WHEEL_TAG: dict[str, str] = {
    "arm64-v8a": "android_24_arm64_v8a",
    "armeabi-v7a": "android_24_armeabi_v7a",
    "x86_64": "android_24_x86_64",
}

ABI_DIST_SUFFIX: dict[str, str] = {
    "arm64-v8a": "arm64",
    "armeabi-v7a": "armv7",
    "x86_64": "x86_64",
}

ABI_EXPECTED_MACHINE: dict[str, int] = {
    # ELF e_machine: 183 = AArch64, 40 = ARM, 62 = x86-64.
    "arm64-v8a": 183,
    "armeabi-v7a": 40,
    "x86_64": 62,
}

PACKAGE_DIR = "pawnpassant_stockfish"
SONAME = "libstockfish.so"


def wheel_tag_for_abi(abi: str) -> str:
    return ABI_WHEEL_TAG[abi]


def dist_name_for_abi(abi: str) -> str:
    return f"pawnpassant-stockfish-android-{ABI_DIST_SUFFIX[abi]}"


def _gate_binary(binary: Path, abi: str) -> None:
    if not binary.is_file():
        print(f"ERROR: PIE binary not found: {binary}", file=sys.stderr)
        raise SystemExit(1)
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root / "src") not in sys.path:
        sys.path.insert(0, str(repo_root / "src"))
    from core.engine_verify import check_android_binary

    ok, reason = check_android_binary(
        str(binary), expected_machine=ABI_EXPECTED_MACHINE[abi]
    )
    if not ok:
        print(
            f"ERROR: refusing to package {abi} binary ({binary}): {reason}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def build_wheel(abi: str, binary: Path, outdir: Path, version: str) -> Path:
    """Gate + wrap one ABI binary; return the wheel path."""
    _gate_binary(binary, abi)
    outdir.mkdir(parents=True, exist_ok=True)
    dist_name = dist_name_for_abi(abi)
    wheel_name = (
        f"{dist_name.replace('-', '_')}-{version}-py3-none-{wheel_tag_for_abi(abi)}.whl"
    )
    wheel_path = outdir / wheel_name
    dist_info = f"{dist_name.replace('-', '_')}-{version}.dist-info"
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{PACKAGE_DIR}/__init__.py", "")
        with open(binary, "rb") as f:
            zf.writestr(f"{PACKAGE_DIR}/{SONAME}", f.read())
        zf.writestr(
            f"{dist_info}/METADATA",
            f"Metadata-Version: 2.1\nName: {dist_name}\nVersion: {version}\n",
        )
        zf.writestr(
            f"{dist_info}/WHEEL",
            "Wheel-Version: 1.0\nGenerator: pawnpassant-package-android-engine\n"
            "Root-Is-Purelib: false\n"
            f"Tag: py3-none-{wheel_tag_for_abi(abi)}\n",
        )
    print(f"  -> {wheel_path} ({wheel_path.stat().st_size} bytes)")
    return wheel_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Wrap PIE engine binaries as wheels")
    parser.add_argument(
        "--dist", required=True,
        help="Input dir from build_stockfish_android_pie.py (<abi>/libstockfish.so)",
    )
    parser.add_argument("--outdir", default="dist/wheels")
    parser.add_argument(
        "--version", default="0.0.0", help="Wheel version (PEP 440, e.g. 19.0.0)"
    )
    parser.add_argument(
        "--abi", default="all", choices=[*ABI_WHEEL_TAG, "all"],
    )
    args = parser.parse_args()

    dist = Path(args.dist)
    outdir = Path(args.outdir)
    abis = list(ABI_WHEEL_TAG) if args.abi == "all" else [args.abi]
    for abi in abis:
        print(f"=== Packaging {abi} ===")
        build_wheel(abi, dist / abi / SONAME, outdir, args.version)


if __name__ == "__main__":
    main()
