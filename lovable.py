"""Lovable credit gating for the Behavioural Forecasting Engine.

Credits are read from the LOVABLE_CREDITS environment variable (default: 100).
Each heavy node checks and consumes credits via this module before executing.
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)


class InsufficientCreditsError(RuntimeError):
    """Raised when a heavy node cannot proceed due to insufficient credits."""


class _LovableContext:
    def __init__(self) -> None:
        self._credits: int = int(os.getenv("LOVABLE_CREDITS", "100"))
        self._lock = threading.Lock()

    @property
    def credits(self) -> int:
        return self._credits

    def has_credits(self, n: int = 1) -> bool:
        with self._lock:
            return self._credits >= n

    def use_credits(self, n: int, reason: str = "") -> None:
        with self._lock:
            if self._credits < n:
                raise InsufficientCreditsError(
                    f"Need {n} credit(s) for {reason!r}; have {self._credits}"
                )
            self._credits -= n
        logger.info(
            "event=credits_consumed node=%s amount=%d remaining=%d",
            reason,
            n,
            self._credits,
        )

    def reset(self, n: int) -> None:
        """Reset credit balance. Use in tests or when Lovable tops up the account."""
        with self._lock:
            self._credits = n
        logger.info("event=credits_reset amount=%d", n)


# Module-level singleton — all nodes share this context.
context = _LovableContext()


def has_credits(n: int = 1) -> bool:
    return context.has_credits(n)


def use_credits(n: int, reason: str = "") -> None:
    context.use_credits(n, reason)
