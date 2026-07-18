"""Copy the correct ABI-specific Stockfish binary into assets/ before APK build.

Usage:
    python scripts/prepare_android_engine.py [arm64-v8a|armeabi-v7a]

If no ABI is given, copies arm64-v8a (default).
"""
import shutil
import sys
from pathlib import Path

BUNDLED_ROOT = Path(__file__).resolve().parent.parent / "bundled" / "stockfish" / "android"
ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets" / "stockfish" / "android"


def main():
    abi = sys.argv[1] if len(sys.argv) > 1 else "arm64-v8a"
    src = BUNDLED_ROOT / abi / "stockfish"
    if not src.exists():
        print(f"ERROR: bundled binary not found at {src}", file=sys.stderr)
        print("Run scripts/fetch_stockfish_android.py first.", file=sys.stderr)
        sys.exit(1)

    dst = ASSETS_ROOT / abi
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst / "stockfish"))
    dst_bin = dst / "stockfish"
    dst_bin.chmod(dst_bin.stat().st_mode | 0o111)
    print(f"Copied {src} -> {dst / 'stockfish'} ({src.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
