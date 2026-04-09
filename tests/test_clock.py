"""Regression tests for the async chess clock."""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.Clock import Clock, ClockColor


class TestClock(unittest.IsolatedAsyncioTestCase):
    """Verify the async clock starts and switches players cleanly."""

    async def asyncTearDown(self):
        clock = getattr(self, "clock", None)
        if clock is not None:
            await clock.stop()

    async def test_start_runs_white_clock_without_blocking(self):
        white_ticks = []
        black_ticks = []

        self.clock = Clock(
            time_control=(1, 0),
            white_clock_callback=lambda *args: white_ticks.append(args),
            black_clock_callback=lambda *args: black_ticks.append(args),
        )
        self.clock.white_ticker.tick_interval = 20
        self.clock.black_ticker.tick_interval = 20

        await self.clock.start()
        await asyncio.sleep(0.06)

        self.assertEqual(self.clock.active_color, ClockColor.white)
        self.assertTrue(self.clock.white_ticker.pause_condition.is_set())
        self.assertFalse(self.clock.black_ticker.pause_condition.is_set())
        self.assertLess(self.clock.white_ticker.remaining_time_ms, 60000)
        self.assertEqual(self.clock.black_ticker.remaining_time_ms, 60000)
        self.assertTrue(white_ticks)
        self.assertFalse(black_ticks)

    async def test_switch_pauses_white_and_resumes_black_with_increment(self):
        self.clock = Clock(time_control=(1, 2))
        self.clock.white_ticker.tick_interval = 20
        self.clock.black_ticker.tick_interval = 20

        await self.clock.start()
        await asyncio.sleep(0.06)
        white_time_before_switch = self.clock.white_ticker.remaining_time_ms

        await self.clock.switch()
        await asyncio.sleep(0.06)

        self.assertEqual(self.clock.active_color, ClockColor.black)
        self.assertFalse(self.clock.white_ticker.pause_condition.is_set())
        self.assertTrue(self.clock.black_ticker.pause_condition.is_set())
        self.assertGreater(
            self.clock.white_ticker.remaining_time_ms,
            white_time_before_switch + 1500,
        )
        self.assertLess(self.clock.black_ticker.remaining_time_ms, 60000)


if __name__ == "__main__":
    unittest.main()
