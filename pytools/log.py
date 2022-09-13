"""Logging utilities."""
import logging
from functools import wraps
from typing import Any, Callable, TypeVar


def set_debug(activate: bool = True):
    """Enable debug log if activate is True."""
    logging.basicConfig(
        format="%(levelname)s | %(message)s",
        level=logging.DEBUG if activate else logging.INFO,
    )


def debug(msg: Any, *args: Any):
    """Write debug log."""
    logging.debug(msg, *args)


DebugTarget = TypeVar("DebugTarget", bound=Callable)


def with_debug(f: DebugTarget) -> DebugTarget:
    """Watch `f`'s arguments and the return value."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        r = f(*args, **kwargs)
        debug("%s with %s %s returned %s", f.__name__, args, kwargs, r)
        return r

    return wrapper  # type: ignore
