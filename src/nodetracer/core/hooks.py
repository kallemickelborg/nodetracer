"""Event hook protocol for real-time trace observation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..models import Node, TraceGraph


@runtime_checkable
class TracerHook(Protocol):
    """Protocol for receiving trace lifecycle events.

    Implement any subset of these methods — unimplemented ones are no-ops.
    Hook methods must not raise; exceptions are swallowed by the dispatcher.
    """

    def on_node_started(self, node: Node, trace_id: str) -> None: ...
    def on_node_completed(self, node: Node, trace_id: str) -> None: ...
    def on_node_failed(self, node: Node, trace_id: str) -> None: ...
    def on_trace_completed(self, trace: TraceGraph) -> None: ...


class NullHook:
    """No-op hook. Useful as a reference implementation and in tests."""

    def on_node_started(self, node: Node, trace_id: str) -> None:
        pass

    def on_node_completed(self, node: Node, trace_id: str) -> None:
        pass

    def on_node_failed(self, node: Node, trace_id: str) -> None:
        pass

    def on_trace_completed(self, trace: TraceGraph) -> None:
        pass
