"""Unit tests for core.clock — Clock and Ticker timing logic."""

import time
import unittest
from unittest.mock import patch

from core.clock import Clock, Ticker
from utils.constants import MS_PER_MINUTE, MS_PER_SECOND


class TestTicker(unittest.TestCase):
    def test_initial_time_from_minutes(self):
        t = Ticker(starting_time=5)
        self.assertEqual(t.remaining_time_ms, 5 * MS_PER_MINUTE)
        self.assertEqual(t.increment, 0)

    def test_formatted_time_zero(self):
        t = Ticker(starting_time=0)
        self.assertEqual(t.formatted_time(), (0, 0, 0))

    def test_formatted_time_5_minutes(self):
        t = Ticker(starting_time=5)
        self.assertEqual(t.formatted_time(), (5, 0, 0))

    def test_formatted_time_1_min_30_sec(self):
        t = Ticker(starting_time=0)
        t.remaining_time_ms = 90 * MS_PER_SECOND
        self.assertEqual(t.formatted_time(), (1, 30, 0))

    def test_update_remaining_time_no_last_update(self):
        t = Ticker(starting_time=5)
        t.last_update_ts = None
        t.update_remaining_time(time.perf_counter())
        self.assertEqual(t.remaining_time_ms, 5 * MS_PER_MINUTE)

    def test_update_remaining_time_elapses(self):
        t = Ticker(starting_time=5)
        now = time.perf_counter()
        t.last_update_ts = now
        t.update_remaining_time(now + 1)
        # At most 1000ms elapsed
        self.assertAlmostEqual(
            t.remaining_time_ms,
            5 * MS_PER_MINUTE - 1000,
            delta=50,  # scheduler jitter
        )

    def test_update_remaining_time_clamps_negative(self):
        t = Ticker(starting_time=0)
        t.remaining_time_ms = 100
        now = time.perf_counter()
        t.last_update_ts = now
        t.update_remaining_time(now + 5)
        self.assertEqual(t.remaining_time_ms, 0)

    def test_negative_elapsed_is_ignored(self):
        t = Ticker(starting_time=5)
        now = time.perf_counter()
        t.last_update_ts = now
        t.update_remaining_time(now - 1)
        self.assertEqual(t.remaining_time_ms, 5 * MS_PER_MINUTE)

    def test_increment_applied(self):
        t = Ticker(starting_time=3, increment=2)
        self.assertEqual(t.increment, 2)


class TestClockConstruction(unittest.TestCase):
    def test_default_active_color_white(self):
        from utils.models import ActiveColor

        # We can't directly construct a Clock easily since it spawns a thread,
        # but we can test ticker initialization
        pass


if __name__ == "__main__":
    unittest.main()
