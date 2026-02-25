from __future__ import annotations

from pathlib import Path

from nodetracer.models import Node, TraceGraph
from nodetracer.storage import FileStore, MemoryStore


def _trace() -> TraceGraph:
    trace = TraceGraph(name="run")
    node = Node(sequence_number=trace.next_sequence_number(), name="step", node_type="custom")
    trace.add_node(node)
    return trace


def test_memory_store_roundtrip() -> None:
    store = MemoryStore()
    trace = _trace()
    store.save(trace)

    loaded = store.load(trace.trace_id)
    assert loaded is trace
    assert store.list_traces() == [trace.trace_id]


def test_file_store_roundtrip(tmp_path: Path) -> None:
    store = FileStore(tmp_path)
    trace = _trace()
    store.save(trace)

    loaded = store.load(trace.trace_id)
    assert loaded is not None
    assert loaded.trace_id == trace.trace_id
    assert trace.trace_id in store.list_traces()


def test_file_store_load_missing_returns_none(tmp_path: Path) -> None:
    store = FileStore(tmp_path)
    assert store.load("missing") is None
