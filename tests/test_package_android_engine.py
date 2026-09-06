"""Tests for scripts/package_android_engine.py (TDD).

The NDK-built PIE binaries (``libstockfish.so`` per ABI) must reach the
APK's ``lib/<abi>/`` directory. Per Flet ≥0.86.2, the supported vehicle is
a minimal platform wheel per ABI (a package folder containing the ``.so``),
installed as an app dependency before ``flet build``.
"""

import struct
import sys
import zipfile
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import package_android_engine as pack  # noqa: E402


def _write_minimal_elf(path: Path, *, e_type: int, e_machine: int) -> None:
    header = bytearray(64)
    header[0:4] = b"\x7fELF"
    header[4] = 2
    header[5] = 1
    struct.pack_into("<H", header, 16, e_type)
    struct.pack_into("<H", header, 18, e_machine)
    path.write_bytes(bytes(header))


def test_abi_to_wheel_tag():
    assert pack.wheel_tag_for_abi("arm64-v8a") == "android_24_arm64_v8a"
    assert pack.wheel_tag_for_abi("armeabi-v7a") == "android_24_armeabi_v7a"


def test_dist_name_for_abi():
    assert (
        pack.dist_name_for_abi("arm64-v8a")
        == "pawnpassant-stockfish-android-arm64"
    )
    assert (
        pack.dist_name_for_abi("armeabi-v7a")
        == "pawnpassant-stockfish-android-armv7"
    )


def test_build_wheel_contains_soname(tmp_path):
    staged = tmp_path / "dist" / "arm64-v8a" / "libstockfish.so"
    staged.parent.mkdir(parents=True)
    _write_minimal_elf(staged, e_type=3, e_machine=183)  # ET_DYN, AArch64
    outdir = tmp_path / "wheels"

    wheel = pack.build_wheel("arm64-v8a", staged, outdir, version="19.0.0")

    assert wheel.exists()
    assert wheel.suffix == ".whl"
    assert "android_24_arm64_v8a" in wheel.name
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    assert "pawnpassant_stockfish/libstockfish.so" in names
    assert any(n.endswith(".dist-info/METADATA") for n in names)


def test_build_wheel_gates_non_pie_binary(tmp_path):
    staged = tmp_path / "dist" / "arm64-v8a" / "libstockfish.so"
    staged.parent.mkdir(parents=True)
    _write_minimal_elf(staged, e_type=2, e_machine=183)  # ET_EXEC: upstream poison

    try:
        pack.build_wheel("arm64-v8a", staged, tmp_path / "wheels", version="19.0.0")
    except SystemExit:
        return
    raise AssertionError("non-PIE binary must be refused packaging")


def test_build_wheel_rejects_missing_binary(tmp_path):
    try:
        pack.build_wheel(
            "arm64-v8a",
            tmp_path / "nope" / "libstockfish.so",
            tmp_path / "wheels",
            version="19.0.0",
        )
    except SystemExit:
        return
    raise AssertionError("missing binary must fail loudly")
