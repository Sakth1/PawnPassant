import threading
from typing import Callable, Optional, Tuple
from dataclasses import dataclass


@dataclass(frozen=True)
class ClockColor:
    white: str = "white"
    black: str = "black"

class Clock:
    """
    The clock time control backend module. Returns two clock control for both players.
    """

    def __init__(self, time_control: Tuple[int, int], white_clock_callback: Optional[Callable] = None, black_clock_callback: Optional[Callable] = None):
        self.time_control: Tuple[int, int] = time_control
        self.white_clock_callback: Optional[Callable] = white_clock_callback
        self.black_clock_callback: Optional[Callable] = black_clock_callback
        self.active_color: ClockColor = ClockColor.white
        self.setup_ticker()

    def setup_ticker(self):
        self.time_remaining: int = self.time_control[0]
        self.increment: int = self.time_control[1]

        self.white_ticker: Ticker = Ticker(starting_time=self.time_remaining, increment=self.increment, callback=self.white_clock_callback)
        self.black_ticker: Ticker = Ticker(starting_time=self.time_remaining, increment=self.increment, callback=self.black_clock_callback)

    def start(self):
        self.white_ticker.start()
        self.black_ticker.start(wait_on_start=True)

    def switch(self):
        self._switch_active_color()
        if self.active_color == ClockColor.white:
            self.white_ticker._pause()
            self.black_ticker._resume()
        else:
            self.white_ticker._resume()
            self.black_ticker._pause()

    def _switch_active_color(self):
        self.active_color = ClockColor.black if self.active_color == ClockColor.white else ClockColor.white    
        

class Ticker:
    """
    Courtesy of https://github.com/omamkaz/flet-timer for example.
    """

    def __init__(self, starting_time: int = 0, increment: int = 0, tick_interval: int = 10, callback: Optional[Callable] = None):
        self.remaining_time_ms: int = starting_time * 60000
        self.increment: int = increment
        self.tick_interval: int = tick_interval
        self.callback: Optional[Callable] = callback
        self.active: bool = False
        self.paused: bool = False
        self.pause_condition: threading.Condition = threading.Condition()
        self.ticker_thread = threading.Thread(target=self.tick)

    def start(self, wait_on_start: bool = False):
        self.active = True
        if not wait_on_start and not self.ticker_thread.is_alive():
            self.ticker_thread.start()

    def _pause(self):
        with self.pause_condition:
            self.remaining_time_ms += self.increment
            self.paused = True

    def _resume(self):
        with self.pause_condition:
            self.paused = False
            # Notify the condition to resume the loop
            self.pause_condition.notify()

    def tick(self):
        while self.active and self.remaining_time_ms > 0:
            with self.pause_condition:
                if self.paused:
                    self.pause_condition.wait()
                if not self.active:
                    break
            if self.callback is not None:
                self.callback(*self._formated_time())

            self.remaining_time_ms -= self.tick_interval

    def _formated_time(self):
        min = self.remaining_time_ms // 60000
        sec = (self.remaining_time_ms % 60000) // 1000
        return (min, sec, self.remaining_time_ms % 1000)

if __name__ == "__main__":
    def white_clock_callback(min, sec, ms):
        print(f"White: {min}:{sec}.{ms}")

    def black_clock_callback(min, sec, ms):
        print(f"Black: {min}:{sec}.{ms}")

    clock = Clock(time_control=(10, 0), white_clock_callback=white_clock_callback, black_clock_callback=black_clock_callback)
    clock.start()
    import time
    time.sleep(5)
    clock.switch()
    time.sleep(3)
    clock.switch()
    breakpoint()