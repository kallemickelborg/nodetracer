from __future__ import annotations

from datetime import UTC, datetime

from nodetracer.models import Edge, EdgeType, Node, NodeStatus, TraceGraph
from nodetracer.renderers import render_trace


def _trace_with_nodes() -> TraceGraph:
    trace = TraceGraph(
        name="agent_run",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=5, tzinfo=UTC),
    )
    root = Node(
        sequence_number=0,
        name="plan",
        node_type="decision",
        status=NodeStatus.COMPLETED,
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=1, tzinfo=UTC),
        annotations=["Routed to weather tool"],
        metadata={"confidence": 0.94},
    )
    child = Node(
        sequence_number=1,
        name="weather_api_call",
        node_type="tool_call",
        parent_id=root.id,
        depth=1,
        status=NodeStatus.COMPLETED,
        start_time=datetime(2026, 1, 1, second=1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=3, tzinfo=UTC),
        input_data={"location": "San Francisco"},
        output_data={"temperature": 62},
    )
    trace.add_node(root)
    trace.add_node(child)
    return trace


def test_render_trace_minimal_contains_structure() -> None:
    output = render_trace(_trace_with_nodes(), verbosity="minimal")
    assert "Trace: agent_run (5000ms)" in output
    assert "[decision] plan (1000ms)" in output
    assert "[tool_call] weather_api_call (2000ms)" in output


def test_render_trace_full_contains_metadata_and_annotations() -> None:
    output = render_trace(_trace_with_nodes(), verbosity="full")
    assert 'annotation: "Routed to weather tool"' in output
    assert 'metadata: {"confidence": 0.94}' in output
    assert 'input: {"location": "San Francisco"}' in output


def test_render_trace_standard_shows_annotations_and_errors_not_io() -> None:
    trace = TraceGraph(
        name="failed_run",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=1, tzinfo=UTC),
    )
    node = Node(
        sequence_number=0,
        name="llm_call",
        node_type="llm_call",
        status=NodeStatus.FAILED,
        error="Connection timeout",
        error_type="TimeoutError",
        annotations=["Retrying..."],
    )
    trace.add_node(node)
    output = render_trace(trace, verbosity="standard")
    assert 'annotation: "Retrying..."' in output
    assert "error: TimeoutError: Connection timeout" in output
    assert "input:" not in output
    assert "output:" not in output


def test_render_trace_edges_shown_inline() -> None:
    trace = TraceGraph(
        name="retry_run",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=3, tzinfo=UTC),
    )
    original = Node(
        sequence_number=0,
        name="first_attempt",
        node_type="tool_call",
        status=NodeStatus.FAILED,
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=1, tzinfo=UTC),
    )
    retry = Node(
        sequence_number=1,
        name="second_attempt",
        node_type="tool_call",
        parent_id=original.id,
        status=NodeStatus.COMPLETED,
        start_time=datetime(2026, 1, 1, second=1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=2, tzinfo=UTC),
    )
    trace.add_node(original)
    trace.add_node(retry)
    trace.add_edge(Edge(source_id=retry.id, target_id=original.id, edge_type=EdgeType.RETRY_OF))
    output = render_trace(trace, verbosity="minimal")
    assert "[retry of first_attempt]" in output


def test_render_trace_full_truncates_large_data() -> None:
    trace = TraceGraph(
        name="large_io",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, second=1, tzinfo=UTC),
    )
    big_payload = "x" * 300
    node = Node(
        sequence_number=0,
        name="big_call",
        node_type="llm_call",
        status=NodeStatus.COMPLETED,
        input_data={"payload": big_payload},
    )
    trace.add_node(node)
    output = render_trace(trace, verbosity="full")
    assert "[truncated]" in output
    assert "x" * 300 not in output
