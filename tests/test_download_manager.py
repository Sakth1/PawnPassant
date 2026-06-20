"""Tests for core.download_manager — _resolve_archive."""
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.download_manager import _resolve_archive


class TestResolveArchive(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="test_resolve_archive_"))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_binary(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"#!/usr/bin/env python\nprint('stockfish')\n")
        path.chmod(0o755)

    def test_plain_binary_returns_unchanged(self):
        f = self._tmp / "stockfish.exe"
        self._write_binary(f)
        result = _resolve_archive(f)
        self.assertEqual(result, f.resolve())

    def test_nonexistent_archive_returns_path_unchanged(self):
        p = self._tmp / "nope.zip"
        result = _resolve_archive(p)
        self.assertEqual(result, p)

    def test_extracts_zip_with_stockfish_exe(self):
        zip_path = self._tmp / "stockfish-windows-x86-64-bmi2.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr(
                "stockfish-windows-x86-64-bmi2/stockfish.exe",
                b"fake binary content",
            )

        result = _resolve_archive(zip_path)
        self.assertTrue(result.name.startswith("stockfish"))
        self.assertTrue(zip_path.exists() is False, "Archive should be deleted")
        self.assertEqual(result.parent, self._tmp)

    def test_archive_without_stockfish_returns_unchanged(self):
        zip_path = self._tmp / "empty.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("random_file.txt", b"hello")

        result = _resolve_archive(zip_path)
        self.assertEqual(result, zip_path)

    def test_bad_zip_returns_unchanged(self):
        f = self._tmp / "corrupt.zip"
        f.write_bytes(b"not a zip file")
        result = _resolve_archive(f)
        self.assertEqual(result, f)


if __name__ == "__main__":
    unittest.main()
