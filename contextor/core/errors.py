"""
contextor/core/errors.py

Contextor exception hierarchy.

Exists so that control-flow signals (user cancellation) are never
swallowed by the broad `except Exception` handlers that guard against
malformed source files.
"""


class ContextorError(Exception):
    """
    Base class for every error raised deliberately by Contextor.
    """


class AnalysisCancelled(ContextorError):
    """
    Raised when the user aborts a running analysis.

    This is an expected outcome, not a failure: the presentation layer
    must report it as a cancellation rather than as a crash.
    """

    def __init__(self, message: str = "Analysis cancelled by user"):
        super().__init__(message)


def checkpoint(progress_callback, message: str, completed: int = 0, total: int = 0) -> None:
    """
    Reports progress and honours a cancellation request.

    The single place that converts the "callback returned False" protocol
    into control flow. Written out by hand at each call site, the pattern
    kept being spelled the other way - `return errors` / `return []` -
    which handed a truncated result to the caller as if the analysis had
    finished, and the GUI reported a cancelled run as a clean one.
    """

    if progress_callback and not progress_callback(completed, total, message):
        raise AnalysisCancelled()


__all__ = [
    "ContextorError",
    "AnalysisCancelled",
    "checkpoint",
]
