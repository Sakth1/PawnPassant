"""Tests for newly added events in utils.events."""

import unittest

from utils.events import BinaryVerificationResultEvent


class TestBinaryVerificationResultEvent(unittest.TestCase):
    def test_valid_event_creation(self):
        event = BinaryVerificationResultEvent(
            valid=True,
            path="/usr/local/bin/lc0",
            version="Lc0 0.32.1",
        )
        self.assertTrue(event.valid)
        self.assertEqual(event.path, "/usr/local/bin/lc0")
        self.assertEqual(event.version, "Lc0 0.32.1")

    def test_invalid_event_creation(self):
        event = BinaryVerificationResultEvent(
            valid=False,
            path="/bad/path",
            version="File not found",
        )
        self.assertFalse(event.valid)
        self.assertEqual(event.path, "/bad/path")
        self.assertEqual(event.version, "File not found")

    def test_event_is_frozen(self):
        event = BinaryVerificationResultEvent(
            valid=True,
            path="/path",
            version="v1",
        )
        with self.assertRaises(AttributeError):
            event.valid = False


if __name__ == "__main__":
    unittest.main()
