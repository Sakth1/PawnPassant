from __future__ import annotations

import logging
import os
import struct
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

ET_EXEC = 2
ET_DYN = 3
PT_INTERP = 3
DT_NEEDED = 1
DT_STRTAB = 5

EM_AARCH64 = 183
EM_X86_64 = 62
EM_ARM = 40
EM_386 = 3

_MACHINE_NAMES = {
    EM_AARCH64: "AArch64 (ARM64)",
    EM_X86_64: "x86-64 (AMD64)",
    EM_ARM: "ARM (32-bit)",
    EM_386: "x86 (32-bit)",
}

_E_TYPE_NAMES = {
    ET_EXEC: "ET_EXEC (non-PIE executable, value 2)",
    ET_DYN: "ET_DYN (PIE executable / shared object, value 3)",
}

_GLIBC_LIBS = {"libc.so.6", "libstdc++.so.6", "libpthread.so.0", "libm.so.6", "libdl.so.2"}


def _read_elf_e_type(path: str) -> int | None:
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                return None
            f.seek(16)
            data = f.read(2)
            return struct.unpack("<H", data)[0]
    except OSError:
        return None


def _read_elf_e_machine(path: str) -> int | None:
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                return None
            f.seek(18)
            data = f.read(2)
            return struct.unpack("<H", data)[0]
    except OSError:
        return None


