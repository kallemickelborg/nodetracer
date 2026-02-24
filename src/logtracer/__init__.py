"""logtracer — framework-agnostic AI agent tracing library.

Convenience API (delegates to a default Tracer instance):
    logtracer.configure(...)   -> set up default tracer
    logtracer.trace(...)       -> start a trace session
    logtracer.trace_node(...)  -> decorator for function-level tracing

DI API (construct your own Tracer):
    from logtracer.core import Tracer, TracerConfig
    tracer = Tracer(config=TracerConfig(...), storage=my_store)
    with tracer.trace("run") as root:
        ...
"""

from __future__ import annotations

from typing import Literal

from .core import NullHook, Tracer, TracerConfig, TracerHook, trace_node
from .core.tracer import TraceContext
from .storage import FileStore, MemoryStore, StorageBackend

CaptureLevel = Literal["minimal", "standard", "full"]

_default_tracer: Tracer | None = None


def configure(
    *,
    capture_level: CaptureLevel = "full",
    auto_instrument: list[str] | None = None,
    storage: str | StorageBackend = "memory",
    redact_patterns: list[str] | None = None,
    max_output_size: int | None = None,
    max_input_size: int | None = None,
    hooks: list[TracerHook] | None = None,
) -> Tracer:
    """Configure and return the default global Tracer instance."""
    global _default_tracer
    config = TracerConfig(
        capture_level=capture_level,
        auto_instrument=list(auto_instrument or []),
        redact_patterns=list(redact_patterns or []),
        max_output_size=max_output_size,
        max_input_size=max_input_size,
    )
    _default_tracer = Tracer(config=config, storage=_resolve_storage(storage), hooks=hooks)
    return _default_tracer


def trace(name: str, metadata: dict[str, object] | None = None) -> TraceContext:
    """Start a trace session using the default Tracer."""
    global _default_tracer
    if _default_tracer is None:
        _default_tracer = Tracer()
    return _default_tracer.trace(name, metadata=metadata)


def _reset_default_tracer() -> None:
    """Reset the default tracer. Used by test fixtures."""
    global _default_tracer
    _default_tracer = None


def _resolve_storage(storage: str | StorageBackend) -> StorageBackend:
    if not isinstance(storage, str):
        return storage
    if storage == "memory":
        return MemoryStore()
    if storage.startswith("file://"):
        return FileStore(storage.removeprefix("file://"))
    raise ValueError(
        "Unsupported storage value. Use 'memory', 'file://<path>', or a StorageBackend instance."
    )


__all__ = [
    "FileStore",
    "MemoryStore",
    "NullHook",
    "StorageBackend",
    "Tracer",
    "TracerConfig",
    "TracerHook",
    "configure",
    "trace",
    "trace_node",
]
