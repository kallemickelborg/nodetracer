from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nodetracer.models import Edge, EdgeType, Node, NodeStatus, TraceGraph


def test_node_duration_ms_is_computed() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 1, second=1, tzinfo=UTC)
    node = Node(
        sequence_number=0,
        name="step",
        node_type="custom",
        start_time=start,
        end_time=end,
    )
    assert node.duration_ms == 1000.0


def test_trace_sequence_counter_is_monotonic() -> None:
    trace = TraceGraph(name="run")
    assert trace.next_sequence_number() == 0
    assert trace.next_sequence_number() == 1
    assert trace.next_sequence_number() == 2


def test_add_edge_requires_existing_nodes() -> None:
    trace = TraceGraph(name="run")
    source = Node(sequence_number=0, name="source", node_type="custom")
    trace.add_node(source)

    with pytest.raises(ValueError, match="Unknown edge target node id"):
        trace.add_edge(Edge(source_id=source.id, target_id="missing"))


def test_model_validation_rejects_edge_with_missing_node() -> None:
    source = Node(sequence_number=0, name="source", node_type="custom")
    edge = Edge(source_id=source.id, target_id="missing", edge_type=EdgeType.CAUSED_BY)

    with pytest.raises(ValueError, match="Edge target_id not found in nodes"):
        TraceGraph(name="run", nodes={source.id: source}, edges=[edge])


def test_root_and_failed_node_helpers() -> None:
    root = Node(sequence_number=0, name="root", node_type="custom")
    child = Node(
        sequence_number=1,
        name="child",
        node_type="custom",
        parent_id=root.id,
        status=NodeStatus.FAILED,
    )
    trace = TraceGraph(name="run", nodes={root.id: root, child.id: child})

    assert [node.id for node in trace.root_nodes] == [root.id]
    assert [node.id for node in trace.failed_nodes] == [child.id]
