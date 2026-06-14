"""View lifecycle mixin for route-based views.

Each view that can be displayed as a route should inherit from
``ViewLifecycle`` and implement ``on_enter`` / ``on_exit``.

The :class:`RouteManager` calls these hooks when navigating::

    old_view.on_exit()   # called BEFORE detaching old view
    new_view.on_enter()  # called AFTER  attaching new view to page tree

This guarantees that services (clock, board interactions) only activate
when the view is actually mounted and visible to the user.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class ViewLifecycle(Protocol):
    """Protocol for views that participate in route lifecycle.

    Implementations are expected to be :class:`~flet.Control` subclasses
    that are used as route views.  The default implementation is a no-op.
    """

    def on_enter(self) -> None:
        """Called after this view is attached to the page tree.

        Start heavyweight services (timers, event listeners) here.
        """

    def on_exit(self) -> None:
        """Called before this view is detached from the page tree.

        Stop services, save draft state, tear down subscriptions here.
        """


class LifecycleAdapter:
    """Wraps a control with lifecycle management.

    Controls that *cannot* inherit from ``ViewLifecycle`` (e.g. third-party
    controls or classes with a different base) can be adapted::

        adapter = LifecycleAdapter(my_control)
        adapter.on_enter = lambda: start_my_service()
        adapter.on_exit  = lambda: stop_my_service()
    """

    def __init__(self, control) -> None:
        self._control = control
        self.on_enter = _noop
        self.on_exit = _noop

    def __getattr__(self, name):
        return getattr(self._control, name)


def _noop() -> None:
    pass
