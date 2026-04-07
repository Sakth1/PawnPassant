import threading
from typing import Callable, Optional

class Clock():
    """
    The clock time control backend module.
    Courtesy of https://github.com/omamkaz/flet-timer for example.
    """
    def __init__(self, interval: float=0.01, callback: Optional[Callable]=None):
        self.interval: float = interval
        self.callback: Optional[Callable] = callback
        self.active: bool = False
        self.paused: bool = False
        self.pause_condition: threading.Condition = threading.Condition()
        self.clock_thread = threading.Thread(target=self.tick, daemon=True)

    def start(self):
        self.active = True
        if not self.clock_thread.is_alive():
            self.clock_thread.start()

    def pause(self):
        with self.pause_condition:
            self.paused = True

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

            threading.Event().wait(self.interval)