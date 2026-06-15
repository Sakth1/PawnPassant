"""Unit tests for utils.signals.SignalBus — connect, emit, disconnect, error isolation."""

import unittest

from utils.signals import SignalBus


class _TestEvent:
    def __init__(self, value=None):
        self.value = value


class _OtherEvent:
    pass


class TestSignalBusConnectEmit(unittest.TestCase):
    def setUp(self):
        self.bus = SignalBus()

    def test_emit_calls_registered_handler(self):
        results = []
        self.bus.connect(_TestEvent, lambda e: results.append(e.value))
        self.bus.emit(_TestEvent("hello"))
        self.assertEqual(results, ["hello"])

    def test_emit_calls_all_handlers(self):
        results = []
        self.bus.connect(_TestEvent, lambda e: results.append(1))
        self.bus.connect(_TestEvent, lambda e: results.append(2))
        self.bus.emit(_TestEvent())
        self.assertEqual(results, [1, 2])

    def test_emit_does_not_call_unrelated_handlers(self):
        results = []
        self.bus.connect(_TestEvent, lambda e: results.append("called"))
        self.bus.emit(_OtherEvent())
        self.assertEqual(results, [])

    def test_emit_with_no_listeners_does_not_raise(self):
        self.bus.emit(_TestEvent())


class TestSignalBusDisconnect(unittest.TestCase):
    def setUp(self):
        self.bus = SignalBus()

    def test_disconnect_removes_handler(self):
        results = []
        fn = lambda e: results.append("x")
        self.bus.connect(_TestEvent, fn)
        self.bus.disconnect(_TestEvent, fn)
        self.bus.emit(_TestEvent())
        self.assertEqual(results, [])

    def test_disconnect_raises_for_nonexistent_handler(self):
        fn = lambda e: None
        self.bus.connect(_TestEvent, fn)
        with self.assertRaises(ValueError):
            self.bus.disconnect(_OtherEvent, fn)

    def test_disconnect_raises_for_unknown_event_type(self):
        fn = lambda e: None
        with self.assertRaises(ValueError):
            self.bus.disconnect(_TestEvent, fn)

    def test_disconnect_removes_exact_handler_only(self):
        results = []
        fn1 = lambda e: results.append(1)
        fn2 = lambda e: results.append(2)
        self.bus.connect(_TestEvent, fn1)
        self.bus.connect(_TestEvent, fn2)
        self.bus.disconnect(_TestEvent, fn1)
        self.bus.emit(_TestEvent())
        self.assertEqual(results, [2])


class TestSignalBusErrorIsolation(unittest.TestCase):
    def setUp(self):
        self.bus = SignalBus()

    def test_broken_handler_does_not_block_others(self):
        results = []

        def broken(_):
            raise RuntimeError("oops")

        def working(e):
            results.append(e.value)

        self.bus.connect(_TestEvent, broken)
        self.bus.connect(_TestEvent, working)
        self.bus.emit(_TestEvent("ok"))
        self.assertEqual(results, ["ok"])

    def test_multiple_broken_handlers_still_call_working(self):
        results = []

        def broken1(_):
            raise ValueError("bad1")

        def broken2(_):
            raise TypeError("bad2")

        def working(e):
            results.append("ok")

        self.bus.connect(_TestEvent, broken1)
        self.bus.connect(_TestEvent, broken2)
        self.bus.connect(_TestEvent, working)
        self.bus.emit(_TestEvent())
        self.assertEqual(results, ["ok"])


if __name__ == "__main__":
    unittest.main()
