"""Example 3: Retry and fallback.

An agent that: calls a tool that fails -> retries once -> fails again
-> falls back to a different tool -> succeeds.

Validates: RETRY_OF and FALLBACK_OF edge types, error capture,
status transitions, mixed success/failure in one trace.
"""

from __future__ import annotations

from nodetracer.core import Tracer, TracerConfig
from nodetracer.models import EdgeType, NodeStatus
from nodetracer.storage import MemoryStore


def main() -> None:
    store = MemoryStore()
    tracer = Tracer(config=TracerConfig(), storage=store)

    with tracer.trace("resilient_agent") as root:
        # First attempt — fails
        with root.node("api_call_attempt_1", node_type="tool_call") as attempt1:
            attempt1.input(endpoint="/v1/data", timeout=5)
            attempt1.set_status(NodeStatus.FAILED)
            attempt1.node_record.error = "ConnectionTimeout"
            attempt1.node_record.error_type = "TimeoutError"
            attempt1.annotate("Primary API timed out after 5s")

        # Retry — also fails
        with root.node("api_call_attempt_2", node_type="tool_call") as attempt2:
            attempt2.input(endpoint="/v1/data", timeout=10)
            attempt2.set_status(NodeStatus.FAILED)
            attempt2.node_record.error = "ConnectionTimeout"
            attempt2.node_record.error_type = "TimeoutError"
            attempt2.annotate("Retry with longer timeout also failed")

        attempt1.link(attempt2, edge_type=EdgeType.RETRY_OF)

        # Fallback to cache
        with root.node("cache_lookup", node_type="retrieval") as fallback:
            fallback.input(cache_key="data_v1")
            fallback.output(data={"cached": True, "value": 42})
            fallback.annotate("Fell back to cached data after API failures")

        attempt1.link(fallback, edge_type=EdgeType.FALLBACK_OF)

        # Synthesize with cached data
        with root.node("synthesize", node_type="llm_call") as synth:
            synth.input(data_source="cache", value=42)
            synth.output(response="Based on cached data, the answer is 42.")

    graph = root.trace

    # -- Assertions --
    assert len(graph.nodes) == 5

    failed = [n for n in graph.nodes.values() if n.status == NodeStatus.FAILED]
    completed = [n for n in graph.nodes.values() if n.status == NodeStatus.COMPLETED]
    assert len(failed) == 2, f"Expected 2 failed nodes, got {len(failed)}"
    assert len(completed) == 3, f"Expected 3 completed nodes, got {len(completed)}"

    retry_edges = [e for e in graph.edges if e.edge_type == EdgeType.RETRY_OF]
    fallback_edges = [e for e in graph.edges if e.edge_type == EdgeType.FALLBACK_OF]
    assert len(retry_edges) == 1
    assert len(fallback_edges) == 1

    assert retry_edges[0].source_id == attempt1.node_record.id
    assert retry_edges[0].target_id == attempt2.node_record.id

    assert fallback_edges[0].source_id == attempt1.node_record.id
    assert fallback_edges[0].target_id == fallback.node_record.id

    attempt1_node = next(n for n in graph.nodes.values() if n.name == "api_call_attempt_1")
    assert attempt1_node.error == "ConnectionTimeout"
    assert attempt1_node.error_type == "TimeoutError"
    assert len(attempt1_node.annotations) == 1

    print("Example 3 PASSED: Retry and fallback")


if __name__ == "__main__":
    main()
