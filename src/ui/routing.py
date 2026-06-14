"""Lifecycle-aware route manager for the Pawn Passant application.

Replaces the ad-hoc ``_navigate_to`` / ``_show_route`` pattern in ``app.py``
with a :class:`RouteManager` that calls lifecycle hooks (``on_enter`` /
``on_exit``) on route transitions.  This guarantees that heavyweight services
like the chess clock only start *after* the game view is attached to the page
tree, preventing the orphan-WebSocket-patch race that drops connections.
"""

from __future__ import annotations

import logging
from typing import Callable, Protocol

from utils.dialogs import safe_update

logger = logging.getLogger(__name__)


class LifecycleHandler(Protocol):
    """Callback signature for route lifecycle hooks."""

    def __call__(self) -> None: ...


class RouteManager:
    """Manages route transitions with lifecycle hooks and error boundaries.

    Typical usage::

        manager = RouteManager(
            page=page,
            view_container=view_container,
            route_views={"/home": home_view, "/game": game_view},
            route_to_index={"/home": 0, "/game": 1},
        )

        # Register lifecycle callbacks for the game route
        manager.on_enter("/game", my_on_enter)
        manager.on_exit("/game", my_on_exit)

        # Navigate — lifecycle hooks fire automatically
        manager.navigate("/game")
    """

    def __init__(
        self,
        page,
        view_container,
        route_views: dict[str, object],
        route_to_index: dict[str, int] | None = None,
    ):
        self._page = page
        self._view_container = view_container
        self._route_views = route_views
        self._route_to_index = route_to_index or {}
        self._on_enter: dict[str, LifecycleHandler] = {}
        self._on_exit: dict[str, LifecycleHandler] = {}
        self.current_route: str | None = None

    # ── lifecycle registration ──────────────────────────────────────────

    def on_enter(self, route: str, handler: LifecycleHandler) -> None:
        """Register a handler called *after* the view for *route* is attached."""
        self._on_enter[route] = handler

    def on_exit(self, route: str, handler: LifecycleHandler) -> None:
        """Register a handler called *before* the current view is detached."""
        self._on_exit[route] = handler

    # ── view swap (no lifecycle, no update, no navigate) ────────────────

    def swap_view(self, route: str) -> None:
        """Swap the view container content and sync nav bar.

        Unlike :meth:`navigate`, this does **not** call lifecycle hooks,
        ``page.update()``, or ``page.navigate()``.  It is intended for
        the async game-start flow where navigation is driven by
        ``page.push_route()`` directly (see ``_async_start_game`` in
        :class:`~ui.app.ChessApp`).
        """
        new_view = self._route_views.get(route)
        if new_view is None:
            logger.warning(
                "Unknown route=%s in swap_view, falling back to /home", route
            )
            route = "/home"
            new_view = self._route_views.get("/home")
        self._view_container.content = new_view
        self.current_route = route
        idx = self._route_to_index.get(route, 0)
        nav = getattr(self._page, "navigation_bar", None)
        if nav is not None:
            nav.selected_index = idx

    # ── navigation ──────────────────────────────────────────────────────

    def navigate(self, route: str) -> None:
        """Transition to *route* and fire lifecycle hooks.

        Lifecycle call order::

            current_view.on_exit()   (if any)
            ── swap view_container.content ──
            new_view.on_enter()
            ── sync navigation bar ──
            ── page.update() ──
            ── page.navigate(route) ──
        """

        try:
            new_view = self._route_views.get(route)
            if new_view is None:
                logger.warning("Unknown route=%s, falling back to /home", route)
                route = "/home"
                new_view = self._route_views.get("/home")

            old_route = self.current_route

            # Exit current view
            if old_route is not None:
                on_exit = self._on_exit.get(old_route)
                if on_exit is not None:
                    self._safe_call(on_exit)

            # Swap
            self._view_container.content = new_view
            self.current_route = route

            # Enter new view
            on_enter = self._on_enter.get(route)
            if on_enter is not None:
                self._safe_call(on_enter)

            # Sync navigation bar
            idx = self._route_to_index.get(route, 0)
            nav = getattr(self._page, "navigation_bar", None)
            if nav is not None:
                nav.selected_index = idx

            # Push route to Flet history
            safe_update(self._view_container)
            navigate = getattr(self._page, "navigate", None)
            if callable(navigate):
                navigate(route)
                return
            self._page.run_task(self._push_route, route)

        except Exception:
            logger.exception("Route transition failed route=%s", route)

    async def _push_route(self, route: str) -> None:
        """Navigate from synchronous callbacks without leaking a coroutine."""
        await self._page.push_route(route)

    def handle_route_change(self, event) -> None:
        """Handle ``page.on_route_change`` and navigate accordingly.

        If the route is already current (e.g. already set by
        :meth:`swap_view` in the async game-start flow), the event is
        silently ignored to prevent duplicate lifecycle calls.
        """
        route = getattr(event, "route", None) or "/home"
        if route == self.current_route:
            return
        self.navigate(route)

    def handle_navigation_change(self, event) -> None:
        """Handle ``page.navigation_bar.on_change`` and navigate accordingly."""
        idx = getattr(event.control, "selected_index", None)
        route_by_index = {v: k for k, v in self._route_to_index.items()}
        route = route_by_index.get(idx, "/home")
        self.navigate(route)

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _safe_call(fn: Callable[[], None]) -> None:
        """Call *fn* inside a try/except so one handler never kills navigation."""
        try:
            fn()
        except Exception:
            logger.exception("Lifecycle handler raised")

    def get_current_view(self):
        """Return the currently displayed route view, or ``None``."""
        if self.current_route is None:
            return None
        return self._route_views.get(self.current_route)
