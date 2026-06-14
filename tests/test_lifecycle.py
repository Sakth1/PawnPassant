"""Tests for view lifecycle, RouteManager, and SignalBus improvements."""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.routing import RouteManager
from utils.signals import bus, SignalBus

# ─────────────────────────────────────────────────────────────────────────────
# Fake page compatible with RouteManager
# ─────────────────────────────────────────────────────────────────────────────


class _FakePage:
    """Minimal page stub for RouteManager tests."""

    def __init__(self):
        self.route = "/home"
        self.navigation_bar = type("FakeNavBar", (), {"selected_index": 0})()
        self.controls = []

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass

    def navigate(self, route):
        self.route = route

    def run_task(self, fn, *args):
        coro = fn(*args)
        if asyncio.iscoroutine(coro):
            return asyncio.run(coro)
        return coro

    async def push_route(self, route):
        self.route = route


# ─────────────────────────────────────────────────────────────────────────────
# RouteManager lifecycle tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteManagerLifecycle(unittest.TestCase):
    """RouteManager must call lifecycle hooks in the correct order."""

    def setUp(self):
        self.page = _FakePage()
        self.view_container = type("FakeContainer", (), {"content": None})()
        self.home = object()
        self.game = object()
        self.settings = object()

        self.manager = RouteManager(
            page=self.page,
            view_container=self.view_container,
            route_views={
                "/home": self.home,
                "/game": self.game,
                "/settings": self.settings,
            },
            route_to_index={"/home": 0, "/game": 1, "/settings": 2},
        )

        self.calls = []
        self.manager.on_enter("/game", lambda: self.calls.append("enter"))
        self.manager.on_exit("/game", lambda: self.calls.append("exit"))

    def test_navigate_calls_on_exit_then_swap_then_on_enter(self):
        """on_exit for old route must fire before on_enter for new route."""
        self.manager.navigate("/home")
        self.calls.clear()
        self.manager.navigate("/game")

        self.assertEqual(self.calls, ["enter"])
        self.assertIs(self.view_container.content, self.game)

    def test_navigate_calls_on_exit_when_leaving_game(self):
        """Leaving /game must fire on_exit."""
        self.manager.navigate("/game")
        self.calls.clear()
        self.manager.navigate("/home")

        self.assertEqual(self.calls, ["exit"])
        self.assertIs(self.view_container.content, self.home)

    def test_navigate_to_same_route_fires_both_lifecycle_hooks(self):
        """Navigating to the current route restarts lifecycle (e.g. new game)."""
        self.manager.navigate("/game")
        self.calls.clear()
        self.manager.navigate("/game")

        self.assertEqual(self.calls, ["exit", "enter"])
        self.assertIs(self.view_container.content, self.game)

    def test_lifecycle_handler_error_does_not_crash_navigation(self):
        """A broken lifecycle handler must not prevent navigation."""
        self.manager.on_exit(
            "/game", lambda: (_ for _ in ()).throw(RuntimeError("oops"))
        )
        self.manager.navigate("/game")
        self.calls.clear()

        try:
            self.manager.navigate("/home")
        except Exception:
            self.fail("Broken on_exit handler leaked through navigation")

        self.assertIs(self.view_container.content, self.home)

    def test_unknown_route_falls_back_to_home(self):
        """Navigating to an unregistered route must fall back to /home."""
        self.manager.navigate("/nonexistent")

        self.assertEqual(self.page.route, "/home")
        self.assertIs(self.view_container.content, self.home)

    def test_navigation_bar_index_is_synced(self):
        """RouteManager must update navigation_bar.selected_index."""
        self.manager.navigate("/game")

        self.assertEqual(self.page.navigation_bar.selected_index, 1)

    def test_get_current_view_returns_none_before_first_navigation(self):
        """Before any navigate call, get_current_view must return None."""
        self.assertIsNone(self.manager.get_current_view())

    def test_get_current_view_after_navigation(self):
        """After navigation, get_current_view must return the current route view."""
        self.manager.navigate("/game")

        self.assertIs(self.manager.get_current_view(), self.game)


