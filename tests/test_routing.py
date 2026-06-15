"""Tests for app routing, navigation safety, and event handler resilience."""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import ChessApp
from utils.dialogs import safe_update
from utils.events import GameEndedEvent, GameStartedEvent
from utils.signals import bus


class _CrashOnEmptyPopPage:
    """Fake page whose pop_dialog raises IndexError on empty overlay.

    Mirrors real Flet's behavior where page.pop_dialog() on an empty overlay
    raises IndexError, which was the root cause of the blank/"Working..." bug.
    """

    def __init__(self, width=960, height=800):
        self.width = width
        self.height = height
        self.window = type("FakeWindow", (), {"icon": None})()
        self.media = type(
            "FakeMedia",
            (),
            {
                "padding": type(
                    "FakePadding", (), {"left": 0, "top": 0, "right": 0, "bottom": 0}
                )()
            },
        )()
        self.fonts = {}
        self.title = ""
        self.padding = 0
        self.spacing = 0
        self.scroll = None
        self.overlay = []
        self.on_resize = None
        self.on_media_change = None
        self.controls = []
        self.route = "/home"
        self.navigation_bar = None

    def add(self, control):
        self.controls.append(control)

    def update(self):
        return None

    def show_dialog(self, dialog):
        dialog.open = True
        self.overlay.append(dialog)

    def pop_dialog(self):
        dialog = self.overlay.pop()
        dialog.open = False
        return dialog

    def run_task(self, fn, *args):
        return asyncio.run(fn(*args))

    async def push_route(self, route):
        self.route = route
        if self.on_route_change is not None:
            self.on_route_change(type("RouteEvent", (), {"route": route})())


class TestRoutingSafety(unittest.TestCase):
    """Route transitions and event handlers must never crash the WebSocket."""

    def setUp(self):
        self._original_emit = bus.emit
        bus.emit = lambda _event: None

    def tearDown(self):
        bus.emit = self._original_emit

    # --- E1: _handle_game_started without dialog ---

    def test_game_started_without_dialog_does_not_crash(self):
        """_handle_game_started must survive pop_dialog() on empty overlay.

        This was the root cause of the blank/"Working..." screen: pressing Play
        emitted GameStartedEvent, which called page.pop_dialog() when no dialog
        had ever been shown, crashing the WebSocket connection.
        """
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)
        page.overlay = []

        try:
            app._handle_game_started(GameStartedEvent())
        except Exception:
            self.fail("_handle_game_started raised on empty overlay")

        self.assertFalse(app.result_dialog.open)
        self.assertEqual(app.result_dialog_title.value, "")
        self.assertEqual(app.result_dialog_message.value, "")

    def test_game_started_after_result_dialog_clears_it(self):
        """_handle_game_started must dismiss a previously shown result dialog."""
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        app._handle_game_ended(
            GameEndedEvent(
                winner="Draw", reason="agreement", message="Draw by agreement."
            )
        )

        self.assertEqual(len(page.overlay), 1)

        app._handle_game_started(GameStartedEvent())

        self.assertFalse(app.result_dialog.open)
        self.assertEqual(len(page.overlay), 0)

    # --- E2: Route transitions ---

    def test_navigate_to_home_does_not_crash(self):
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        try:
            app._navigate_to("/home")
        except Exception:
            self.fail("_navigate_to('/home') raised unexpectedly")

        self.assertIs(app.view_container.content, app.home_view)

    def test_navigate_to_game_does_not_crash(self):
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        try:
            app._navigate_to("/game")
        except Exception:
            self.fail("_navigate_to('/game') raised unexpectedly")

        self.assertIs(app.view_container.content, app.game_page_view)

    def test_navigate_to_settings_does_not_crash(self):
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        try:
            app._navigate_to("/settings")
        except Exception:
            self.fail("_navigate_to('/settings') raised unexpectedly")

        self.assertIs(app.view_container.content, app.settings_view)

    def test_navigate_to_unknown_route_falls_back_to_home(self):
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        try:
            app._navigate_to("/nonexistent")
        except Exception:
            self.fail("_navigate_to('/nonexistent') raised unexpectedly")

        self.assertIs(app.view_container.content, app.home_view)

    # --- E3: Full Play→Game flow ---

    def test_start_game_with_time_control_navigates_to_game(self):
        """Full Play button flow: set clock, reset board, navigate to /game."""
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        app._start_game_with_time_control((5, 3))

        self.assertEqual(app.time_control_UI.time_control, (5, 3))
        self.assertIs(app.view_container.content, app.game_page_view)
        self.assertEqual(page.route, "/game")

    def test_navigation_tab_shows_game_view_without_crashing(self):
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)
        page.navigation_bar.selected_index = 1

        event = type("NavEvent", (), {"control": page.navigation_bar})()
        app._handle_navigation_change(event)

        self.assertIs(app.view_container.content, app.game_page_view)
        self.assertEqual(page.route, "/game")

    def test_multiple_rapid_navigations_do_not_crash(self):
        """Rapid route switching must not drop the WebSocket connection."""
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        try:
            for route in ["/home", "/game", "/settings", "/home", "/game"]:
                app._navigate_to(route)
        except Exception:
            self.fail("Rapid navigations raised unexpectedly")


class TestErrorBoundaries(unittest.TestCase):
    """Error boundaries must catch exceptions and log them, not crash."""

    def setUp(self):
        self._original_emit = bus.emit
        bus.emit = lambda _event: None

    def tearDown(self):
        bus.emit = self._original_emit

    def test_broken_page_update_does_not_propagate(self):
        """safe_update must tolerate RuntimeError from detached controls."""
        page = _CrashOnEmptyPopPage()
        ChessApp(page, dev_mode=False)

        original_update = page.update
        page.update = lambda: (_ for _ in ()).throw(RuntimeError("detached"))

        try:
            safe_update(page)
        except Exception:
            self.fail("safe_update raised unexpectedly with broken page")

        page.update = original_update

    def test_pop_dialog_never_raises_from_event_handler(self):
        """_handle_game_started must catch any pop_dialog error."""
        page = _CrashOnEmptyPopPage()
        app = ChessApp(page, dev_mode=False)

        original_pop = page.pop_dialog
        call_count = 0

        def crashing_pop():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("overlay unavailable")

        page.pop_dialog = crashing_pop
        page.overlay = []

        try:
            app._handle_game_started(GameStartedEvent())
        except Exception:
            self.fail("_handle_game_started raised despite error boundary")

        self.assertEqual(call_count, 1)
        page.pop_dialog = original_pop


if __name__ == "__main__":
    unittest.main()
