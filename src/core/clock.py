import threading
import time
from typing import Optional, Tuple

from utils.models import ActiveColor
from utils.events import ClockStateEvent, ClockTickEvent
from utils.signals import bus


class Clock:
    """
    Threaded chess clock backend.

    The clock state lives on a single worker thread so the UI thread only needs to
    call `start()`, `switch()`, and `stop()` without managing its own timer loop.
    """

    def __init__(
        self,
        time_control: Tuple[int, int],
        critical_threshold_seconds: int = 10,
    ):
        self.time_control: Tuple[int, int] = time_control
        self.critical_threshold_seconds = critical_threshold_seconds
        self.active_color: ActiveColor = ActiveColor.WHITE
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._active_started_at: Optional[float] = None
        self._last_emitted_second_white: Optional[Tuple[int, int]] = None
        self._last_emitted_second_black: Optional[Tuple[int, int]] = None
        self.setup_ticker()

    def setup_ticker(self):
        self.time_remaining: int = self.time_control[0]
        self.increment: int = self.time_control[1]

        self.white_ticker: Ticker = Ticker(
            starting_time=self.time_remaining,
            increment=self.increment,
        )
        self.black_ticker: Ticker = Ticker(
            starting_time=self.time_remaining,
            increment=self.increment,
        )

    def start(self):
        should_emit_initial = False
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return

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

        if should_emit_initial:
            self._emit_clock_state("started", self.active_color)
            self._emit_ticker_event(self.white_ticker, ActiveColor.WHITE, force=True)

    def switch(self):
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
            emit_updates.extend(
                [(current_ticker, current_color), (next_ticker, next_color)]
            )

        for ticker, color in emit_updates:
            self._emit_ticker_event(ticker, color, force=True)

        if next_color is not None:
            self._emit_clock_state("switched", next_color)

    def stop(self):
        worker_thread = None
        should_emit_stopped = False
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

        if worker_thread is not None:
            worker_thread.join(timeout=1)

        with self._lock:
            self._worker_thread = None

        if should_emit_stopped:
            self._emit_clock_state("stopped", None)

    def _run_clock(self):
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
                    active_ticker.remaining_time_ms = 0
                    active_ticker.active = False
                    active_ticker.last_update_ts = None
                    self._active_started_at = None
                    flagged_color = active_color
                    should_emit = True

                if should_emit:
                    event_payload = self._build_tick_event(active_ticker, active_color)
                    self._mark_emitted_second(active_color, event_payload)

            if event_payload is not None:
                bus.emit(event_payload)
            if flagged_color is not None:
                self._emit_clock_state("flagged", flagged_color)

    def _get_active_ticker(self) -> Optional["Ticker"]:
        if self.white_ticker.active:
            return self.white_ticker
        if self.black_ticker.active:
            return self.black_ticker
        return None

    def _switch_active_color(self):
        self.active_color = (
            ActiveColor.BLACK
            if self.active_color == ActiveColor.WHITE
            else ActiveColor.WHITE
        )

    def _emit_clock_state(
        self, state: str, active_color: Optional[ActiveColor]
    ) -> None:
        bus.emit(ClockStateEvent(state=state, active_color=active_color))

    def _emit_ticker_event(
        self, ticker: "Ticker", color: ActiveColor, force: bool = False
    ) -> bool:
        with self._lock:
            if not force and not self._should_emit_for_ticker(ticker, color):
                return False
            event = self._build_tick_event(ticker, color)
            self._mark_emitted_second(color, event)
        bus.emit(event)
        return True

    def _build_tick_event(self, ticker: "Ticker", color: ActiveColor) -> ClockTickEvent:
        minutes, seconds, milliseconds = ticker.formatted_time()
        return ClockTickEvent(
            color=color,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
            is_critical=self._is_critical_time(minutes, seconds),
        )

    def _is_critical_time(self, minutes: int, seconds: int) -> bool:
        return minutes == 0 and seconds <= self.critical_threshold_seconds

    def _should_emit_for_ticker(self, ticker: "Ticker", color: ActiveColor) -> bool:
        minutes, seconds, _ = ticker.formatted_time()
        if self._is_critical_time(minutes, seconds):
            return True
        return self._get_last_emitted_second(color) != (minutes, seconds)

    def _get_last_emitted_second(self, color: ActiveColor) -> Optional[Tuple[int, int]]:
        if color == ActiveColor.WHITE:
            return self._last_emitted_second_white
        return self._last_emitted_second_black

    def _mark_emitted_second(self, color: ActiveColor, event: ClockTickEvent) -> None:
        second_key = (event.minutes, event.seconds)
        if color == ActiveColor.WHITE:
            self._last_emitted_second_white = second_key
            return
        self._last_emitted_second_black = second_key


class Ticker:
    def __init__(
        self,
        starting_time: int = 0,
        increment: int = 0,
        tick_interval: int = 10,
    ):
        self.remaining_time_ms: int = starting_time * 60000
        self.increment: int = increment
        self.tick_interval: int = tick_interval
        self.active: bool = False
        self.last_update_ts: Optional[float] = None

    def update_remaining_time(self, now: float):
        if self.last_update_ts is None:
            return

        elapsed_ms = int((now - self.last_update_ts) * 1000)
        if elapsed_ms <= 0:
            return

        self.remaining_time_ms = max(0, self.remaining_time_ms - elapsed_ms)
        self.last_update_ts = now

    def formatted_time(self) -> Tuple[int, int, int]:
        minutes: int = self.remaining_time_ms // 60000
        seconds: int = (self.remaining_time_ms % 60000) // 1000
        return (minutes, seconds, self.remaining_time_ms % 1000)
