"""Function decorators for span instrumentation."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from .context import get_current_trace
from .span import Span

P = ParamSpec("P")
R = TypeVar("R")


def trace_node(
    name: str | None = None,
    node_type: str = "custom",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a function call in a span when a trace is active."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        label = name or getattr(func, "__name__", "callable")

        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Awaitable[R]], func)

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                current_trace = get_current_trace()
                if current_trace is None:
                    return await async_func(*args, **kwargs)
                async with Span(trace=current_trace, name=label, node_type=node_type):
                    return await async_func(*args, **kwargs)

            return cast(Callable[P, R], async_wrapper)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_trace = get_current_trace()
            if current_trace is None:
                return func(*args, **kwargs)
            with Span(trace=current_trace, name=label, node_type=node_type):
                return func(*args, **kwargs)

        return wrapper

    return decorator
