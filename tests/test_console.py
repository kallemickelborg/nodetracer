from __future__ import annotations

from datetime import UTC, datetime

from nodetracer.models import Node, NodeStatus, TraceGraph
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
    assert "metadata: {'confidence': 0.94}" in output
    assert "input: {'location': 'San Francisco'}" in output
