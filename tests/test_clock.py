"""Regression tests for the event-driven threaded chess clock."""

import asyncio
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.clock import Clock
from ui.clockui import ClockUI
from utils.events import (
    ClockStateEvent,
    ClockTickEvent,
    GameEndedEvent,
    GameStartedEvent,
    PieceModevedEvent,
)
from utils.models import ActiveColor
from utils.signals import bus


class _FakePage:
    def __init__(self):
        self.calls = []

    def run_task(self, fn, *args):
        self.calls.append((fn, args))
        return asyncio.run(fn(*args))


class _ClockStub:
    def __init__(self):
        self.start_calls = 0
        self.switch_calls = 0
        self.stop_calls = 0

    def start(self):
        self.start_calls += 1

    def switch(self):
        self.switch_calls += 1

    def stop(self):
        self.stop_calls += 1


class TestClock(unittest.TestCase):
    """Verify the threaded clock emits bus events with the expected cadence."""

    def setUp(self):
        self._original_listeners = {
            event_type: listeners.copy()
            for event_type, listeners in bus._listeners.items()
        }
        bus._listeners = {}
        self.tick_events = []
        self.state_events = []
        bus.connect(ClockTickEvent, self.tick_events.append)
        bus.connect(ClockStateEvent, self.state_events.append)

    def tearDown(self):
        clock = getattr(self, "clock", None)
        if clock is not None:
            clock.stop()
        bus._listeners = {
            event_type: listeners.copy()
            for event_type, listeners in self._original_listeners.items()
        }

    def test_start_emits_initial_tick_and_started_state(self):
        self.clock = Clock(time_control=(1, 0))
        self.clock.white_ticker.tick_interval = 20
        self.clock.black_ticker.tick_interval = 20

        self.clock.start()
        time.sleep(0.05)

        self.assertEqual(self.clock.active_color, ActiveColor.WHITE)
        self.assertTrue(self.clock.white_ticker.active)
        self.assertFalse(self.clock.black_ticker.active)
        self.assertTrue(self.tick_events)
        self.assertEqual(self.tick_events[0].color, ActiveColor.WHITE)
        self.assertEqual(
            self.state_events[0],
            ClockStateEvent(state="started", active_color=ActiveColor.WHITE),
        )

    def test_normal_mode_only_emits_when_displayed_second_changes(self):
        self.clock = Clock(time_control=(1, 0))
        self.clock.white_ticker.tick_interval = 20
        self.clock.black_ticker.tick_interval = 20

        self.clock.start()
        time.sleep(0.15)

        white_events = [
            event
            for event in self.tick_events
            if event.color == ActiveColor.WHITE and not event.is_critical
        ]
        displayed_seconds = [(event.minutes, event.seconds) for event in white_events]
        self.assertGreaterEqual(len(white_events), 2)
        self.assertEqual(len(displayed_seconds), len(set(displayed_seconds)))

    def test_critical_mode_emits_every_tick_with_milliseconds(self):
        self.clock = Clock(time_control=(1, 0), critical_threshold_seconds=10)
        self.clock.white_ticker.remaining_time_ms = 9_950
        self.clock.white_ticker.tick_interval = 20
        self.clock.black_ticker.tick_interval = 20

        self.clock.start()
        time.sleep(0.08)

        white_events = [
            event for event in self.tick_events if event.color == ActiveColor.WHITE
        ]
        self.assertGreaterEqual(len(white_events), 3)
        self.assertTrue(all(event.is_critical for event in white_events))
        self.assertGreater(
            len({event.milliseconds for event in white_events}),
            1,
        )

    def test_switch_emits_both_colors_and_applies_increment(self):
        self.clock = Clock(time_control=(1, 2))
        self.clock.white_ticker.tick_interval = 20
        self.clock.black_ticker.tick_interval = 20

        self.clock.start()
        time.sleep(0.06)
        white_before_switch = self.clock.white_ticker.remaining_time_ms

        self.clock.switch()
        time.sleep(0.03)

        self.assertEqual(self.clock.active_color, ActiveColor.BLACK)
        self.assertFalse(self.clock.white_ticker.active)
        self.assertTrue(self.clock.black_ticker.active)
        self.assertGreater(
            self.clock.white_ticker.remaining_time_ms,
            white_before_switch + 1500,
        )
        switched_events = [
            event for event in self.state_events if event.state == "switched"
        ]
        self.assertTrue(switched_events)
        self.assertEqual(switched_events[-1].active_color, ActiveColor.BLACK)
        colors_seen = {event.color for event in self.tick_events}
        self.assertIn(ActiveColor.WHITE, colors_seen)
        self.assertIn(ActiveColor.BLACK, colors_seen)

    def test_flag_fall_emits_terminal_tick_and_flagged_state(self):
        self.clock = Clock(time_control=(1, 0), critical_threshold_seconds=10)
        self.clock.white_ticker.remaining_time_ms = 35
        self.clock.white_ticker.tick_interval = 10
        self.clock.black_ticker.tick_interval = 10

        self.clock.start()
        time.sleep(0.08)

        flagged_events = [
            event for event in self.state_events if event.state == "flagged"
        ]
        self.assertTrue(flagged_events)
        self.assertEqual(flagged_events[-1].active_color, ActiveColor.WHITE)
        self.assertFalse(self.clock.white_ticker.active)
        last_white_tick = [
            event for event in self.tick_events if event.color == ActiveColor.WHITE
        ][-1]
        self.assertEqual(
            (
                last_white_tick.minutes,
                last_white_tick.seconds,
                last_white_tick.milliseconds,
            ),
            (0, 0, 0),
        )

        tick_count_after_flag = len(self.tick_events)
        time.sleep(0.03)
        self.assertEqual(len(self.tick_events), tick_count_after_flag)


class TestClockUi(unittest.TestCase):
    """Verify the UI reacts to clock events without touching worker threads directly."""

    def setUp(self):
        self._original_listeners = {
            event_type: listeners.copy()
            for event_type, listeners in bus._listeners.items()
        }
        bus._listeners = {}

    def tearDown(self):
        bus._listeners = {
            event_type: listeners.copy()
            for event_type, listeners in self._original_listeners.items()
        }

    def test_clock_tick_uses_call_from_thread_for_ui_updates(self):
        clock_ui = ClockUI()
        fake_page = _FakePage()
        updates = []

        clock_ui._safe_page = lambda: fake_page
        clock_ui.update = lambda: updates.append("updated")

        event = ClockTickEvent(
            color=ActiveColor.BLACK,
            minutes=0,
            seconds=9,
            milliseconds=870,
            is_critical=True,
        )
        clock_ui._handle_clock_tick(event)

        self.assertEqual(len(fake_page.calls), 1)
        self.assertEqual(clock_ui.black_timer.value, "00:09.87")
        self.assertEqual(updates, ["updated"])

    def test_bus_events_drive_start_switch_and_stop(self):
        clock_ui = ClockUI()
        clock_ui.clock = _ClockStub()

        bus.emit(GameStartedEvent())
        bus.emit(PieceModevedEvent())
        bus.emit(GameEndedEvent())

        self.assertEqual(clock_ui.clock.start_calls, 1)
        self.assertEqual(clock_ui.clock.switch_calls, 1)
        self.assertEqual(clock_ui.clock.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
