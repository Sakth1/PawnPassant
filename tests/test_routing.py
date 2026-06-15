"""Unit tests for ui.routing — RouteManager registration, navigation, lifecycle."""

import unittest
from unittest.mock import MagicMock, Mock

from ui.routing import RouteManager


class FakePage:
    def __init__(self):
        self.width = 800
        self.height = 600
        self.run_task = MagicMock()
        self.navigate = MagicMock()
        self.push_route = MagicMock()
        self.navigation_bar = MagicMock()


class TestRouteManagerConstruction(unittest.TestCase):
    def test_creates_with_routes(self):
        page = FakePage()
        view_container = MagicMock()
        views = {"/home": MagicMock(), "/game": MagicMock()}
        rm = RouteManager(page, view_container, views)
        self.assertEqual(rm.current_route, None)
        self.assertEqual(rm._route_views, views)

    def test_creates_with_route_to_index(self):
        page = FakePage()
        view_container = MagicMock()
        views = {"/home": MagicMock(), "/game": MagicMock()}
        rti = {"/home": 0, "/game": 1}
        rm = RouteManager(page, view_container, views, rti)
        self.assertEqual(rm._route_to_index, rti)


class TestRouteManagerLifecycle(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.view_container = MagicMock()
        self.views = {"/home": MagicMock(), "/game": MagicMock()}
        self.rm = RouteManager(self.page, self.view_container, self.views)

    def test_register_on_enter(self):
        handler = MagicMock()
        self.rm.on_enter("/game", handler)
        self.assertEqual(self.rm._on_enter["/game"], handler)

    def test_register_on_exit(self):
        handler = MagicMock()
        self.rm.on_exit("/game", handler)
        self.assertEqual(self.rm._on_exit["/game"], handler)

    def test_navigate_updates_current_route(self):
        self.rm.navigate("/home")
        self.assertEqual(self.rm.current_route, "/home")

    def test_navigate_to_unknown_falls_back_to_home(self):
        self.rm.navigate("/unknown")
        self.assertEqual(self.rm.current_route, "/home")

    def test_navigate_triggers_navigate_on_page(self):
        self.rm.navigate("/home")
        self.page.navigate.assert_called_with("/home")


class TestRouteManagerSwapView(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.view_container = MagicMock()
        self.views = {"/home": MagicMock(), "/game": MagicMock()}
        self.rm = RouteManager(self.page, self.view_container, self.views)

    def test_swap_view_sets_content(self):
        self.rm.swap_view("/game")
        self.assertEqual(self.rm.current_route, "/game")

    def test_swap_view_unknown_falls_back_to_home(self):
        self.rm.swap_view("/unknown")
        self.assertEqual(self.rm.current_route, "/home")

    def test_swap_view_does_not_call_navigate(self):
        self.rm.swap_view("/game")
        self.page.navigate.assert_not_called()


class TestRouteManagerHandleRouteChange(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.view_container = MagicMock()
        self.views = {"/home": MagicMock(), "/game": MagicMock()}
        self.rm = RouteManager(self.page, self.view_container, self.views)

    def test_handles_event_with_route(self):
        event = MagicMock()
        event.route = "/game"
        self.rm.handle_route_change(event)
        self.assertEqual(self.rm.current_route, "/game")

    def test_handles_event_without_route_falls_back_to_home(self):
        event = MagicMock()
        event.route = None
        self.rm.handle_route_change(event)
        self.assertEqual(self.rm.current_route, "/home")

    def test_same_route_ignored(self):
        self.rm.current_route = "/game"
        event = MagicMock()
        event.route = "/game"
        self.rm.handle_route_change(event)


class TestRouteManagerGetCurrentView(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.view_container = MagicMock()
        self.views = {"/home": MagicMock(), "/game": MagicMock()}
        self.rm = RouteManager(self.page, self.view_container, self.views)

    def test_no_current_route_returns_none(self):
        self.assertIsNone(self.rm.get_current_view())

    def test_returns_view_for_current_route(self):
        self.rm.navigate("/game")
        view = self.rm.get_current_view()
        self.assertIs(view, self.views["/game"])


if __name__ == "__main__":
    unittest.main()
