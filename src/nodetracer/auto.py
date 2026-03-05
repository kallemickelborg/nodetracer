"""One-liner auto-instrumentation."""

from __future__ import annotations

from collections.abc import Callable

from .instrumentation import instrument_http, instrument_threads


def auto_instrument(
    *,
    http: bool = True,
    threads: bool = True,
    url_filter: Callable[[str], str] | None = None,
    exclude_urls: list[str] | None = None,
) -> None:
    """Activate all universal auto-instrumentation.

    Call once at application startup. Enables:
    - HTTP client instrumentation (requests, httpx, aiohttp) when http=True
    - Thread context propagation (asyncio.to_thread) when threads=True

    Idempotent; safe to call multiple times.
    """
    if http:
        instrument_http(url_filter=url_filter, exclude_urls=exclude_urls)
    if threads:
        instrument_threads()
