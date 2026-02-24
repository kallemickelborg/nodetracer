"""In-memory storage backend."""

from __future__ import annotations

from ..models import TraceGraph


class MemoryStore:
    """In-memory store. Good for tests and short-lived scripts."""

    def __init__(self) -> None:
        self._traces: dict[str, TraceGraph] = {}

    def save(self, trace: TraceGraph) -> None:
        self._traces[trace.trace_id] = trace

    def load(self, trace_id: str) -> TraceGraph | None:
        return self._traces.get(trace_id)

    def list_traces(self) -> list[str]:
        return list(self._traces.keys())
