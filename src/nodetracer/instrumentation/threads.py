"""Thread context propagation instrumentation."""

from __future__ import annotations

import asyncio

from ..core.context import propagate_context

_original_to_thread = asyncio.to_thread
_patched = False


def instrument_threads() -> None:
    """Patch asyncio.to_thread to propagate nodetracer context.

    When a trace is active, any callable run via asyncio.to_thread() will
    execute in a thread that has the same trace and node context, so
    auto-instrumented HTTP/LLM calls nest correctly under the spawning span.
    Call once at application startup. Idempotent.
    """
    global _patched
    if _patched:
        return

    async def _patched_to_thread(func: object, /, *args: object, **kwargs: object) -> object:
        wrapped = propagate_context(func)  # type: ignore[arg-type]
        return await _original_to_thread(wrapped, *args, **kwargs)

    asyncio.to_thread = _patched_to_thread  # type: ignore[assignment]
    _patched = True


def uninstrument_threads() -> None:
    """Restore original asyncio.to_thread. For testing."""
    global _patched
    asyncio.to_thread = _original_to_thread  # type: ignore[assignment]
    _patched = False
