"""Android native-library engine resolution tests (TDD).

On modern Android (API 29+) executables can only run from the app's
read-only native library directory. Flet/serious_python exposes it to the
embedded Python process via the ``ANDROID_NATIVE_LIBRARY_DIR`` environment
variable (see https://flet.dev/docs/publish/android). With legacy packaging
the Stockfish PIE binary is extracted there as ``libstockfish.so`` and must
be executed from that path — never from writable app storage.
"""

import os

import utils.paths as paths


def _clean_env(monkeypatch):
    for var in (
        "ANDROID_NATIVE_LIBRARY_DIR",
        "FLET_APP_LIB_DIR",
        "FLET_ASSETS_DIR",
        "FLET_APP_STORAGE_DATA",
        "ENGINE_BINARY_DIR",
    ):
        monkeypatch.delenv(var, raising=False)


def test_resolves_engine_from_android_native_library_dir(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    lib = tmp_path / "libstockfish.so"
    lib.write_bytes(b"fake-elf")
    monkeypatch.setenv("ANDROID_NATIVE_LIBRARY_DIR", str(tmp_path))

    found = paths.get_bundled_engine_path(engine_name="stockfish")

    assert found is not None
    assert found == lib.resolve()


def test_resolves_custom_engine_name_from_native_library_dir(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    lib = tmp_path / "libfairy.so"
    lib.write_bytes(b"fake-elf")
    monkeypatch.setenv("ANDROID_NATIVE_LIBRARY_DIR", str(tmp_path))

    found = paths.get_bundled_engine_path(engine_name="fairy")

    assert found is not None
    assert found == lib.resolve()


def test_legacy_flet_app_lib_dir_still_supported(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    lib = tmp_path / "libstockfish.so"
    lib.write_bytes(b"fake-elf")
    monkeypatch.setenv("FLET_APP_LIB_DIR", str(tmp_path))

    found = paths.get_bundled_engine_path(engine_name="stockfish")

    assert found is not None
    assert found == lib.resolve()


def test_android_native_library_dir_takes_precedence(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    first = tmp_path / "first" / "libstockfish.so"
    first.parent.mkdir()
    first.write_bytes(b"fake-elf")
    second = tmp_path / "second" / "libstockfish.so"
    second.parent.mkdir()
    second.write_bytes(b"fake-elf")
    monkeypatch.setenv("ANDROID_NATIVE_LIBRARY_DIR", str(first.parent))
    monkeypatch.setenv("FLET_APP_LIB_DIR", str(second.parent))

    found = paths.get_bundled_engine_path(engine_name="stockfish")

    assert found == first.resolve()


def test_returns_none_when_native_lib_missing(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("ANDROID_NATIVE_LIBRARY_DIR", str(tmp_path))

    assert paths.get_bundled_engine_path(engine_name="stockfish") is None


def test_missing_native_lib_dir_env_is_not_an_error(monkeypatch):
    _clean_env(monkeypatch)
    assert os.environ.get("ANDROID_NATIVE_LIBRARY_DIR") is None

    # Must not raise; falls through to the other lookup strategies.
    paths.get_bundled_engine_path(engine_name="stockfish")


def test_device_android_abi_mapping(monkeypatch):
    import platform

    cases = {
        "aarch64": "arm64-v8a",
        "arm64": "arm64-v8a",
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "armv7l": "armeabi-v7a",
        "armv8l": "arm64-v8a",
    }
    for machine, abi in cases.items():
        monkeypatch.setattr(platform, "machine", lambda m=machine: m)
        assert paths.device_android_abi() == abi, machine


def test_native_lib_wins_over_asset_copy(tmp_path, monkeypatch):
    """A bundled lib/*.so must shadow any stale assets/ copy.

    Asset extraction targets writable app storage, which Android 10+
    refuses to execute from — the native library directory is the only
    runnable location, so it must resolve first.
    """
    _clean_env(monkeypatch)
    monkeypatch.setenv("ANDROID_ROOT", "/system")
    abi = paths.device_android_abi()
    assets_dir = tmp_path / "assets"
    (assets_dir / "stockfish" / "android" / abi).mkdir(parents=True)
    (assets_dir / "stockfish" / "android" / abi / "stockfish").write_bytes(
        b"stale-asset"
    )
    monkeypatch.setenv("FLET_ASSETS_DIR", str(assets_dir))
    native = tmp_path / "native" / "libstockfish.so"
    native.parent.mkdir()
    native.write_bytes(b"fake-elf")
    monkeypatch.setenv("ANDROID_NATIVE_LIBRARY_DIR", str(native.parent))

    try:
        found = paths.get_bundled_engine_path(engine_name="stockfish")
    finally:
        monkeypatch.delenv("ANDROID_ROOT", raising=False)

    assert found == native.resolve()
