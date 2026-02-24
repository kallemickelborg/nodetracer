"""Tracer — the primary DI-constructed entry point for trace capture."""

from __future__ import annotations

import warnings
from contextvars import Token
from datetime import UTC, datetime
from types import TracebackType

from ..models import Node, TraceGraph
from ..storage import MemoryStore, StorageBackend
from .context import push_current_node, push_current_trace, reset_current_node, reset_current_trace
from .hooks import TracerHook
from .span import Span
from .tracer_config import TracerConfig


class Tracer:
    """Owns its config and storage. Construct via DI or use the convenience layer.

    Error-handling contract
    ----------------------
    - Configuration errors (invalid ``TracerConfig``, non-writable storage path)
      raise immediately — these are programming errors the caller should fix.
    - Runtime tracing errors (``storage.save()`` failure, internal span
      accounting) are swallowed with ``warnings.warn`` so that the host
      application is never affected by tracing infrastructure.
    """

    def __init__(
        self,
        config: TracerConfig | None = None,
        storage: StorageBackend | None = None,
        hooks: list[TracerHook] | None = None,
    ) -> None:
        self.config = config or TracerConfig()
        self.storage: StorageBackend = storage or MemoryStore()
        self.hooks: list[TracerHook] = hooks or []

    def trace(self, name: str, metadata: dict[str, object] | None = None) -> TraceContext:
        return TraceContext(name=name, metadata=metadata, tracer=self)


class TraceContext:
    """Sync + async context manager that captures one trace."""

    def __init__(
        self,
        name: str,
        tracer: Tracer,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self._tracer = tracer
        self._hooks = tracer.hooks
        self.trace_graph = TraceGraph(
            name=name,
            metadata=metadata or {},
            start_time=datetime.now(UTC),
        )
        self.root_span = Span(
            trace=self.trace_graph,
            name=name,
            node_type="trace",
            config=tracer.config,
            hooks=self._hooks,
        )
        self._trace_token: Token[TraceGraph | None] | None = None
        self._node_token: Token[Node | None] | None = None

    def _finalize(self) -> None:
        self.trace_graph.end_time = datetime.now(UTC)
        try:
            self._tracer.storage.save(self.trace_graph)
        except Exception:
            warnings.warn(
                f"logtracer: failed to save trace {self.trace_graph.trace_id}. "
                "Trace data has been dropped.",
                stacklevel=2,
            )
        if self._hooks:
            for hook in self._hooks:
                try:
                    hook.on_trace_completed(self.trace_graph)
                except Exception:
                    warnings.warn(
                        "logtracer: hook error in on_trace_completed",
                        stacklevel=2,
                    )

    def __enter__(self) -> Span:
        self._trace_token = push_current_trace(self.trace_graph)
        self._node_token = push_current_node(None)
        self.root_span.__enter__()
        return self.root_span

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self.root_span.__exit__(exc_type, exc, None)
        if self._node_token is not None:
            reset_current_node(self._node_token)
        if self._trace_token is not None:
            reset_current_trace(self._trace_token)
        self._finalize()
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
