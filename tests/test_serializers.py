from __future__ import annotations

from pathlib import Path

from nodetracer.models import Edge, Node, TraceGraph
from nodetracer.serializers import load_trace_json, save_trace_json, trace_from_json, trace_to_json


def _build_trace() -> TraceGraph:
    trace = TraceGraph(name="agent_run", metadata={"agent_version": "1.0.0"})
    plan = Node(sequence_number=trace.next_sequence_number(), name="plan", node_type="decision")
    call = Node(
        sequence_number=trace.next_sequence_number(),
        name="llm_call",
        node_type="llm_call",
        parent_id=plan.id,
        depth=1,
    )
    trace.add_node(plan)
    trace.add_node(call)
    trace.add_edge(Edge(source_id=plan.id, target_id=call.id))
    return trace


def test_trace_to_and_from_json_roundtrip() -> None:
    trace = _build_trace()
    payload = trace_to_json(trace)
    loaded = trace_from_json(payload)

    assert loaded.schema_version == "0.1.0"
    assert loaded.name == "agent_run"
    assert len(loaded.nodes) == 2
    assert len(loaded.edges) == 1


def test_save_and_load_trace_json_file(tmp_path: Path) -> None:
    trace = _build_trace()
    output = tmp_path / "trace.json"
    save_trace_json(trace, output)

    loaded = load_trace_json(output)
    assert loaded.trace_id == trace.trace_id
    assert loaded.nodes.keys() == trace.nodes.keys()
