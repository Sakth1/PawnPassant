"""Tests for scripts/inject_android_engine.py (TDD).

Wheels cannot reach the APK through pip: serious_python configures pip
for a single ABI, so the sibling-arch wheel hard-fails the build
("not a supported wheel on this platform"). Instead the NDK-built
``libstockfish.so`` files are injected straight into the built APKs'
``lib/<abi>/`` dirs just before zipalign/apksigner run (our pipeline
signs last, so injection never invalidates a signature).
"""

import sys
import zipfile
from pathlib import Path

import pytest

SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import inject_android_engine as inject  # noqa: E402


def _make_apk(path: Path, abis: list[str]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AndroidManifest.xml", b"<manifest/>")
        for abi in abis:
            zf.writestr(f"lib/{abi}/libflutter.so", b"flutter-" + abi.encode())


def _apk_entries(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def test_detects_apk_abis(tmp_path):
    apk = tmp_path / "app-arm64.apk"
    _make_apk(apk, ["arm64-v8a"])

    assert inject.detect_apk_abis(apk) == ["arm64-v8a"]


def test_injects_matching_engine_binary(tmp_path):
    apk = tmp_path / "app-arm64.apk"
    _make_apk(apk, ["arm64-v8a", "x86_64"])
    arm64_lib = tmp_path / "arm64-v8a" / "libstockfish.so"
    arm64_lib.parent.mkdir()
    arm64_lib.write_bytes(b"arm64-pie")
    x86_lib = tmp_path / "x86_64" / "libstockfish.so"
    x86_lib.parent.mkdir()
    x86_lib.write_bytes(b"x86-pie")

    injected = inject.inject_engine(apk, tmp_path)

    assert injected == ["arm64-v8a", "x86_64"]
    with zipfile.ZipFile(apk) as zf:
        assert zf.read("lib/arm64-v8a/libstockfish.so") == b"arm64-pie"
        assert zf.read("lib/x86_64/libstockfish.so") == b"x86-pie"


def test_apk_without_matching_lib_is_left_alone(tmp_path):
    apk = tmp_path / "app.apk"
    _make_apk(apk, ["x86_64"])

    injected = inject.inject_engine(apk, tmp_path)

    assert injected == []
    assert "lib/x86_64/libstockfish.so" not in _apk_entries(apk)


def test_apk_with_no_lib_dir_fails_loudly(tmp_path):
    apk = tmp_path / "app.apk"
    with zipfile.ZipFile(apk, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"<manifest/>")

    with pytest.raises(SystemExit):
        inject.inject_engine(apk, tmp_path)


def test_injected_so_is_stored_compressed_for_legacy_packaging(tmp_path):
    apk = tmp_path / "app-arm64.apk"
    _make_apk(apk, ["arm64-v8a"])
    arm64_lib = tmp_path / "arm64-v8a" / "libstockfish.so"
    arm64_lib.parent.mkdir()
    arm64_lib.write_bytes(b"arm64-pie" * 1000)

    inject.inject_engine(apk, tmp_path)

    with zipfile.ZipFile(apk) as zf:
        info = zf.getinfo("lib/arm64-v8a/libstockfish.so")
    assert info.compress_type == zipfile.ZIP_DEFLATED


def test_main_fails_when_nothing_injected_anywhere(tmp_path, monkeypatch, capsys):
    apk = tmp_path / "app.apk"
    _make_apk(apk, ["x86_64"])  # no matching engine binary staged
    monkeypatch.setattr(
        sys,
        "argv",
        ["inject_android_engine.py", "--apk", str(apk), "--libdir", str(tmp_path)],
    )

    with pytest.raises(SystemExit) as exc_info:
        inject.main()

    assert exc_info.value.code != 0
    assert "no engine binary injected" in capsys.readouterr().out.lower()
