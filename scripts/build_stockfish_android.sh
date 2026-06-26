#!/bin/bash
# Build Stockfish for Android ARM64 with PIE support.
#
# The official Stockfish CI produces non-PIE static binaries (e_type=2) which
# Android's linker rejects. This script builds a PIE binary (e_type=3) that
# works with /system/bin/linker64 on Android 5.0+.
#
# Usage:
#   ARCH=arm64-universal STOCKFISH_TAG=sf_18 ./scripts/build_stockfish_android.sh
#
# Environment:
#   ARCH           Target arch (arm64-universal, armv8, armv7-neon)
#   STOCKFISH_TAG  Stockfish git tag or branch
#   ANDROID_NDK_BIN  Path to NDK toolchain bin dir (optional, auto-detected)
#
# Output:
#   stockfish-android-<ARCH>.tar.gz  in the current directory

set -euo pipefail

ARCH="${ARCH:-arm64-universal}"
STOCKFISH_TAG="${STOCKFISH_TAG:-master}"
SRC_DIR="stockfish-src"
OUTPUT_TAR="stockfish-android-${ARCH}.tar.gz"

# Detect NDK bin directory
if [ -z "${ANDROID_NDK_BIN:-}" ]; then
    ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
    NDK_VERSION="27.2.12479018"
    NDK_DIR="$ANDROID_HOME/ndk/$NDK_VERSION"
    if [ -d "$NDK_DIR" ]; then
        ANDROID_NDK_BIN="$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin"
    else
        echo "ERROR: ANDROID_NDK_BIN not set and NDK not found at $NDK_DIR"
        echo "Install NDK or set ANDROID_NDK_BIN"
        exit 1
    fi
fi

export PATH="$ANDROID_NDK_BIN:$PATH"

echo "=== Building Stockfish ==="
echo "ARCH:          $ARCH"
echo "STOCKFISH_TAG: $STOCKFISH_TAG"
echo "CXX:           $(which aarch64-linux-android29-clang++ 2>/dev/null || echo 'not found')"

# Clone
if [ ! -d "$SRC_DIR" ]; then
    echo "Cloning Stockfish@$STOCKFISH_TAG..."
    git clone --depth 1 --branch "$STOCKFISH_TAG" \
        https://github.com/official-stockfish/Stockfish.git "$SRC_DIR"
fi

cd "$SRC_DIR/src"

# Download NNUE network
echo "Downloading NNUE network..."
make net ARCH="$ARCH" COMP=ndk

# Build with corrected PIE flags.
# Key difference from official CI:
#   Official: LDFLAGS="-static ..." -> produces ET_EXEC (non-PIE)
#   Our:      LDFLAGS="-pie ..."    -> produces ET_DYN (PIE)
export LDFLAGS="-pie -Wno-unused-command-line-argument"

JOBS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)
echo "Building with $JOBS parallel jobs..."

if [ "$ARCH" = "arm64-universal" ]; then
    # Universal build needs UNIVERSAL_FINAL_FLAGS override to remove -static
    make -j"$JOBS" profile-build ARCH="$ARCH" COMP=ndk \
        UNIVERSAL_FINAL_FLAGS="-fno-exceptions -Os -static-libstdc++ -static-libgcc"
else
    make -j"$JOBS" profile-build ARCH="$ARCH" COMP=ndk
fi

make strip ARCH="$ARCH" COMP=ndk

# Verify file type
echo "=== Binary info ==="
file stockfish

# Package
cd ../..
tar czf "$OUTPUT_TAR" -C "$SRC_DIR/src" stockfish
echo "=== Done ==="
echo "Output: $OUTPUT_TAR"
echo "SHA256: $(sha256sum "$OUTPUT_TAR" | cut -d' ' -f1)"
