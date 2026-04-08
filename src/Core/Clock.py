import threading
from datetime import datetime
from typing import Callable, Optional, Tuple


class Clock:
    """
    The clock time control backend module. Returns two clock control for both players.
    """

    def __init__(self, time_control: Tuple[int, int]):
        self.time_control: Tuple[int, int] = time_control
        self.setup_ticker()

    def setup_ticker(self):
        self.time_remaining: int = self.time_control[0]
        self.increment: int = self.time_control[1]

        self.white_ticker: Ticker = Ticker()
        self.black_ticker: Ticker = Ticker()

    def start(self):
        pass
    
        

class Ticker:
    """
    Courtesy of https://github.com/omamkaz/flet-timer for example.
    """

    def __init__(self, starting_time: int = 0, increment: int = 0, tick_interval: float = 0.01, callback: Optional[Callable] = None):
        self.remaining_time_sec: float = starting_time * 60.0
        self.increment: int = increment
        self.tick_interval: float = tick_interval
        self.callback: Optional[Callable] = callback
        self.active: bool = False
        self.paused: bool = False
        self.pause_condition: threading.Condition = threading.Condition()
        self.ticker_thread = threading.Thread(target=self.tick, daemon=True)

    def start(self):
        self.active = True
        if not self.ticker_thread.is_alive():
            self.ticker_thread.start()

    def pause(self):
        with self.pause_condition:
            self.paused = True

    def yeld_time(self):
        while self.active:
            yield 

    def resume(self):
        with self.pause_condition:
            self.paused = False
            # Notify the condition to resume the loop
            self.pause_condition.notify()

    def tick(self):
        while self.active:
            with self.pause_condition:
                if self.paused:
                    self.pause_condition.wait()
                if not self.active:
                    break
            if self.callback is not None:
                self.callback()

            self.remaining_time_sec -= self.tick_interval
