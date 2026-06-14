"""Synchronous event bus with error isolation and disconnect support.

Flet controls in this app often need to react to the same game event without
holding direct references to each other. A tiny in-process bus is enough for
that job: events are emitted on the UI process and delivered immediately to
registered listeners.

Key improvements over the original design:

* **Per-handler error isolation** — one failing listener never kills others.
* **``disconnect()``** — removes a previously registered listener so stale
  handlers do not accumulate across repeated game sessions.
"""

import logging

logger = logging.getLogger(__name__)


class SignalBus:
    """Dispatch events to callbacks registered by exact event type."""

    def __init__(self):
        """Initialize the listener registry."""

        self._listeners = {}

    def connect(self, event_type, fn):
        """Register ``fn`` to be called whenever ``event_type`` is emitted."""

        self._listeners.setdefault(event_type, []).append(fn)
        logger.debug("Signal listener connected event_type=%s", event_type.__name__)

    def disconnect(self, event_type, fn):
        """Remove a previously registered listener.

        Uses identity comparison (``is``) so that bound methods and lambdas
        are matched correctly when the same object is passed for removal.

        Raises ``ValueError`` if *fn* was not registered for *event_type*.
        """

        listeners = self._listeners.get(event_type, [])
        # Find by identity (``is``), not equality (``==``).
        for i, registered in enumerate(listeners):
            if registered is fn:
                del listeners[i]
                logger.debug(
                    "Signal listener disconnected event_type=%s", event_type.__name__
                )
                return
        raise ValueError(
            f"Listener {fn!r} not found for event type {event_type.__name__}"
        )

    def emit(self, event):
        """Synchronously deliver ``event`` to listeners of its concrete class.

        Each listener runs inside its own try/except so that a single broken
        handler never prevents other handlers from receiving the event.
        """

        event_type = type(event)
        listeners = list(self._listeners.get(event_type, []))
        logger.debug(
            "Signal emitted event_type=%s listener_count=%s",
            event_type.__name__,
            len(listeners),
        )

        for fn in listeners:
            try:
                fn(event)
            except Exception:
                logger.exception(
                    "Signal handler failed event_type=%s handler=%s",
                    event_type.__name__,
                    fn.__name__ if hasattr(fn, "__name__") else str(fn),
                )


# Shared app-wide bus. Components import this singleton instead of owning each
# other directly, which keeps board, clock, settings, and dialogs loosely coupled.
bus = SignalBus()
