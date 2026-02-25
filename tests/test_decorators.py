from __future__ import annotations

import pytest

from nodetracer import trace
from nodetracer.core import trace_node


def test_trace_node_decorator_sync_inside_trace() -> None:
    @trace_node(node_type="tool_call")
    def compute(value: int) -> int:
        return value + 1

    with trace("decorated_sync") as root:
        result = compute(1)

    assert result == 2
    names = [node.name for node in root.trace.nodes.values()]
    assert "compute" in names


@pytest.mark.asyncio
async def test_trace_node_decorator_async_inside_trace() -> None:
    @trace_node(name="async_compute", node_type="llm_call")
    async def compute(value: int) -> int:
        return value + 1

    async with trace("decorated_async") as root:
        result = await compute(10)

    assert result == 11
    names = [node.name for node in root.trace.nodes.values()]
    assert "async_compute" in names


def test_trace_node_decorator_no_active_trace_executes_normally() -> None:
    @trace_node()
    def identity(value: str) -> str:
        return value

    assert identity("ok") == "ok"
