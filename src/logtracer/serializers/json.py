"""JSON serialization helpers for trace graphs."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

from ..exceptions import LogtracerLoadError
from ..models import CURRENT_SCHEMA_VERSION, TraceGraph


def trace_to_json(trace: TraceGraph, *, indent: int | None = 2) -> str:
    return trace.model_dump_json(indent=indent)


def trace_from_json(payload: str) -> TraceGraph:
    """Parse a JSON string into a TraceGraph.

    Raises ``LogtracerLoadError`` on invalid or unparseable input.
    Emits a warning if the trace's schema version differs from the current one.
    """
    try:
        graph = TraceGraph.model_validate_json(payload)
    except (json.JSONDecodeError, ValueError, Exception) as exc:
        raise LogtracerLoadError(f"Failed to parse trace JSON: {exc}") from exc
    if graph.schema_version != CURRENT_SCHEMA_VERSION:
        warnings.warn(
            f"Trace schema version {graph.schema_version!r} differs from "
            f"current {CURRENT_SCHEMA_VERSION!r}. "
            "Some fields may be missing or ignored.",
            stacklevel=2,
        )
    return graph


def save_trace_json(trace: TraceGraph, path: str | Path, *, indent: int | None = 2) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(trace_to_json(trace, indent=indent), encoding="utf-8")
    return output_path


def load_trace_json(path: str | Path) -> TraceGraph:
    """Load a trace from a JSON file.

    Raises ``LogtracerLoadError`` on invalid content,
    or ``FileNotFoundError`` / ``OSError`` if the file is inaccessible.
    """
    payload = Path(path).read_text(encoding="utf-8")
    return trace_from_json(payload)
