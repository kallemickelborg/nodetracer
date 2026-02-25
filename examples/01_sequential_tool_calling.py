"""Example 1: Sequential tool-calling agent.

An agent that: receives a query -> decides which tool to use -> calls the tool
-> synthesizes a response. All sequential, no parallelism.

Validates: basic trace/node nesting, input/output recording, annotations,
edge creation, JSON serialization roundtrip.
"""

from __future__ import annotations

from nodetracer.core import Tracer, TracerConfig
from nodetracer.models import EdgeType, NodeStatus
from nodetracer.serializers import trace_from_json, trace_to_json
from nodetracer.storage import MemoryStore


def main() -> None:
    store = MemoryStore()
    tracer = Tracer(config=TracerConfig(), storage=store)

    with tracer.trace("weather_agent", metadata={"user_id": "u_123"}) as root:
        with root.node("classify_intent", node_type="llm_call") as classify:
            classify.input(query="What's the weather in Paris?", model="gpt-4o")
            intent = "weather_lookup"
            classify.output(intent=intent, confidence=0.95)
            classify.annotate("High confidence weather intent — routing to weather tool")
            classify.metadata(tokens_used=42)

        with root.node("weather_api", node_type="tool_call") as tool:
            tool.input(location="Paris", units="celsius")
            result = {"temperature_c": 18, "condition": "partly cloudy"}
            tool.output(**result)

        with root.node("synthesize", node_type="llm_call") as synth:
            synth.input(context=result, query="What's the weather in Paris?")
            answer = "It's 18°C and partly cloudy in Paris right now."
            synth.output(response=answer)
            synth.metadata(tokens_used=67)

    graph = root.trace

    # -- Assertions --
    assert len(graph.nodes) == 4, f"Expected 4 nodes (root + 3 steps), got {len(graph.nodes)}"
    assert graph.name == "weather_agent"
    assert graph.metadata["user_id"] == "u_123"
    assert all(n.status == NodeStatus.COMPLETED for n in graph.nodes.values())

    node_names = [n.name for n in sorted(graph.nodes.values(), key=lambda n: n.sequence_number)]
    assert node_names == [
        "weather_agent",
        "classify_intent",
        "weather_api",
        "synthesize",
    ]

    classify_node = next(n for n in graph.nodes.values() if n.name == "classify_intent")
    assert classify_node.input_data["query"] == "What's the weather in Paris?"
    assert classify_node.annotations == ["High confidence weather intent — routing to weather tool"]
    assert classify_node.metadata["tokens_used"] == 42

    assert len(graph.edges) == 3
    assert all(e.edge_type == EdgeType.CAUSED_BY for e in graph.edges)

    # JSON roundtrip
    json_str = trace_to_json(graph)
    restored = trace_from_json(json_str)
    assert restored.trace_id == graph.trace_id
    assert len(restored.nodes) == 4

    # Storage roundtrip
    assert len(store.list_traces()) == 1

    print("Example 1 PASSED: Sequential tool-calling agent")


if __name__ == "__main__":
    main()
