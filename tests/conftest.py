"""Shared pytest fixtures for Pawn Passant tests.

Automatically adds ``src/`` to ``sys.path`` so all tests can import
application modules without repeating the ``sys.path.insert`` boilerplate.
"""

import sys
from pathlib import Path

SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
