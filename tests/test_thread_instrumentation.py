"""Tests for thread context propagation instrumentation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("requests")

from nodetracer.core import Tracer
from nodetracer.instrumentation import (
    instrument_requests,
    instrument_threads,
    uninstrument_threads,
)
from nodetracer.storage import MemoryStore


def _mock_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def _sync_http_in_thread() -> None:
    """Sync function that performs an HTTP request. Runs in thread pool."""
    import requests

    requests.get("https://example.com/thread")


@pytest.mark.asyncio
async def test_asyncio_to_thread_propagates_context_when_instrumented() -> None:
    """With instrument_threads(), HTTP calls inside asyncio.to_thread nest under current span."""
    with patch("requests.Session.request", return_value=_mock_response(200)):
        instrument_requests()
        instrument_threads()

        tracer = Tracer(storage=MemoryStore())
        async with tracer.trace("root") as root:
            await __import__("asyncio").to_thread(_sync_http_in_thread)

        nodes = list(root.trace.nodes.values())
        root_nodes = [n for n in nodes if n.parent_id is None]
        http_nodes = [n for n in nodes if n.node_type == "http_request"]
        assert len(root_nodes) == 1, "one root"
        assert len(http_nodes) == 1, "one http span"
        assert http_nodes[0].parent_id == root.node_record.id, "http span is child of root"


@pytest.mark.asyncio
async def test_instrument_threads_idempotent() -> None:
    """Calling instrument_threads() multiple times is safe."""
    with patch("requests.Session.request", return_value=_mock_response(200)):
        instrument_requests()
        instrument_threads()
        instrument_threads()

        tracer = Tracer(storage=MemoryStore())
        async with tracer.trace("root") as root:
            await __import__("asyncio").to_thread(_sync_http_in_thread)

        http_nodes = [n for n in root.trace.nodes.values() if n.node_type == "http_request"]
        assert len(http_nodes) == 1
        assert http_nodes[0].parent_id == root.node_record.id


@pytest.mark.asyncio
async def test_uninstrument_threads_then_reinstrument_works() -> None:
    """After uninstrument_threads(), calling instrument_threads() again restores propagation."""
    with patch("requests.Session.request", return_value=_mock_response(200)):
        instrument_requests()
        instrument_threads()

        tracer = Tracer(storage=MemoryStore())
        async with tracer.trace("root") as root:
            await __import__("asyncio").to_thread(_sync_http_in_thread)

        http_nodes = [n for n in root.trace.nodes.values() if n.node_type == "http_request"]
        assert len(http_nodes) == 1
        assert http_nodes[0].parent_id == root.node_record.id

        uninstrument_threads()
        instrument_threads()

        tracer2 = Tracer(storage=MemoryStore())
        async with tracer2.trace("root2") as root2:
            await __import__("asyncio").to_thread(_sync_http_in_thread)

        http_nodes2 = [n for n in root2.trace.nodes.values() if n.node_type == "http_request"]
        assert len(http_nodes2) == 1, "re-instrument preserves propagation"
        assert http_nodes2[0].parent_id == root2.node_record.id
