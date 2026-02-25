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


def test_trace_node_capture_args_records_input_data() -> None:
    @trace_node(node_type="tool_call", capture_args=True)
    def search(query: str, max_results: int = 10) -> list[str]:
        return ["result_1"]

    with trace("capture_args") as root:
        search("hello world", max_results=5)

    node = next(n for n in root.trace.nodes.values() if n.name == "search")
    assert node.input_data["query"] == "hello world"
    assert node.input_data["max_results"] == 5


def test_trace_node_capture_return_records_output_data() -> None:
    @trace_node(node_type="tool_call", capture_return=True)
    def fetch(url: str) -> dict[str, str]:
        return {"status": "ok", "body": "hello"}

    with trace("capture_return") as root:
        result = fetch("https://example.com")

    assert result == {"status": "ok", "body": "hello"}
    node = next(n for n in root.trace.nodes.values() if n.name == "fetch")
    assert node.output_data["status"] == "ok"
    assert node.output_data["body"] == "hello"


def test_trace_node_capture_return_non_dict_uses_return_value_key() -> None:
    @trace_node(node_type="tool_call", capture_return=True)
    def compute(x: int) -> int:
        return x * 2

    with trace("capture_scalar_return") as root:
        result = compute(21)

    assert result == 42
    node = next(n for n in root.trace.nodes.values() if n.name == "compute")
    assert node.output_data["return_value"] == 42


def test_trace_node_capture_args_excludes_self() -> None:
    class MyService:
        @trace_node(node_type="tool_call", capture_args=True, capture_return=True)
        def process(self, query: str) -> str:
            return f"processed: {query}"

    svc = MyService()
    with trace("method_capture") as root:
        result = svc.process("test")

    assert result == "processed: test"
    node = next(n for n in root.trace.nodes.values() if n.name == "process")
    assert "self" not in node.input_data
    assert node.input_data["query"] == "test"
    assert node.output_data["return_value"] == "processed: test"


@pytest.mark.asyncio
async def test_trace_node_capture_args_and_return_async() -> None:
    @trace_node(node_type="llm_call", capture_args=True, capture_return=True)
    async def evaluate(title: str, score: float) -> dict[str, object]:
        return {"title": title, "relevancy": score}

    async with trace("async_capture") as root:
        result = await evaluate("Test Paper", score=0.85)

    assert result == {"title": "Test Paper", "relevancy": 0.85}
    node = next(n for n in root.trace.nodes.values() if n.name == "evaluate")
    assert node.input_data["title"] == "Test Paper"
    assert node.input_data["score"] == 0.85
    assert node.output_data["title"] == "Test Paper"
    assert node.output_data["relevancy"] == 0.85


def test_trace_node_capture_args_no_trace_active() -> None:
    @trace_node(capture_args=True, capture_return=True)
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
