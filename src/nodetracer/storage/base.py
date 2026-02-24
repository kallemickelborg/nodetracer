"""Storage backend abstractions."""

from __future__ import annotations

from typing import Protocol

from ..models import TraceGraph


class StorageBackend(Protocol):
    """Protocol for persisting traces."""

    def save(self, trace: TraceGraph) -> None: ...
    def load(self, trace_id: str) -> TraceGraph | None: ...
    def list_traces(self) -> list[str]: ...
