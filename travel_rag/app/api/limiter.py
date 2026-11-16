"""A small in-process limiter for the demo agent route.

Two rules protect a single local model from being hammered through a tunnel:
one run at a time, and at most `max_runs` starts in any `per_seconds` window.
Both are global: there is no authenticated caller to count against, and client
addresses behind a tunnel are not reliable.

It is single-process state. It is safe under one asyncio event loop because
`try_start` never awaits between checking and updating. Several workers or hosts
would each have their own counter, so a real deployment would use a shared store
or the gateway's rate limiting instead.
"""
import time
from collections import deque
from collections.abc import Callable


class RunLimiter:
    def __init__(
        self,
        max_runs: int,
        per_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_runs = max_runs
        self._per_seconds = per_seconds
        self._clock = clock
        self._starts: deque[float] = deque()
        self._busy = False

    def try_start(self) -> tuple[str, int] | None:
        """Claim a run. Returns None if allowed, else (reason, retry_after_seconds)."""
        now = self._clock()
        while self._starts and now - self._starts[0] >= self._per_seconds:
            self._starts.popleft()
        if self._busy:
            return "another run is in progress", 5
        if len(self._starts) >= self._max_runs:
            wait = self._per_seconds - (now - self._starts[0])
            return f"limit of {self._max_runs} runs per {int(self._per_seconds)} seconds reached", max(1, round(wait))
        self._starts.append(now)
        self._busy = True
        return None

    def finish(self) -> None:
        self._busy = False
