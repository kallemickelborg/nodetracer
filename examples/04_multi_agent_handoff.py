"""Example 4: Multi-agent handoff.

A router agent delegates a sub-task to a specialist agent. The specialist
runs its own nodes nested under the router's trace.

Validates: nested spans representing sub-agents, deep nesting, the data model's
ability to represent multi-agent collaboration within a single trace.
"""

from __future__ import annotations

from nodetracer.core import Tracer, TracerConfig
from nodetracer.models import NodeStatus
from nodetracer.storage import MemoryStore


def specialist_agent(parent_span: object) -> str:
    """A specialist agent that runs its own sequence of steps under a parent span."""
    from nodetracer.core import Span

    assert isinstance(parent_span, Span)

    with parent_span.node("specialist_plan", node_type="decision") as plan:
        plan.input(task="deep research on quantum computing")
        plan.output(steps=["search_papers", "summarize"])
        plan.annotate("Specialist decomposed task into 2 steps")

    with parent_span.node("search_papers", node_type="retrieval") as search:
        search.input(query="quantum computing advances 2026")
        search.output(papers=["paper_a", "paper_b", "paper_c"])

    with parent_span.node("summarize", node_type="llm_call") as summarize:
        summarize.input(papers=["paper_a", "paper_b", "paper_c"])
        answer = "Quantum computing reached 1000 logical qubits in 2026."
        summarize.output(summary=answer)

    return answer


def main() -> None:
    store = MemoryStore()
    tracer = Tracer(config=TracerConfig(), storage=store)

    with tracer.trace("router_agent") as root:
        with root.node("classify_query", node_type="llm_call") as classify:
            classify.input(query="Tell me about quantum computing breakthroughs")
            classify.output(domain="quantum_computing", complexity="high")
            classify.annotate("High complexity — delegating to specialist")

        with root.node("specialist_agent", node_type="sub_agent") as agent_span:
            agent_span.input(task="deep research on quantum computing")
            result = specialist_agent(agent_span)
            agent_span.output(result=result)
            agent_span.annotate("Specialist completed successfully")

        with root.node("final_response", node_type="llm_call") as final:
            final.input(specialist_result=result, original_query="quantum computing")
            final.output(
                response="Based on specialist research: " + result,
            )

    graph = root.trace

    # -- Assertions --
    # root + classify + specialist_agent + 3 specialist children + final = 7
    assert len(graph.nodes) == 7, f"Expected 7 nodes, got {len(graph.nodes)}"
    assert all(n.status == NodeStatus.COMPLETED for n in graph.nodes.values())

    agent_node = next(n for n in graph.nodes.values() if n.name == "specialist_agent")
    assert agent_node.node_type == "sub_agent"
    assert agent_node.depth == 1

    specialist_children = [n for n in graph.nodes.values() if n.parent_id == agent_node.id]
    assert len(specialist_children) == 3, (
        f"Expected 3 specialist children, got {len(specialist_children)}"
    )
    child_names = sorted(n.name for n in specialist_children)
    assert child_names == ["search_papers", "specialist_plan", "summarize"]

    # Verify depth: root=0, agent=1, specialist children=2
    for child in specialist_children:
        assert child.depth == 2, f"{child.name} should be depth 2, got {child.depth}"

    assert len(store.list_traces()) == 1

    print("Example 4 PASSED: Multi-agent handoff")


if __name__ == "__main__":
    main()
