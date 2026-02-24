"""File-based JSON storage backend."""

from __future__ import annotations

from pathlib import Path

from ..models import TraceGraph
from ..serializers import load_trace_json, save_trace_json


class FileStore:
    """Writes each trace as a JSON file in a directory."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, trace: TraceGraph) -> None:
        save_trace_json(trace, self.directory / f"{trace.trace_id}.json")

    def load(self, trace_id: str) -> TraceGraph | None:
        path = self.directory / f"{trace_id}.json"
        if not path.exists():
            return None
        return load_trace_json(path)

    def list_traces(self) -> list[str]:
        return sorted(path.stem for path in self.directory.glob("*.json"))
