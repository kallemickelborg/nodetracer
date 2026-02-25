"""Example 2: Parallel execution.

An agent that: receives a query -> spawns 3 parallel search tasks via
asyncio.gather() -> merges results -> synthesizes a response.

Validates: contextvars forking across async tasks, concurrent nodes,
proper sequence numbering under parallelism.
"""

from __future__ import annotations

import asyncio

from nodetracer.core import Tracer, TracerConfig
from nodetracer.models import NodeStatus
from nodetracer.storage import MemoryStore


async def main() -> None:
    store = MemoryStore()
    tracer = Tracer(config=TracerConfig(), storage=store)

    async with tracer.trace("parallel_search_agent") as root:
        with root.node("plan", node_type="decision") as plan:
            plan.input(query="Compare Python, Rust, and Go")
            plan.output(strategy="parallel_search")
            plan.annotate("Query requires multi-source comparison — fanning out")

        async def search(source: str) -> dict[str, str]:
            async with root.node(f"search_{source}", node_type="retrieval") as s:
                s.input(source=source, query="language comparison")
                await asyncio.sleep(0)
                result = {"source": source, "summary": f"{source} results here"}
                s.output(**result)
                return result

        results = await asyncio.gather(
            search("web"),
            search("docs"),
            search("arxiv"),
        )

        with root.node("synthesize", node_type="llm_call") as synth:
            synth.input(sources=[r["source"] for r in results])
            synth.output(response="Python is great for AI, Rust for systems, Go for services.")

    graph = root.trace

    # -- Assertions --
    assert len(graph.nodes) == 6, f"Expected 6 nodes, got {len(graph.nodes)}"
    assert all(n.status == NodeStatus.COMPLETED for n in graph.nodes.values())

    search_nodes = [n for n in graph.nodes.values() if n.name.startswith("search_")]
    assert len(search_nodes) == 3

    sequence_numbers = {n.sequence_number for n in search_nodes}
    assert len(sequence_numbers) == 3, "Each parallel node must have a unique sequence number"

    assert all(n.parent_id == root.node_record.id for n in search_nodes)

    assert len(store.list_traces()) == 1

    print("Example 2 PASSED: Parallel execution")


if __name__ == "__main__":
    asyncio.run(main())
