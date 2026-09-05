"""Per-command time-budget enforcement (research.md R3)."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

T = TypeVar("T")

DEFAULT_BUDGET_SECONDS = 10.0
RISERS_BUDGET_SECONDS = 30.0


class BudgetExceededError(Exception):
    def __init__(self, budget_seconds: float):
        super().__init__(f"request exceeded its time budget ({budget_seconds:g}s)")
        self.budget_seconds = budget_seconds


def run_with_budget(fn: Callable[..., T], *args, budget_seconds: float = DEFAULT_BUDGET_SECONDS, **kwargs) -> T:
    """
    Run fn(*args, **kwargs) but never wait past budget_seconds for it.

    Deliberately does not use ThreadPoolExecutor as a context manager: `with` calls
    shutdown(wait=True) on exit, which blocks until the worker thread finishes -- exactly
    the hang this function exists to prevent. On timeout, shut down without waiting and let
    the caller decide how to exit the process (see output.timeout_failure).
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args, **kwargs)
    try:
        result = future.result(timeout=budget_seconds)
    except FutureTimeoutError as exc:
        executor.shutdown(wait=False)
        raise BudgetExceededError(budget_seconds) from exc
    executor.shutdown(wait=False)
    return result
