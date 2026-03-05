"""Tests for auto_instrument()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("requests")

from nodetracer import auto_instrument
from nodetracer.core import Tracer
from nodetracer.instrumentation import uninstrument_threads
from nodetracer.storage import MemoryStore


def _mock_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def _sync_http() -> None:
    import requests

    requests.get("https://example.com/")


@pytest.mark.asyncio
async def test_auto_instrument_activates_http_and_threads() -> None:
    """auto_instrument() enables both HTTP and thread instrumentation."""
    with patch("requests.Session.request", return_value=_mock_response(200)):
        auto_instrument()

        tracer = Tracer(storage=MemoryStore())
        async with tracer.trace("root") as root:
            await __import__("asyncio").to_thread(_sync_http)

        http_nodes = [n for n in root.trace.nodes.values() if n.node_type == "http_request"]
        assert len(http_nodes) == 1
        assert http_nodes[0].parent_id == root.node_record.id

    uninstrument_threads()


def test_auto_instrument_http_false_only_threads() -> None:
    """auto_instrument(http=False) only activates thread instrumentation."""
    auto_instrument(http=False, threads=True)
    # Thread instrumentation is active; HTTP is not patched by us (may still be from prior test)
    uninstrument_threads()


def test_auto_instrument_multiple_calls_safe() -> None:
    """Calling auto_instrument() multiple times does not crash and tracing still works."""
    with patch("requests.Session.request", return_value=_mock_response(200)):
        auto_instrument()
        auto_instrument()

        tracer = Tracer(storage=MemoryStore())
        with tracer.trace("r") as root:
            import requests

            requests.get("https://example.com/")

        http_nodes = [n for n in root.trace.nodes.values() if n.node_type == "http_request"]
        assert len(http_nodes) >= 1
