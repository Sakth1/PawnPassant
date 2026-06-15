"""State-machine fuzz tests for Ticker — countdown invariants under random updates."""

import time
from hypothesis import given
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition

from core.clock import Ticker
from utils.constants import MS_PER_MINUTE, MS_PER_SECOND


class TickerFuzz(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.ticker = Ticker(starting_time=10, increment=2)
        self.now = time.perf_counter()
        self.ticker.last_update_ts = self.now

    @rule()
    def update_time(self):
        self.now += 0.5  # simulate 500ms passing
        self.ticker.update_remaining_time(self.now)

    @rule()
    def update_time_large(self):
        self.now += 5.0  # simulate 5s passing
        self.ticker.update_remaining_time(self.now)

    @invariant()
    def remaining_time_non_negative(self):
        assert self.ticker.remaining_time_ms >= 0

    @invariant()
    def formatted_time_consistent(self):
        minutes, seconds, ms = self.ticker.formatted_time()
        total_from_formatted = minutes * MS_PER_MINUTE + seconds * MS_PER_SECOND + ms
        assert total_from_formatted <= self.ticker.remaining_time_ms + MS_PER_SECOND
        # Allow 1-second tolerance for formatting rounding

    @invariant()
    def minutes_seconds_in_range(self):
        minutes, seconds, ms = self.ticker.formatted_time()
        assert 0 <= seconds < 60
        assert 0 <= ms < 1000


TestTickerFuzz = TickerFuzz.TestCase
