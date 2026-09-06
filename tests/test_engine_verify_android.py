"""Android PIE packaging-gate tests (TDD).

Upstream Stockfish release/dev binaries are statically linked ``ET_EXEC``
and cannot run on modern Android. Our APK must therefore bundle a
self-built position-independent (``ET_DYN``) binary. This gate validates an
Android-bound binary on any host OS (e.g. a Linux CI runner) purely from
its ELF headers — without executing it.
"""

import platform
import struct

from core import engine_verify


def _write_minimal_elf(path, *, e_type: int, e_machine: int) -> None:
    header = bytearray(64)
    header[0:4] = b"\x7fELF"
    header[4] = 2  # ELFCLASS64
    header[5] = 1  # ELFDATA2LSB
    struct.pack_into("<H", header, 16, e_type)
    struct.pack_into("<H", header, 18, e_machine)
    # e_phoff / e_phentsize / e_phnum left zero: no program headers,
    # so interpreter is None and needed-libs is [].
    path.write_bytes(bytes(header))


def _host_machine() -> int:
    machine = platform.machine().lower()
    if "64" in machine and ("arm" in machine or "aarch64" in machine):
        return engine_verify.EM_AARCH64
    if "arm" in machine:
        return engine_verify.EM_ARM
    if "64" in machine:
        return engine_verify.EM_X86_64
    return engine_verify.EM_386


def test_rejects_non_pie_android_binary(tmp_path):
    binary = tmp_path / "stockfish"
    _write_minimal_elf(
        binary, e_type=engine_verify.ET_EXEC, e_machine=_host_machine()
    )

    ok, reason = engine_verify.check_android_binary(str(binary))

    assert ok is False
    assert "PIE" in reason


def test_accepts_pie_android_binary(tmp_path):
    binary = tmp_path / "libstockfish.so"
    _write_minimal_elf(
        binary, e_type=engine_verify.ET_DYN, e_machine=_host_machine()
    )

    ok, reason = engine_verify.check_android_binary(str(binary))

    assert ok is True
    assert reason == ""


def test_rejects_non_elf_file(tmp_path):
    binary = tmp_path / "stockfish"
    binary.write_bytes(b"not an elf binary")

    ok, reason = engine_verify.check_android_binary(str(binary))

    assert ok is False
    assert "ELF" in reason


def test_rejects_missing_file(tmp_path):
    ok, reason = engine_verify.check_android_binary(
        str(tmp_path / "does-not-exist")
    )

    assert ok is False
    assert reason != ""


def test_rejects_wrong_architecture(tmp_path):
    binary = tmp_path / "stockfish"
    host = _host_machine()
    other = (
        engine_verify.EM_X86_64
        if host != engine_verify.EM_X86_64
        else engine_verify.EM_AARCH64
    )
    _write_minimal_elf(binary, e_type=engine_verify.ET_DYN, e_machine=other)

    ok, reason = engine_verify.check_android_binary(str(binary))

    assert ok is False
    assert "Architecture mismatch" in reason


def test_expected_machine_overrides_host_for_cross_builds(tmp_path):
    # A Linux x86_64 CI runner cross-building the arm64 binary must be able
    # to gate it without an arm64 host.
    binary = tmp_path / "libstockfish.so"
    _write_minimal_elf(
        binary,
        e_type=engine_verify.ET_DYN,
        e_machine=engine_verify.EM_AARCH64,
    )

    ok, reason = engine_verify.check_android_binary(
        str(binary), expected_machine=engine_verify.EM_AARCH64
    )

    assert ok is True
    assert reason == ""


def test_expected_machine_mismatch_still_rejected(tmp_path):
    binary = tmp_path / "libstockfish.so"
    _write_minimal_elf(
        binary,
        e_type=engine_verify.ET_DYN,
        e_machine=engine_verify.EM_AARCH64,
    )

    ok, reason = engine_verify.check_android_binary(
        str(binary), expected_machine=engine_verify.EM_X86_64
    )

    assert ok is False
    assert "Architecture mismatch" in reason
