"""Span abstraction for in-progress nodes."""

from __future__ import annotations

import json
import traceback
import warnings
from collections.abc import Callable
from contextvars import Token
from datetime import UTC, datetime
from types import TracebackType

from ..models import Edge, EdgeType, Node, NodeStatus, TraceGraph
from .context import get_current_node, push_current_node, reset_current_node
from .tracer_config import TracerConfig


class Span:
    """A node that is currently being recorded."""

    def __init__(
        self,
        *,
        trace: TraceGraph,
        name: str,
        node_type: str = "custom",
        parent_node: Node | None = None,
        config: TracerConfig | None = None,
        on_close: Callable[[Span], None] | None = None,
    ) -> None:
        self.trace = trace
        self.name = name
        self.node_type = node_type
        self.parent_node = parent_node if parent_node is not None else get_current_node()
        self._config = config or TracerConfig()
        self._on_close = on_close

        self.node_record = Node(
            sequence_number=self.trace.next_sequence_number(),
            name=self.name,
            node_type=self.node_type,
            parent_id=self.parent_node.id if self.parent_node is not None else None,
            depth=self.parent_node.depth + 1 if self.parent_node is not None else 0,
        )
        self._node_token: Token[Node | None] | None = None
        self._entered = False

    def input(self, **kwargs: object) -> None:
        """Merge values into node input data."""
        limit = self._config.max_input_size
        self.node_record.input_data.update(
            {key: _truncate_if_needed(_safe_value(value), limit) for key, value in kwargs.items()}
        )

    def output(self, **kwargs: object) -> None:
        """Merge values into node output data."""
        limit = self._config.max_output_size
        self.node_record.output_data.update(
            {key: _truncate_if_needed(_safe_value(value), limit) for key, value in kwargs.items()}
        )

    def annotate(self, message: str) -> None:
        self.node_record.annotations.append(message)

    def metadata(self, **kwargs: object) -> None:
        self.node_record.metadata.update({key: _safe_value(value) for key, value in kwargs.items()})

    def set_status(self, status: NodeStatus) -> None:
        self.node_record.status = status

    def link(self, target: Span, edge_type: EdgeType = EdgeType.DATA_FLOW) -> None:
        self.trace.add_edge(
            Edge(
                source_id=self.node_record.id,
                target_id=target.node_record.id,
                edge_type=edge_type,
            )
        )

    def node(self, name: str, node_type: str = "custom") -> Span:
        """Create a child span that automatically nests under this span."""
        return Span(
            trace=self.trace,
            name=name,
            node_type=node_type,
            parent_node=self.node_record,
            config=self._config,
        )

    def __enter__(self) -> Span:
        if self._entered:
            return self

        self.node_record.status = NodeStatus.RUNNING
        self.node_record.start_time = datetime.now(UTC)
        self.trace.add_node(self.node_record)
        if self.parent_node is not None:
            self.trace.add_edge(Edge(source_id=self.parent_node.id, target_id=self.node_record.id))
        self._node_token = push_current_node(self.node_record)
        self._entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        del tb
        try:
            if exc is None:
                if self.node_record.status == NodeStatus.RUNNING:
                    self.node_record.status = NodeStatus.COMPLETED
            else:
                self.node_record.status = NodeStatus.FAILED
                self.node_record.error = str(exc)
                self.node_record.error_type = exc.__class__.__name__
                self.node_record.error_traceback = "".join(traceback.format_exception(exc))
            self.node_record.end_time = datetime.now(UTC)
        except Exception:
            warnings.warn(
                f"logtracer: internal error finalizing span '{self.name}'",
                stacklevel=2,
            )
        if self._node_token is not None:
            reset_current_node(self._node_token)
        self._entered = False
        if self._on_close is not None:
            self._on_close(self)
        return False

    async def __aenter__(self) -> Span:
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return self.__exit__(exc_type, exc, tb)


def _safe_value(value: object) -> object:
    """Ensure a value is JSON-serializable; fall back to str representation."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, dict)):
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return f"{value!r} [NON-SERIALIZABLE]"
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return f"{value!r} [NON-SERIALIZABLE]"


def _truncate_if_needed(value: object, limit: int | None) -> object:
    if limit is None or limit <= 0:
        return value
    if not isinstance(value, str):
        return value
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... [TRUNCATED: original_size={len(value)}]"
