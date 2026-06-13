"""Minimal synchronous event bus used to decouple UI controls.

Flet controls in this app often need to react to the same game event without
holding direct references to each other. A tiny in-process bus is enough for
that job: events are emitted on the UI process and delivered immediately to
registered listeners.
"""

import logging

logger = logging.getLogger(__name__)


class SignalBus:
    """Dispatch events to callbacks registered by exact event type."""

    def __init__(self):
        """Initialize the listener registry.

        The registry is intentionally simple because tests often replace it to
        isolate event-driven behavior.
        """

        self._listeners = {}

    def connect(self, event_type, fn):
        """Register ``fn`` to be called whenever ``event_type`` is emitted."""

        self._listeners.setdefault(event_type, []).append(fn)
        logger.debug("Signal listener connected event_type=%s", event_type.__name__)

    def emit(self, event):
        """Synchronously deliver ``event`` to listeners of its concrete class."""

        event_type = type(event)
        listeners = self._listeners.get(event_type, [])
        logger.debug(
            "Signal emitted event_type=%s listener_count=%s",
            event_type.__name__,
            len(listeners),
        )

        for fn in listeners:
            fn(event)


# Shared app-wide bus. Components import this singleton instead of owning each
# other directly, which keeps board, clock, settings, and dialogs loosely coupled.
bus = SignalBus()
