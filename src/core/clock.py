"""Threaded chess clock backend.

The UI should not own a tight timer loop, because Flet controls need to remain
responsive and are updated through page tasks. This module keeps time on a small
daemon worker thread, emits coarse updates outside critical time, and emits
high-frequency updates only when milliseconds matter.
"""

import logging
import threading
import time
from typing import Optional, Tuple

from utils.models import ActiveColor
from utils.events import ClockStateEvent, ClockTickEvent
from utils.signals import bus

logger = logging.getLogger(__name__)


class Clock:
    """Manage both player timers and publish clock events.

    Args:
        time_control: ``(minutes, increment_seconds)`` pair used for both sides.
        critical_threshold_seconds: Remaining seconds at which tick events should
            include high-frequency millisecond updates.

    Side Effects:
        Emits :class:`utils.events.ClockTickEvent` and
        :class:`utils.events.ClockStateEvent` on the shared signal bus.
    """

    def __init__(
        self,
        time_control: Tuple[int, int],
        critical_threshold_seconds: int = 10,
    ):
        #: Original time control used when a new game starts.
        self.time_control: Tuple[int, int] = time_control
        #: Threshold for switching from second-level to millisecond-level ticks.
        self.critical_threshold_seconds = critical_threshold_seconds
        #: Side whose clock is currently counting down.
        self.active_color: ActiveColor = ActiveColor.WHITE
        #: Guards ticker state because the UI thread and worker thread both act.
        self._lock = threading.RLock()
        #: Cooperative stop signal checked by the worker loop.
        self._stop_event = threading.Event()
        #: Daemon thread that decrements the active ticker.
        self._worker_thread: Optional[threading.Thread] = None
        #: Perf-counter timestamp for when the active ticker last resumed.
        self._active_started_at: Optional[float] = None
        #: Last emitted ``(minutes, seconds)`` for white to avoid redundant UI work.
        self._last_emitted_second_white: Optional[Tuple[int, int]] = None
        #: Last emitted ``(minutes, seconds)`` for black to avoid redundant UI work.
        self._last_emitted_second_black: Optional[Tuple[int, int]] = None
        #: Tracks whether ticker objects exist so new games can reuse controls.
        self._tickers_initialized = False
        self.setup_ticker()

    def setup_ticker(self):
        """Create or reset the side tickers from the current time control."""

        initial_time_ms = self.time_control[0] * 60000
        increment = self.time_control[1]
        logger.debug(
            "Setting up tickers minutes=%s increment_seconds=%s",
            self.time_control[0],
            increment,
        )

        # Create tickers on first call
        if not self._tickers_initialized:
            self.white_ticker: Ticker = Ticker(
                starting_time=self.time_control[0],
                increment=increment,
            )
            self.black_ticker: Ticker = Ticker(
                starting_time=self.time_control[0],
                increment=increment,
            )
            self._tickers_initialized = True
        else:
            # Reset ticker times on subsequent calls so existing references keep
            # working while a new game starts from the configured base time.
            self.white_ticker.remaining_time_ms = initial_time_ms
            self.black_ticker.remaining_time_ms = initial_time_ms

        #: Increment, in seconds, added to a side after it completes a move.
        self.increment: int = increment

    def start(self):
        """Start white's clock and spawn the worker thread if needed."""

        should_emit_initial = False
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return

            self.setup_ticker()
            self._stop_event.clear()
            self.active_color = ActiveColor.WHITE
            self._last_emitted_second_white = None
            self._last_emitted_second_black = None
            self.white_ticker.active = True
            self.black_ticker.active = False
            now = time.perf_counter()
            self.white_ticker.last_update_ts = now
            self.black_ticker.last_update_ts = None
            self._active_started_at = now

            self._worker_thread = threading.Thread(
                target=self._run_clock,
                name="pawnpassant-clock",
                daemon=True,
            )
            self._worker_thread.start()
            should_emit_initial = True
            logger.info(
                "Clock started minutes=%s increment_seconds=%s",
                self.time_control[0],
                self.increment,
            )

        if should_emit_initial:
            # Emit outside the lock so subscribers can react without being tied
            # to clock internals or risking re-entrant lock surprises.
            self._emit_clock_state("started", self.active_color)
            self._emit_ticker_event(self.white_ticker, ActiveColor.WHITE, force=True)

    def switch(self):
        """Stop the active side, apply increment, and resume the opponent clock."""

        emit_updates: list[tuple[Ticker, ActiveColor]] = []
        next_color: Optional[ActiveColor] = None
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                return

            current_ticker = self._get_active_ticker()
            if current_ticker is None:
                return

            current_color = self.active_color
            next_ticker = (
                self.black_ticker
                if current_ticker is self.white_ticker
                else self.white_ticker
            )
            next_color = (
                ActiveColor.BLACK
                if current_color == ActiveColor.WHITE
                else ActiveColor.WHITE
            )

            current_ticker.update_remaining_time(time.perf_counter())
            # Increment is applied after the side moves, matching common chess
            # clock behavior and avoiding bonus time for a player who flags.
            if current_ticker.remaining_time_ms > 0:
                current_ticker.remaining_time_ms += current_ticker.increment * 1000
            current_ticker.active = False
            current_ticker.last_update_ts = None

            if next_ticker.remaining_time_ms > 0:
                resume_at = time.perf_counter()
                next_ticker.active = True
                next_ticker.last_update_ts = resume_at
                self._active_started_at = resume_at
            else:
                next_ticker.active = False
                next_ticker.last_update_ts = None
                self._active_started_at = None

            self._switch_active_color()
            logger.info(
                "Clock switched from_color=%s to_color=%s remaining_ms=%s",
                current_color,
                next_color,
                next_ticker.remaining_time_ms,
            )
            emit_updates.extend(
                [(current_ticker, current_color), (next_ticker, next_color)]
            )

        for ticker, color in emit_updates:
            self._emit_ticker_event(ticker, color, force=True)

        if next_color is not None:
            self._emit_clock_state("switched", next_color)

    def stop(self):
        """Stop the worker thread and publish a stopped state when active."""

        worker_thread = None
        should_emit_stopped = False
        current_thread = threading.current_thread()
        with self._lock:
            if self._worker_thread is None:
                return
            self._stop_event.set()
            self.white_ticker.active = False
            self.black_ticker.active = False
            self.white_ticker.last_update_ts = None
            self.black_ticker.last_update_ts = None
            self._active_started_at = None
            worker_thread = self._worker_thread
            should_emit_stopped = True
            logger.info("Clock stopping")

        # A flag fall may stop the clock from inside the worker. Joining the
        # current thread would deadlock, so only external callers wait.
        if worker_thread is not None and worker_thread is not current_thread:
            worker_thread.join(timeout=1)

        with self._lock:
            self._worker_thread = None

        if should_emit_stopped:
            self._emit_clock_state("stopped", None)
            logger.info("Clock stopped")

    def _run_clock(self):
        """Worker loop that decrements the active ticker and emits due events."""

        tick_seconds = (
            min(self.white_ticker.tick_interval, self.black_ticker.tick_interval) / 1000
        )

        while not self._stop_event.wait(tick_seconds):
            event_payload = None
            flagged_color = None
            with self._lock:
                active_ticker = self._get_active_ticker()
                if active_ticker is None:
                    continue

                active_ticker.update_remaining_time(time.perf_counter())
                active_color = self.active_color
                should_emit = self._should_emit_for_ticker(active_ticker, active_color)

                if active_ticker.remaining_time_ms <= 0:
                    # Clamp at exactly zero so UI and tests never see negative
                    # time caused by scheduler delay between worker ticks.
                    active_ticker.remaining_time_ms = 0
                    active_ticker.active = False
                    active_ticker.last_update_ts = None
                    self._active_started_at = None
                    flagged_color = active_color
                    should_emit = True
                    logger.info("Clock flagged color=%s", flagged_color)

                if should_emit:
                    event_payload = self._build_tick_event(active_ticker, active_color)
                    self._mark_emitted_second(active_color, event_payload)

            if event_payload is not None:
                bus.emit(event_payload)
            if flagged_color is not None:
                self._emit_clock_state("flagged", flagged_color)

    def _get_active_ticker(self) -> Optional["Ticker"]:
        """Return the ticker currently counting down, if either clock is active."""

        if self.white_ticker.active:
            return self.white_ticker
        if self.black_ticker.active:
            return self.black_ticker
        return None

    def _switch_active_color(self):
        """Toggle :attr:`active_color` after a legal move switches turns."""

        self.active_color = (
            ActiveColor.BLACK
            if self.active_color == ActiveColor.WHITE
            else ActiveColor.WHITE
        )

    def _emit_clock_state(
        self, state: str, active_color: Optional[ActiveColor]
    ) -> None:
        """Publish a lifecycle or flag-fall event."""

        bus.emit(ClockStateEvent(state=state, active_color=active_color))
        logger.debug(
            "Clock state emitted state=%s active_color=%s",
            state,
            active_color,
        )

    def _emit_ticker_event(
        self, ticker: "Ticker", color: ActiveColor, force: bool = False
    ) -> bool:
        """Emit one ticker event when cadence rules allow it.

        Args:
            ticker: Side ticker whose current value should be rendered.
            color: Side represented by ``ticker``.
            force: Whether to bypass cadence throttling.

        Returns:
            ``True`` when an event was emitted; otherwise ``False``.
        """

        with self._lock:
            if not force and not self._should_emit_for_ticker(ticker, color):
                return False
            event = self._build_tick_event(ticker, color)
            self._mark_emitted_second(color, event)
        bus.emit(event)
        return True

    def _build_tick_event(self, ticker: "Ticker", color: ActiveColor) -> ClockTickEvent:
        """Create the immutable bus payload for the ticker's current time."""

        minutes, seconds, milliseconds = ticker.formatted_time()
        return ClockTickEvent(
            color=color,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
            is_critical=self._is_critical_time(minutes, seconds),
        )

    def _is_critical_time(self, minutes: int, seconds: int) -> bool:
        """Return whether the displayed time should include critical detail."""

        return minutes == 0 and seconds <= self.critical_threshold_seconds

    def _should_emit_for_ticker(self, ticker: "Ticker", color: ActiveColor) -> bool:
        """Throttle normal ticks while allowing every critical-time worker tick."""

        minutes, seconds, _ = ticker.formatted_time()
        if self._is_critical_time(minutes, seconds):
            return True
        return self._get_last_emitted_second(color) != (minutes, seconds)

    def _get_last_emitted_second(self, color: ActiveColor) -> Optional[Tuple[int, int]]:
        """Return the last second-level display value emitted for ``color``."""

        if color == ActiveColor.WHITE:
            return self._last_emitted_second_white
        return self._last_emitted_second_black

    def _mark_emitted_second(self, color: ActiveColor, event: ClockTickEvent) -> None:
        """Remember the latest second-level display value for cadence throttling."""

        second_key = (event.minutes, event.seconds)
        if color == ActiveColor.WHITE:
            self._last_emitted_second_white = second_key
            return
        self._last_emitted_second_black = second_key


