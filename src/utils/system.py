"""System architecture and platform detection utilities."""

import logging
import os
import platform

from utils.models import Arch, CpuSubarch, Platform, SystemInfo

logger = logging.getLogger(__name__)

_system_info: SystemInfo | None = None


def get_sys_arch() -> Arch:
    raw = platform.machine().lower()
    if raw in ("arm64", "aarch64"):
        return Arch.ARM64
    if raw.startswith("arm"):
        return Arch.ARM
    if raw in ("amd64", "x86_64", "x64"):
        return Arch.X86_64
    if raw in ("i386", "i686", "x86"):
        return Arch.X86
    return Arch.UNKNOWN


def get_sys_platform() -> Platform:
    system = platform.system().lower()
    if system == "windows":
        return Platform.WINDOWS
    if system == "linux":
        return Platform.LINUX
    if system == "darwin":
        return Platform.MACOS
    return Platform.UNKNOWN


def detect_cpu_subarch() -> CpuSubarch:
    """Detect the CPU sub-architecture of the current system.

    Returns the most specific :class:`CpuSubarch` value that matches the
    running CPU. Detection methods vary by platform:

    * **Windows** — checks ``PROCESSOR_IDENTIFIER`` for CPU family/model.
    * **Linux** — reads ``/proc/cpuinfo`` for CPU flags.
    * **macOS** — uses ``sysctl`` to query CPU features.
    * **ARM64** — distinguishes Apple Silicon from generic ARMv8.

    When no specific sub-architecture can be determined, returns ``GENERIC``
    for x86-64 systems (a safe default) and ``UNKNOWN`` for others.
    """
    arch = get_sys_arch()
    sys_platform = get_sys_platform()

    if arch == Arch.ARM64:
        if sys_platform == Platform.MACOS:
            return CpuSubarch.APPLE_SILICON
        return CpuSubarch.ARMV8

    if arch == Arch.ARM:
        return CpuSubarch.ARMV8

    if arch == Arch.X86:
        return CpuSubarch.GENERIC

    if arch != Arch.X86_64:
        return CpuSubarch.UNKNOWN

    flags = _detect_x86_64_features()
    if flags is None:
        logger.info("Could not detect CPU features, defaulting to GENERIC")
        return CpuSubarch.GENERIC

    if "vnni" in flags:
        return CpuSubarch.VNNI
    if "bmi2" in flags:
        return CpuSubarch.BMI2
    if "avx2" in flags:
        return CpuSubarch.AVX2

    return CpuSubarch.MODERN


def _detect_x86_64_features() -> set[str] | None:
    """Return a set of detected CPU feature flags, or ``None`` if detection fails.

    Uses platform-specific methods to discover CPU capabilities.
    """
    sys_platform = get_sys_platform()

    if sys_platform == Platform.WINDOWS:
        return _detect_windows_cpu_features()

    if sys_platform == Platform.LINUX:
        return _detect_linux_cpu_features()

    if sys_platform == Platform.MACOS:
        return _detect_macos_cpu_features()

    return None


def _detect_windows_cpu_features() -> set[str] | None:
    """Detect x86-64 CPU features on Windows using environment variables."""
    proc_id = os.environ.get("PROCESSOR_IDENTIFIER", "").lower()
    if not proc_id:
        return None

    flags: set[str] = set()

    if "avx2" in proc_id:
        flags.add("avx2")

    processor_arch = os.environ.get("PROCESSOR_ARCHITECTURE", "")
    if "avx2" in processor_arch.lower():
        flags.add("avx2")

    return flags


def _detect_linux_cpu_features() -> set[str] | None:
    """Detect x86-64 CPU features on Linux from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            content = f.read().lower()
    except OSError:
        return None

    flags: set[str] = set()
    if "avx2" in content:
        flags.add("avx2")
    if "bmi2" in content:
        flags.add("bmi2")
    if "vnni" in content or "avx512" in content or "avx10" in content:
        if "vnni" in content:
            flags.add("vnni")
    return flags


def _detect_macos_cpu_features() -> set[str] | None:
    """Detect x86-64 CPU features on macOS using sysctl."""
    try:
        import subprocess

        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.features"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        feature_string = result.stdout.lower()
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    flags: set[str] = set()
    if "avx2" in feature_string:
        flags.add("avx2")
    if "bmi2" in feature_string:
        flags.add("bmi2")
    return flags


def get_system_info() -> SystemInfo:
    """Return cached system info, detecting on first call.

    The result is cached module-wide so that repeated calls from the download
    manager, storage paths, and other consumers share a single detection pass.
    """
    global _system_info
    if _system_info is not None:
        return _system_info

    _system_info = SystemInfo(
        arch=get_sys_arch(),
        platform=get_sys_platform(),
        subarch=detect_cpu_subarch(),
    )
    logger.info(
        "System info: arch=%s platform=%s subarch=%s",
        _system_info.arch.value,
        _system_info.platform.value,
        _system_info.subarch.value,
    )
    return _system_info
