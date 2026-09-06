"""Build position-independent (PIE) Stockfish binaries for Android.

Upstream Stockfish CI exports ``LDFLAGS="-static"`` for its Android builds
(PGO-under-QEMU workaround), producing non-PIE ``ET_EXEC`` binaries that
modern Android refuses to execute. This script builds per-architecture
dynamically linked PIE (``ET_DYN``) binaries from pinned Stockfish sources
using the Android NDK, then gates each artifact with the ELF packaging
check from :mod:`core.engine_verify`.

Intended to run on a Linux CI runner with the NDK installed::

    python scripts/build_stockfish_android_pie.py --abi all --outdir dist/

Outputs ``<outdir>/<android-abi>/libstockfish.so`` ready for APK
packaging under ``lib/<abi>/`` (see ``scripts/package_android_engine.py``).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

STOCKFISH_REPO = "https://github.com/official-stockfish/Stockfish.git"
DEFAULT_REF = "sf_19"

# Android ABI -> (NDK clang++ driver, Stockfish ARCH, ELF e_machine).
ABI_MAP: dict[str, tuple[str, str, int]] = {
    # e_machine values: 183 = AArch64, 40 = ARM. Imported lazily from
    # core.engine_verify by main(); duplicated here to keep this module
    # importable without src/ on sys.path.
    "arm64-v8a": ("aarch64-linux-android29-clang++", "armv8", 183),
    "armeabi-v7a": ("armv7a-linux-androideabi29-clang++", "armv7-neon", 40),
}

# API 29 = oldest level with the fixed ELF TLS layout (NDK r27c errors out
# below it); dynamic link against Bionic keeps the binary forward compatible.
# 16 KB page alignment is required by Google Play for Android 15+ targets.
EXTRA_LDFLAGS = "-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384"


def resolve_abis(spec: str) -> list[str]:
    if spec == "all":
        return list(ABI_MAP)
    if spec in ABI_MAP:
        return [spec]
    raise ValueError(
        f"Unknown ABI {spec!r}; expected one of {sorted(ABI_MAP)} or 'all'"
    )


def toolchain_for_abi(abi: str) -> tuple[str, str]:
    """Return (NDK compiler driver, Stockfish ARCH) for an Android ABI."""
    compiler, stockfish_arch, _ = ABI_MAP[abi]
    return compiler, stockfish_arch


def expected_machine_for_abi(abi: str) -> int:
    return ABI_MAP[abi][2]


def build_command(
    abi: str, ndk_bin: str, source_dir: Path
) -> tuple[list[str], dict[str, str]]:
    """Return (make command, extra env) for a dynamically linked PIE build.

    Never requests full ``-static`` linking: that is exactly what produces
    the uninstallable ``ET_EXEC`` binaries upstream ships. Plain ``build``
    (not ``profile-build``) is used because PGO needs QEMU, and QEMU cannot
    run dynamically linked NDK binaries (no Android loader on the host).
    """
    _, stockfish_arch = toolchain_for_abi(abi)
    jobs = str(os.cpu_count() or 4)
    cmd = [
        "make",
        f"-j{jobs}",
        "build",
        f"ARCH={stockfish_arch}",
        "COMP=ndk",
    ]
    env = {
        "PATH": ndk_bin + os.pathsep + os.environ.get("PATH", ""),
        "EXTRALDFLAGS": EXTRA_LDFLAGS,
    }
    return cmd, env


def build_steps(
    abi: str, ndk_bin: str, source_dir: Path
) -> list[tuple[str, list[str], dict[str, str]]]:
    """Ordered (name, command, env) steps; NNUE embedding comes first."""
    cmd, env = build_command(abi, ndk_bin, source_dir)
    make_net = (["make", "net"], env)
    return [("net", *make_net), ("build", cmd, env)]


def require_platform(platform_name: str) -> None:
    if platform_name != "linux":
        print(
            f"ERROR: Android NDK cross-builds require Linux (got {platform_name!r}).",
            file=sys.stderr,
        )
        raise SystemExit(1)


def require_ndk_bin(path: str) -> str:
    if not Path(path).is_dir():
        print(
            f"ERROR: NDK bin directory not found: {path}\n"
            "Install NDK r27c+ and pass its "
            "toolchains/llvm/prebuilt/linux-x86_64/bin via --ndk-bin.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return path


def _run(cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
    print(f"+ {' '.join(cmd)} (cwd={cwd})")
    merged = dict(os.environ)
    merged.update(env)
    subprocess.run(cmd, cwd=str(cwd), env=merged, check=True)


def _ensure_source(workdir: Path, ref: str) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    checkout = workdir / "Stockfish"
    if not (checkout / ".git").exists():
        _run(
            [
                "git", "clone", "--depth", "1", "--branch", ref,
                STOCKFISH_REPO, str(checkout),
            ],
            cwd=workdir,
            env={},
        )
    src = checkout / "src"
    if not src.is_dir():
        print(f"ERROR: Stockfish source not found at {src}", file=sys.stderr)
        raise SystemExit(1)
    return src


def _gate_binary(binary: Path, abi: str) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root / "src") not in sys.path:
        sys.path.insert(0, str(repo_root / "src"))
    from core.engine_verify import ET_DYN, check_android_binary, read_elf_diagnostics

    ok, reason = check_android_binary(
        str(binary), expected_machine=expected_machine_for_abi(abi)
    )
    diag = read_elf_diagnostics(str(binary))
    print(f"  ELF e_type={diag['e_type']} ({diag['e_type_name']})")
    if not ok:
        print(f"ERROR: PIE packaging gate failed for {abi}: {reason}", file=sys.stderr)
        raise SystemExit(1)
    if diag["e_type"] != ET_DYN:
        print(
            f"ERROR: {abi} binary is not ET_DYN (got {diag['e_type']}); "
            "refusing to package a non-PIE binary.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(f"  PIE gate passed for {abi}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build PIE Stockfish for Android")
    parser.add_argument(
        "--abi", default="all", choices=[*ABI_MAP, "all"],
        help="Android ABI to build (default: all)",
    )
    parser.add_argument(
        "--ref", default=DEFAULT_REF,
        help=f"Stockfish git ref to build (default: {DEFAULT_REF})",
    )
    parser.add_argument(
        "--ndk-bin", required=True,
        help="NDK LLVM bin dir (toolchains/llvm/prebuilt/linux-x86_64/bin)",
    )
    parser.add_argument("--workdir", default="build/stockfish-pie")
    parser.add_argument("--outdir", default="dist/stockfish-android")
    args = parser.parse_args()

    require_platform(sys.platform)
    ndk_bin = require_ndk_bin(args.ndk_bin)

    src = _ensure_source(Path(args.workdir), args.ref)
    outdir = Path(args.outdir)
    for abi in resolve_abis(args.abi):
        print(f"=== Building {abi} ===")
        for name, cmd, env in build_steps(abi, ndk_bin, src):
            print(f"--- step: {name} ---")
            _run(cmd, cwd=src, env=env)
        built = src / "stockfish"
        dest_dir = outdir / abi
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "libstockfish.so"
        shutil.copy2(str(built), str(dest))
        strip = Path(ndk_bin) / "llvm-strip"
        if strip.exists():
            _run([str(strip), str(dest)], cwd=src, env={})
        _gate_binary(dest, abi)
        print(f"  -> {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
