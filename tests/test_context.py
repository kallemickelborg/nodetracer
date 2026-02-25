from __future__ import annotations

from nodetracer.core.context import (
    clear_context,
    get_current_node,
    get_current_trace,
    propagate_context,
    push_current_node,
    push_current_trace,
    reset_current_node,
    reset_current_trace,
)
from nodetracer.models import Node, TraceGraph


def test_push_and_reset_context() -> None:
    trace = TraceGraph(name="run")
    node = Node(sequence_number=0, name="step", node_type="custom")

    trace_token = push_current_trace(trace)
    node_token = push_current_node(node)
    assert get_current_trace() is trace
    assert get_current_node() is node

    reset_current_node(node_token)
    reset_current_trace(trace_token)
    assert get_current_trace() is None
    assert get_current_node() is None


def test_propagate_context_copies_trace_and_node() -> None:
    trace = TraceGraph(name="run")
    node = Node(sequence_number=0, name="step", node_type="custom")
    trace_token = push_current_trace(trace)
    node_token = push_current_node(node)

    def inspect_context() -> tuple[TraceGraph | None, Node | None]:
        return get_current_trace(), get_current_node()

    wrapped = propagate_context(inspect_context)
    copied_trace, copied_node = wrapped()
    assert copied_trace is trace
    assert copied_node is node

    reset_current_node(node_token)
    reset_current_trace(trace_token)
    clear_context()
