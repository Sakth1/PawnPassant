"""Tests for core.binary_verifier — verify_stockfish_binary."""

import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from core.binary_verifier import verify_stockfish_binary


class TestBinaryVerifier(unittest.TestCase):
    def test_nonexistent_file_returns_false(self):
        valid, msg = verify_stockfish_binary("C:\\nonexistent\\stockfish.exe")
        self.assertFalse(valid)
        self.assertIn("File not found", msg)

    def test_non_executable_file_returns_false(self):
        with NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"not a binary")
            tmp = f.name
        try:
            valid, msg = verify_stockfish_binary(tmp)
            self.assertFalse(valid)
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_empty_path_returns_false(self):
        valid, msg = verify_stockfish_binary("")
        self.assertFalse(valid)

    def test_directory_path_returns_false(self):
        valid, msg = verify_stockfish_binary(".")
        self.assertFalse(valid)
        self.assertIn("Not a file", msg)

    def test_verify_non_stockfish_binary(self):
        with NamedTemporaryFile(delete=False, suffix=".exe") as f:
            f.write(b"#!/usr/bin/env python\nprint('hello')")
            tmp = f.name
        try:
            valid, msg = verify_stockfish_binary(tmp)
            self.assertFalse(valid)
        finally:
            Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
