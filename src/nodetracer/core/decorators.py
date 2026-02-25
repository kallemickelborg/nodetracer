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
    capture_args: bool = False,
    capture_return: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a function call in a span when a trace is active.

    When ``capture_args`` is True, function arguments are recorded as the
    span's input data (``self`` is excluded for methods).  When
    ``capture_return`` is True, the return value is recorded as the span's
    output data under the key ``return_value``.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        label = name or getattr(func, "__name__", "callable")
        sig = inspect.signature(func) if capture_args else None

        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Awaitable[R]], func)

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                current_trace = get_current_trace()
                if current_trace is None:
                    return await async_func(*args, **kwargs)
                async with Span(trace=current_trace, name=label, node_type=node_type) as span:
                    if capture_args and sig is not None:
                        span.input(**_bind_args(sig, args, kwargs))
                    result = await async_func(*args, **kwargs)
                    if capture_return:
                        span.output(**_format_return(result))
                    return result

            return cast(Callable[P, R], async_wrapper)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_trace = get_current_trace()
            if current_trace is None:
                return func(*args, **kwargs)
            with Span(trace=current_trace, name=label, node_type=node_type) as span:
                if capture_args and sig is not None:
                    span.input(**_bind_args(sig, args, kwargs))
                result = func(*args, **kwargs)
                if capture_return:
                    span.output(**_format_return(result))
                return result

        return wrapper

    return decorator


def _bind_args(
    sig: inspect.Signature,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> dict[str, object]:
    """Bind positional and keyword args to parameter names, excluding ``self``."""
    try:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return {k: v for k, v in bound.arguments.items() if k != "self"}
    except TypeError:
        return dict(kwargs) if kwargs else {}


def _format_return(value: object) -> dict[str, object]:
    """Format a return value for recording as span output data."""
    if isinstance(value, dict):
        return value
    if isinstance(value, tuple) and hasattr(value, "_fields"):
        return value._asdict()  # type: ignore[union-attr]
    return {"return_value": value}
