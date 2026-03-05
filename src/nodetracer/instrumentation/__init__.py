"""HTTP client auto-instrumentation for requests, httpx, and aiohttp."""

from __future__ import annotations

from collections.abc import Callable

from .aiohttp_ import instrument_aiohttp
from .httpx_ import instrument_httpx
from .requests_ import instrument_requests
from .threads import instrument_threads, uninstrument_threads


def instrument_http(
    *,
    requests: bool = True,
    httpx: bool = True,
    aiohttp: bool = True,
    url_filter: Callable[[str], str] | None = None,
    exclude_urls: list[str] | None = None,
) -> None:
    """Instrument HTTP clients. Patches whichever libraries are installed.

    Call once at application startup. When a trace is active, every HTTP
    request creates a child span with method, url, status_code, duration_ms.

    Args:
        requests: Whether to patch the requests library.
        httpx: Whether to patch the httpx library (sync + async).
        aiohttp: Whether to patch the aiohttp library.
        url_filter: Optional callback to redact sensitive URL parts.
        exclude_urls: List of regex patterns; matching URLs are not traced.
    """
    if requests:
        instrument_requests(url_filter=url_filter, exclude_urls=exclude_urls)
    if httpx:
        instrument_httpx(url_filter=url_filter, exclude_urls=exclude_urls)
    if aiohttp:
        instrument_aiohttp(url_filter=url_filter, exclude_urls=exclude_urls)


__all__ = [
    "instrument_aiohttp",
    "instrument_http",
    "instrument_httpx",
    "instrument_requests",
    "instrument_threads",
    "uninstrument_threads",
]