def _read_elf_interp(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                return None
            is_64 = f.read(1) == b"\x02"
            f.seek(0)
            header = f.read(64 if is_64 else 52)
            if is_64:
                e_phoff = struct.unpack("<Q", header[32:40])[0]
                e_phentsize = struct.unpack("<H", header[54:56])[0]
                e_phnum = struct.unpack("<H", header[56:58])[0]
            else:
                e_phoff = struct.unpack("<I", header[28:32])[0]
                e_phentsize = struct.unpack("<H", header[42:44])[0]
                e_phnum = struct.unpack("<H", header[44:46])[0]
            for i in range(e_phnum):
                f.seek(e_phoff + i * e_phentsize)
                phdr = f.read(e_phentsize)
                p_type = struct.unpack("<I", phdr[:4])[0]
                if p_type == PT_INTERP:
                    if is_64:
                        p_offset = struct.unpack("<Q", phdr[8:16])[0]
                    else:
                        p_offset = struct.unpack("<I", phdr[4:8])[0]
                    f.seek(p_offset)
                    raw = b""
                    while True:
                        b = f.read(1)
                        if b == b"\x00" or not b:
                            break
                        raw += b
                    return raw.decode("utf-8", errors="replace")
    except OSError:
        pass
    return None


def _read_elf_needed_libs(path: str) -> list[str]:
    libs: list[str] = []
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                return libs
            is_64 = f.read(1) == b"\x02"
            f.seek(0)
            header = f.read(64 if is_64 else 52)
            if is_64:
                e_phoff = struct.unpack("<Q", header[32:40])[0]
                e_phentsize = struct.unpack("<H", header[54:56])[0]
                e_phnum = struct.unpack("<H", header[56:58])[0]
            else:
                e_phoff = struct.unpack("<I", header[28:32])[0]
                e_phentsize = struct.unpack("<H", header[42:44])[0]
                e_phnum = struct.unpack("<H", header[44:46])[0]

            dynamic_offset = None
            dynamic_size = None
            strtab_offset = None

            for i in range(e_phnum):
                f.seek(e_phoff + i * e_phentsize)
                phdr = f.read(e_phentsize)
                p_type = struct.unpack("<I", phdr[:4])[0]
                if p_type == 2:
                    if is_64:
                        dynamic_offset = struct.unpack("<Q", phdr[8:16])[0]
                        dynamic_size = struct.unpack("<Q", phdr[32:40])[0]
                    else:
                        dynamic_offset = struct.unpack("<I", phdr[4:8])[0]
                        dynamic_size = struct.unpack("<I", phdr[20:24])[0]

            if dynamic_offset is None:
                return libs

            f.seek(dynamic_offset)
            entry_size = 16 if is_64 else 8
            num_entries = dynamic_size // entry_size
            needed_offsets: list[int] = []

            for _ in range(num_entries):
                entry = f.read(entry_size)
                if is_64:
                    d_tag = struct.unpack("<Q", entry[:8])[0]
                    d_val = struct.unpack("<Q", entry[8:16])[0]
                else:
                    d_tag = struct.unpack("<I", entry[:4])[0]
                    d_val = struct.unpack("<I", entry[4:8])[0]
                if d_tag == DT_STRTAB:
                    strtab_offset = d_val
                elif d_tag == DT_NEEDED:
                    needed_offsets.append(d_val)
                if d_tag == 0:
                    break

            if strtab_offset is None:
                return libs

            for off in needed_offsets:
                f.seek(strtab_offset + off)
                raw = b""
                while True:
                    b = f.read(1)
                    if b == b"\x00" or not b:
                        break
                    raw += b
                libs.append(raw.decode("utf-8", errors="replace"))
    except OSError:
        pass
    return libs


def read_elf_diagnostics(path: str) -> dict:
    info: dict = {
        "e_type": None,
        "e_type_name": "",
        "e_machine": None,
        "machine_name": "",
        "interpreter": None,
        "needed_libs": [],
        "errors": [],
    }

    if not Path(path).exists():
        info["errors"].append("File not found")
        return info

    e_type = _read_elf_e_type(path)
    info["e_type"] = e_type
    if e_type is None:
        info["errors"].append("Not a valid ELF file (bad magic)")
        return info
    info["e_type_name"] = _E_TYPE_NAMES.get(e_type, f"Unknown e_type ({e_type})")

    e_machine = _read_elf_e_machine(path)
    info["e_machine"] = e_machine
    info["machine_name"] = _MACHINE_NAMES.get(e_machine, f"Unknown ({e_machine})")

    info["interpreter"] = _read_elf_interp(path)
    info["needed_libs"] = _read_elf_needed_libs(path)

    return info


def _check_android_compatible(diag: dict) -> tuple[bool, str]:
    if diag["e_type"] is None:
        return False, "Not a valid ELF file."

    if diag["e_type"] != ET_DYN:
        return False, (
            f"Android requires PIE executables (ET_DYN, value 3). "
            f"This binary has {diag['e_type_name']}. "
            "Download the Android NDK build of the engine."
        )

    if diag["e_machine"] is not None:
        import platform as _platform
        expected = {
            "aarch64": EM_AARCH64,
            "arm64": EM_AARCH64,
            "armv8": EM_AARCH64,
            "x86_64": EM_X86_64,
            "amd64": EM_X86_64,
        }
        machine = _platform.machine().lower()
        expected_val = None
        for k, v in expected.items():
            if k in machine:
                expected_val = v
                break
        if expected_val is not None and diag["e_machine"] != expected_val:
            return False, (
                f"Architecture mismatch: binary is {diag['machine_name']} "
                f"(e_machine={diag['e_machine']}) but device is {machine}. "
                f"Download the correct binary for your device architecture."
            )

    interp = diag.get("interpreter", "")
    if interp and "linux" in interp.lower() and "linker64" not in interp:
        return False, (
            f"This is a Linux binary (interpreter: {interp}), not an Android binary. "
            f"Android binaries use /system/bin/linker64. "
            f"Download the Android release of the engine."
        )

    for lib in diag.get("needed_libs", []):
        if lib in _GLIBC_LIBS:
            return False, (
                f"This is a glibc (Linux) binary (needs: {lib}). "
                f"Android uses Bionic libc. "
                f"Download the Android NDK build of the engine."
            )

    return True, ""


def _is_android() -> bool:
    return "ANDROID_ROOT" in os.environ


def _find_linker() -> str | None:
    for c in ["/system/bin/linker64", "/system/bin/linker"]:
        if os.path.exists(c):
            return c
    return None


def _verify_via_uci(path: str, extra_args: list[str] | None = None) -> tuple[bool, str]:
    cmd = (extra_args or []) + [path]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _ = proc.communicate(input="uci\nquit\n", timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("UCI verification failed for %s: %s", path, exc, exc_info=True)
        return False, f"Engine error: {exc}"

    engine_name = ""
    for line in stdout.splitlines():
        if line.startswith("id name "):
            engine_name = line[len("id name "):].strip()
        elif line.startswith("id author "):
            pass

    if engine_name:
        logger.info("Verified engine name=%s path=%s", engine_name, path)
        return True, engine_name

    preview = stdout[:200].replace("\n", " | ")
    return False, f"Engine did not respond to UCI. Output: {preview}"


def verify_engine_binary(path: str) -> tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        logger.warning("Binary not found at path=%s", path)
        return False, "File not found."
    if not p.is_file():
        logger.warning("Path is not a file path=%s", path)
        return False, "Not a file."

    if _is_android():
        if not os.access(path, os.X_OK):
            logger.warning("Binary lacks execute permission path=%s", path)

        diag = read_elf_diagnostics(path)
        compatible, reason = _check_android_compatible(diag)
        if not compatible:
            logger.error(
                "Android compatibility check failed: %s | diag=%s",
                reason,
                {k: v for k, v in diag.items() if k != "errors"},
            )
            return False, f"Binary not compatible: {reason}"

    extra_args: list[str] | None = None
    if _is_android():
        linker = _find_linker()
        if linker:
            extra_args = [linker]

    return _verify_via_uci(path, extra_args=extra_args)
