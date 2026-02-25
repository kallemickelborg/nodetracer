from __future__ import annotations

import asyncio

import pytest

from nodetracer import configure, trace
from nodetracer.core import Tracer, TracerConfig
from nodetracer.models import EdgeType, NodeStatus
from nodetracer.storage import MemoryStore


def test_trace_sync_lifecycle_and_nesting() -> None:
    with trace("agent_run") as root:
        with root.node("plan", node_type="decision") as plan:
            plan.input(prompt="hello")
            plan.output(answer="world")
            plan.annotate("First route selected")

        with root.node("tool_call", node_type="tool_call"):
            pass

    graph = root.trace
    assert graph.start_time is not None
    assert graph.end_time is not None
    assert len(graph.nodes) == 3
    assert all(node.sequence_number >= 0 for node in graph.nodes.values())

    plan_node = next(node for node in graph.nodes.values() if node.name == "plan")
    assert plan_node.status == NodeStatus.COMPLETED
    assert plan_node.input_data["prompt"] == "hello"
    assert plan_node.output_data["answer"] == "world"
    assert plan_node.annotations == ["First route selected"]


@pytest.mark.asyncio
async def test_trace_async_parallel_gather() -> None:
    async with trace("parallel_run") as root:

        async def branch(name: str) -> None:
            async with root.node(name, node_type="tool_call"):
                await asyncio.sleep(0)

        await asyncio.gather(branch("b1"), branch("b2"), branch("b3"))

    graph = root.trace
    branch_nodes = [node for node in graph.nodes.values() if node.name.startswith("b")]
    assert len(branch_nodes) == 3
    assert len({node.sequence_number for node in branch_nodes}) == 3
    assert all(node.parent_id == root.node_record.id for node in branch_nodes)


def test_trace_captures_failure_in_child_span() -> None:
    with (
        trace("error_run") as root,
        pytest.raises(RuntimeError, match="boom"),
        root.node("failing_step", node_type="custom"),
    ):
        raise RuntimeError("boom")

    failing_node = next(node for node in root.trace.nodes.values() if node.name == "failing_step")
    assert failing_node.status == NodeStatus.FAILED
    assert failing_node.error == "boom"
    assert failing_node.error_type == "RuntimeError"
    assert failing_node.error_traceback is not None


def test_trace_retry_and_fallback_edges_are_recorded() -> None:
    with trace("recovery_run") as root:
        with root.node("attempt_1", node_type="tool_call") as attempt_1:
            attempt_1.set_status(NodeStatus.FAILED)

        with root.node("attempt_2", node_type="tool_call") as attempt_2:
            pass

        attempt_1.link(attempt_2, edge_type=EdgeType.RETRY_OF)

        with root.node("fallback_path", node_type="tool_call") as fallback:
            pass

        attempt_1.link(fallback, edge_type=EdgeType.FALLBACK_OF)

    retry_edges = [edge for edge in root.trace.edges if edge.edge_type == EdgeType.RETRY_OF]
    fallback_edges = [edge for edge in root.trace.edges if edge.edge_type == EdgeType.FALLBACK_OF]

    assert len(retry_edges) == 1
    assert len(fallback_edges) == 1


def test_trace_payload_truncation_from_config() -> None:
    configure(max_input_size=6, max_output_size=8)

    with trace("truncate_run") as root, root.node("payload_step", node_type="custom") as payload:
        payload.input(query="1234567890")
        payload.output(result="abcdefghijk")

    node = next(node for node in root.trace.nodes.values() if node.name == "payload_step")
    assert isinstance(node.input_data["query"], str)
    assert isinstance(node.output_data["result"], str)
    assert "TRUNCATED" in node.input_data["query"]
    assert "TRUNCATED" in node.output_data["result"]


def test_tracer_di_construction() -> None:
    """Verify the DI API: construct a Tracer with explicit config and storage."""
    store = MemoryStore()
    config = TracerConfig(max_input_size=5)
    tracer = Tracer(config=config, storage=store)

    with tracer.trace("di_run") as root, root.node("step", node_type="tool_call") as step:
        step.input(data="abcdefgh")

    assert len(store.list_traces()) == 1
    loaded = store.load(root.trace.trace_id)
    assert loaded is not None
    step_node = next(n for n in loaded.nodes.values() if n.name == "step")
    assert "TRUNCATED" in str(step_node.input_data["data"])
