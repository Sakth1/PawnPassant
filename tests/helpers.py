"""Shared test stubs, fakes, and utilities used across all Pawn Passant tests."""

import asyncio
import unittest

from utils.signals import bus


class FakePadding:
    def __init__(self, left=0, top=0, right=0, bottom=0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class FakeMedia:
    def __init__(self, padding=None):
        self.padding = padding or FakePadding()


class FakeWindow:
    def __init__(self):
        self.icon = None


class FakePage:
    """Minimal Flet page stub for use in all tests.

    Extend via setUp if a test needs more fidelity (e.g., shared_preferences,
    navigation bar, custom pop_dialog error behavior).
    """

    def __init__(self, width=960, height=800, padding=None, platform=None):
        self.width = width
        self.height = height
        self.window = FakeWindow()
        self.media = FakeMedia(padding=padding)
        self.platform = platform
        self.fonts = {}
        self.title = ""
        self.padding = 0
        self.spacing = 0
        self.scroll = None
        self.overlay = []
        self.on_resize = None
        self.on_media_change = None
        self.on_route_change = None
        self.controls = []
        self.route = "/home"
        self.navigation_bar = None
        self.shared_preferences = None
        self.storage_paths = None

    def add(self, control):
        self.controls.append(control)

    def update(self):
        return None

    def show_dialog(self, dialog):
        dialog.open = True
        self.overlay.append(dialog)

    def pop_dialog(self):
        if not self.overlay:
            return None
        dialog = self.overlay.pop()
        dialog.open = False
        return dialog

    def run_task(self, fn, *args):
        coro = fn(*args)
        if asyncio.iscoroutine(coro):
            return asyncio.run(coro)
        return coro

    async def push_route(self, route):
        self.route = route
        if self.on_route_change is not None:
            self.on_route_change(type("RouteEvent", (), {"route": route})())

    def go(self, route):
        self.route = route
        if self.on_route_change is not None:
            self.on_route_change(type("RouteEvent", (), {"route": route})())


class FakeSharedPreferences:
    def __init__(self, payload=None):
        self.payload = payload
        self.saved = None

    async def get(self, _key):
        return self.payload

    async def set(self, _key, value):
        self.saved = value


def fake_page_with_settings(payload=None, platform="android", support_dir=None):
    """Build a FakePage wired with shared_preferences and optional storage paths."""
    page = FakePage(platform=platform)
    page.shared_preferences = FakeSharedPreferences(payload)
    if support_dir is not None:
        page.storage_paths = type(
            "StoragePathsStub",
            (),
            {"get_application_support_directory": (lambda _self: support_dir)},
        )()
    return page


def save_bus_listeners():
    """Deep-copy current bus listeners for later restore."""
    return {
        event_type: listeners.copy() for event_type, listeners in bus._listeners.items()
    }


def restore_bus_listeners(saved):
    """Restore bus listeners from a prior save_bus_listeners() call."""
    bus._listeners = {
        event_type: listeners.copy() for event_type, listeners in saved.items()
    }


def silence_bus():
    """Replace bus.emit with a no-op, returning the original."""
    original = bus.emit
    bus.emit = lambda _event: None
    return original


class BusTestCase(unittest.TestCase):
    """Base TestCase that saves/restores bus listeners around each test."""

    def setUp(self):
        self._saved_listeners = save_bus_listeners()
        bus._listeners = {}

    def tearDown(self):
        restore_bus_listeners(self._saved_listeners)


class BusSilenceTestCase(unittest.TestCase):
    """Base TestCase that silences bus.emit around each test."""

    def setUp(self):
        self._original_emit = silence_bus()

    def tearDown(self):
        bus.emit = self._original_emit