# ─────────────────────────────────────────────────────────────────────────────
# RouteManager event-handler delegation tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteManagerEventDelegation(unittest.TestCase):
    """RouteManager.handle_route_change and handle_navigation_change."""

    def setUp(self):
        self.page = _FakePage()
        self.view_container = type("FakeContainer", (), {"content": None})()
        self.home = object()
        self.manager = RouteManager(
            page=self.page,
            view_container=self.view_container,
            route_views={"/home": self.home},
            route_to_index={"/home": 0},
        )

    def test_handle_route_change_navigates_to_event_route(self):
        event = type("RouteEvent", (), {"route": "/home"})()
        self.manager.handle_route_change(event)

        self.assertIs(self.view_container.content, self.home)

    def test_handle_route_change_falls_back_to_home_without_route(self):
        event = type("RouteEvent", (), {"route": None})()
        self.manager.handle_route_change(event)

        self.assertIs(self.view_container.content, self.home)

    def test_handle_navigation_change_uses_selected_index(self):
        game = object()
        self.manager._route_views["/game"] = game
        self.manager._route_to_index["/game"] = 1
        nav_bar = type("FakeNavBar", (), {"selected_index": 1})()
        event = type("NavEvent", (), {"control": nav_bar})()

        self.manager.handle_navigation_change(event)

        self.assertIs(self.view_container.content, game)


# ─────────────────────────────────────────────────────────────────────────────
# SignalBus enhancements
# ─────────────────────────────────────────────────────────────────────────────


class TestSignalBusDisconnect(unittest.TestCase):
    """SignalBus.disconnect must remove listeners correctly."""

    def setUp(self):
        self.bus = SignalBus()
        self._calls = []
        self._handler = lambda _e: self._calls.append("called")

    def test_disconnect_removes_listener(self):
        self.bus.connect(str, self._handler)
        self.bus.disconnect(str, self._handler)
        self.bus.emit("hello")

        self.assertEqual(self._calls, [])

    def test_disconnect_raises_for_nonexistent_handler(self):
        self.bus.connect(str, self._handler)

        other = lambda _e: None
        with self.assertRaises(ValueError):
            self.bus.disconnect(str, other)

    def test_disconnect_raises_for_unknown_event_type(self):
        with self.assertRaises(ValueError):
            self.bus.disconnect(int, self._handler)

    def test_disconnect_only_removes_exact_handler(self):
        other = lambda _e: self._calls.append("other")
        self.bus.connect(str, self._handler)
        self.bus.connect(str, other)

        self.bus.disconnect(str, self._handler)
        self.bus.emit("hello")

        self.assertEqual(self._calls, ["other"])


class TestSignalBusErrorIsolation(unittest.TestCase):
    """One failing handler must not prevent other handlers from firing."""

    def setUp(self):
        self.bus = SignalBus()
        self._calls = []

    def test_error_isolation(self):
        broken = lambda _e: (_ for _ in ()).throw(RuntimeError("oops"))
        working = lambda _e: self._calls.append("ok")

        self.bus.connect(str, broken)
        self.bus.connect(str, working)

        try:
            self.bus.emit("hello")
        except Exception:
            self.fail("SignalBus.emit leaked exception from a broken handler")

        self.assertEqual(self._calls, ["ok"])

    def test_multiple_errors_do_not_cascade(self):
        broken1 = lambda _e: (_ for _ in ()).throw(RuntimeError("first"))
        broken2 = lambda _e: (_ for _ in ()).throw(RuntimeError("second"))
        working = lambda _e: self._calls.append("ok")

        self.bus.connect(str, broken1)
        self.bus.connect(str, broken2)
        self.bus.connect(str, working)

        try:
            self.bus.emit("hello")
        except Exception:
            self.fail("SignalBus.emit leaked exception from broken handler")

        self.assertEqual(self._calls, ["ok"])


if __name__ == "__main__":
    unittest.main()
