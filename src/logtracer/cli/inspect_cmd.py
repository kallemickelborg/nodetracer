"""Inspect subcommand implementation."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Literal

from ..exceptions import LogtracerLoadError
from ..models import NodeStatus, TraceGraph
from ..renderers import render_trace
from ..serializers import load_trace_json

VerbosityArg = Literal["minimal", "standard", "full"]


def run_inspect(
    trace_file: Path,
    verbosity: VerbosityArg,
    *,
    as_json: bool,
    output_path: Path | None,
) -> int:
    if output_path is not None and not as_json:
        raise ValueError("--output is only supported when --json is provided")

    try:
        trace = load_trace_json(trace_file)
    except FileNotFoundError:
        print(f"Error: file not found: {trace_file}", file=sys.stderr)
        return 1
    except LogtracerLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error reading file: {exc}", file=sys.stderr)
        return 1
    summary = _build_summary(trace)

    if as_json:
        payload = json.dumps(summary, ensure_ascii=True, sort_keys=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return 0

    status_counts = Counter(node.status for node in trace.nodes.values())
    type_counts = Counter(node.node_type for node in trace.nodes.values())
    duration = f"{trace.duration_ms:.0f}ms" if trace.duration_ms is not None else "unknown"

    print(f"Trace ID: {trace.trace_id}")
    print(f"Name: {trace.name or '<unnamed>'}")
    print(f"Schema: {trace.schema_version}")
    print(f"Duration: {duration}")
    print(f"Nodes: {len(trace.nodes)}")
    print(f"Edges: {len(trace.edges)}")
    print("Status counts:")
    for status, count in sorted(status_counts.items(), key=lambda item: item[0].value):
        print(f"  - {status.value}: {count}")
    print("Node type counts:")
    for node_type, count in sorted(type_counts.items(), key=lambda item: item[0]):
        print(f"  - {node_type}: {count}")
    print()
    print(render_trace(trace, verbosity=verbosity))
    return 0


def _build_summary(trace: TraceGraph) -> dict[str, object]:
    status_counts = Counter(node.status for node in trace.nodes.values())
    node_type_counts = Counter(node.node_type for node in trace.nodes.values())
    full_status_counts = {status.value: int(status_counts.get(status, 0)) for status in NodeStatus}
    sorted_type_counts = dict(sorted(node_type_counts.items(), key=lambda item: item[0]))

    return {
        "trace_id": trace.trace_id,
        "name": trace.name,
        "schema_version": trace.schema_version,
        "duration_ms": trace.duration_ms,
        "node_count": len(trace.nodes),
        "edge_count": len(trace.edges),
        "status_counts": full_status_counts,
        "node_type_counts": sorted_type_counts,
    }