class Ticker:
    """Mutable countdown state for one side of the chess clock."""

    def __init__(
        self,
        starting_time: int = 0,
        increment: int = 0,
        tick_interval: int = 10,
    ):
        #: Remaining clock time in milliseconds.
        self.remaining_time_ms: int = starting_time * 60000
        #: Increment, in seconds, added after this side completes a move.
        self.increment: int = increment
        #: Worker polling interval in milliseconds.
        self.tick_interval: int = tick_interval
        #: Whether this side is currently counting down.
        self.active: bool = False
        #: Perf-counter timestamp of the most recent countdown update.
        self.last_update_ts: Optional[float] = None

    def update_remaining_time(self, now: float):
        """Subtract elapsed wall-clock time from this ticker.

        Args:
            now: Current ``time.perf_counter()`` value supplied by the clock.
        """

        if self.last_update_ts is None:
            return

        elapsed_ms = int((now - self.last_update_ts) * 1000)
        if elapsed_ms <= 0:
            return

        self.remaining_time_ms = max(0, self.remaining_time_ms - elapsed_ms)
        self.last_update_ts = now

    def formatted_time(self) -> Tuple[int, int, int]:
        """Return ``(minutes, seconds, milliseconds)`` for display/events."""

        minutes: int = self.remaining_time_ms // 60000
        seconds: int = (self.remaining_time_ms % 60000) // 1000
        return (minutes, seconds, self.remaining_time_ms % 1000)
