"""Tests for scripts/build_stockfish_android_pie.py (TDD).

Upstream Stockfish CI poisons its Android binaries with ``LDFLAGS="-static"``
(PGO-under-QEMU workaround), producing non-PIE ``ET_EXEC`` binaries that
modern Android refuses to execute. Our build must stay dynamically linked
(PIE, ``ET_DYN``). These tests pin the testable seams of the build script;
the actual NDK compilation itself runs in CI.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import build_stockfish_android_pie as build_pie  # noqa: E402


def test_resolve_all_abis():
    assert build_pie.resolve_abis("all") == ["arm64-v8a", "armeabi-v7a"]


def test_resolve_single_abi():
    assert build_pie.resolve_abis("arm64-v8a") == ["arm64-v8a"]


def test_resolve_unknown_abi_rejected():
    with pytest.raises(ValueError):
        build_pie.resolve_abis("x86_64")


def test_arm64_toolchain_uses_api29_clang():
    compiler, stockfish_arch = build_pie.toolchain_for_abi("arm64-v8a")

    assert compiler == "aarch64-linux-android29-clang++"
    assert stockfish_arch == "armv8"


def test_armv7_toolchain_uses_api29_clang():
    compiler, stockfish_arch = build_pie.toolchain_for_abi("armeabi-v7a")

    assert compiler == "armv7a-linux-androideabi29-clang++"
    assert stockfish_arch == "armv7-neon"


def test_build_command_is_dynamic_pie_not_static():
    cmd, env = build_pie.build_command(
        "arm64-v8a", ndk_bin="/opt/ndk/bin", source_dir=Path("/tmp/sf/src")
    )

    assert "COMP=ndk" in cmd
    assert "ARCH=armv8" in cmd
    assert "build" in cmd
    assert "profile-build" not in cmd
    # The poison: full static linking must never be requested. Note that
    # "-static-libstdc++" is fine and expected; only bare "-static" kills PIE.
    ldflags = env.get("EXTRALDFLAGS", "")
    assert " -static " not in f" {ldflags} "
    assert "-static-libstdc++" not in ldflags  # comes from Makefile default
    assert "max-page-size=16384" in ldflags  # Android 15 16KB-page rule


def test_build_command_runs_make_net_first_for_embedded_nnue():
    steps = build_pie.build_steps(
        "arm64-v8a", ndk_bin="/opt/ndk/bin", source_dir=Path("/tmp/sf/src")
    )

    assert steps[0][0] == "net"


def test_require_linux_rejects_non_linux():
    with pytest.raises(SystemExit):
        build_pie.require_platform("win32")


def test_require_linux_accepts_linux():
    build_pie.require_platform("linux")  # must not raise


def test_missing_ndk_bin_dir_is_a_clear_error(tmp_path):
    with pytest.raises(SystemExit):
        build_pie.require_ndk_bin(str(tmp_path / "no-such-ndk"))
