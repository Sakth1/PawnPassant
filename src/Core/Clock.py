import asyncio
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass(frozen=True)
class ClockColor:
    white: str = "white"
    black: str = "black"


class Clock:
    """
    The clock time control backend module. Returns two clock control for both players.
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

    async def start(self):
        await self.white_ticker.start()
        await self.black_ticker.start(wait_on_start=True)

    async def switch(self):
        self._switch_active_color()
        if self.active_color == ClockColor.white:
            await self.black_ticker._pause()
            await self.white_ticker._resume()
        else:
            await self.white_ticker._pause()
            await self.black_ticker._resume()

    async def stop(self):
        await self.white_ticker.stop()
        await self.black_ticker.stop()

    def _switch_active_color(self):
        self.active_color = (
            ClockColor.black
            if self.active_color == ClockColor.white
            else ClockColor.white
        )


class Ticker:
    """
    Courtesy of https://github.com/omamkaz/flet-timer for example.
    """

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
        self.pause_condition = asyncio.Event()
        self.ticker_task: Optional[asyncio.Task] = None
        self._last_update_ts: Optional[float] = None

    async def start(self, wait_on_start: bool = False):
        self.active = True
        if self.ticker_task is None or self.ticker_task.done():
            self.ticker_task = asyncio.create_task(self.tick())

        if wait_on_start:
            self.pause_condition.clear()
            self._last_update_ts = None
            return

        await self._resume()

    async def _pause(self):
        if not self.active or not self.pause_condition.is_set():
            return

        self._update_remaining_time()
        if self.remaining_time_ms > 0:
            self.remaining_time_ms += self.increment * 1000

        self.pause_condition.clear()
        self._last_update_ts = None
        self._emit_callback()

    async def _resume(self):
        if not self.active or self.pause_condition.is_set() or self.remaining_time_ms <= 0:
            return

        self._last_update_ts = asyncio.get_running_loop().time()
        self.pause_condition.set()
        self._emit_callback()

    async def stop(self):
        self.active = False
        self.pause_condition.set()

        if self.ticker_task is None:
            return

        self.ticker_task.cancel()
        try:
            await self.ticker_task
        except asyncio.CancelledError:
            pass
        finally:
            self.ticker_task = None
            self._last_update_ts = None

    async def tick(self):
        try:
            while self.active and self.remaining_time_ms > 0:
                await self.pause_condition.wait()
                if not self.active:
                    break

                await asyncio.sleep(self.tick_interval / 1000)
                if not self.pause_condition.is_set():
                    continue

                self._update_remaining_time()
                self._emit_callback()
        except asyncio.CancelledError:
            raise
        finally:
            if self.remaining_time_ms <= 0:
                self.remaining_time_ms = 0
                self.pause_condition.clear()
                self._last_update_ts = None
                self._emit_callback()

    def _update_remaining_time(self):
        if self._last_update_ts is None:
            return

        now = asyncio.get_running_loop().time()
        elapsed_ms = int((now - self._last_update_ts) * 1000)
        if elapsed_ms <= 0:
            return

        self.remaining_time_ms = max(0, self.remaining_time_ms - elapsed_ms)
        self._last_update_ts = now

    def _emit_callback(self):
        if self.callback is not None:
            self.callback(*self._formatted_time())

    def _formatted_time(self):
        min = self.remaining_time_ms // 60000
        sec = (self.remaining_time_ms % 60000) // 1000
        return (min, sec, self.remaining_time_ms % 1000)


if __name__ == "__main__":

    def white_clock_callback(min, sec, ms):
        print(f"White: {min}:{sec}.{ms}")

    def black_clock_callback(min, sec, ms):
        print(f"Black: {min}:{sec}.{ms}")

    async def main():
        clock = Clock(
            time_control=(10, 0),
            white_clock_callback=white_clock_callback,
            black_clock_callback=black_clock_callback,
        )
        await clock.start()
        await asyncio.sleep(5)
        await clock.switch()
        await asyncio.sleep(3)
        await clock.switch()
        await asyncio.sleep(1)
        await clock.stop()

    asyncio.run(main())
