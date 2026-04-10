import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass(frozen=True)
class ClockColor:
    white: str = "white"
    black: str = "black"


class Clock:
    """
    Threaded chess clock backend.

    The clock state lives on a single worker thread so the UI thread only needs to
    call `start()`, `switch()`, and `stop()` without managing its own timer loop.
    """

    def __init__(
        self,
        time_control: Tuple[int, int],
        white_clock_callback: Optional[Callable] = None,
        black_clock_callback: Optional[Callable] = None,
    ):
        self.time_control: Tuple[int, int] = time_control
        self.white_clock_callback: Optional[Callable] = white_clock_callback
        self.black_clock_callback: Optional[Callable] = black_clock_callback
        self.active_color: ClockColor = ClockColor.white
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._active_started_at: Optional[float] = None
        self.setup_ticker()

    def setup_ticker(self):
        self.time_remaining: int = self.time_control[0]
        self.increment: int = self.time_control[1]

        self.white_ticker: Ticker = Ticker(
            starting_time=self.time_remaining,
            increment=self.increment,
            callback=self.white_clock_callback,
        )
        self.black_ticker: Ticker = Ticker(
            starting_time=self.time_remaining,
            increment=self.increment,
            callback=self.black_clock_callback,
        )

    def start(self):
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return

            self._stop_event.clear()
            self.active_color = ClockColor.white
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

        self.white_ticker.emit_callback()

    def switch(self):
        callbacks_to_emit: list[Ticker] = []
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                return

            current_ticker = self._get_active_ticker()
            next_ticker = (
                self.black_ticker
                if current_ticker is self.white_ticker
                else self.white_ticker
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
            callbacks_to_emit.extend([current_ticker, next_ticker])

        for ticker in callbacks_to_emit:
            ticker.emit_callback()

    def stop(self):
        worker_thread = None
        with self._lock:
            self._stop_event.set()
            self.white_ticker.active = False
            self.black_ticker.active = False
            self.white_ticker.last_update_ts = None
            self.black_ticker.last_update_ts = None
            self._active_started_at = None
            worker_thread = self._worker_thread

        if worker_thread is not None:
            worker_thread.join(timeout=1)

        with self._lock:
            self._worker_thread = None

    def _run_clock(self):
        tick_seconds = (
            min(self.white_ticker.tick_interval, self.black_ticker.tick_interval) / 1000
        )

        while not self._stop_event.wait(tick_seconds):
            callback_ticker = None
            with self._lock:
                active_ticker = self._get_active_ticker()
                if active_ticker is None:
                    continue

                active_ticker.update_remaining_time(time.perf_counter())
                callback_ticker = active_ticker

                if active_ticker.remaining_time_ms <= 0:
                    active_ticker.remaining_time_ms = 0
                    active_ticker.active = False
                    active_ticker.last_update_ts = None
                    self._active_started_at = None

            if callback_ticker is not None:
                callback_ticker.emit_callback()

    def _get_active_ticker(self) -> Optional["Ticker"]:
        if self.white_ticker.active:
            return self.white_ticker
        if self.black_ticker.active:
            return self.black_ticker
        return None

    def _switch_active_color(self):
        self.active_color = (
            ClockColor.black
            if self.active_color == ClockColor.white
            else ClockColor.white
        )


class Ticker:
    def __init__(
        self,
        starting_time: int = 0,
        increment: int = 0,
        tick_interval: int = 10,
        callback: Optional[Callable] = None,
    ):
        self.remaining_time_ms: int = starting_time * 60000
        self.increment: int = increment
        self.tick_interval: int = tick_interval
        self.callback: Optional[Callable] = callback
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

    def emit_callback(self):
        if self.callback is not None:
            self.callback(*self.formatted_time())

    def formatted_time(self):
        minutes = self.remaining_time_ms // 60000
        seconds = (self.remaining_time_ms % 60000) // 1000
        return (minutes, seconds, self.remaining_time_ms % 1000)


"""if __name__ == "__main__":

    def white_clock_callback(minutes, seconds, milliseconds):
        print(f"White: {minutes}:{seconds}.{milliseconds}")

    def black_clock_callback(minutes, seconds, milliseconds):
        print(f"Black: {minutes}:{seconds}.{milliseconds}")

    clock = Clock(
        time_control=(10, 0),
        white_clock_callback=white_clock_callback,
        black_clock_callback=black_clock_callback,
    )
    clock.start()
    time.sleep(5)
    clock.switch()
    time.sleep(3)
    clock.switch()
    time.sleep(1)
    clock.stop()"""
