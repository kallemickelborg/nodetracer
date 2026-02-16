"""Command line interface for logtracer."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Literal, cast

from .console import render_trace
from .graph import NodeStatus, TraceGraph
from .serializers import load_trace_json

VerbosityArg = Literal["minimal", "standard", "full"]


def build_parser() -> argparse.ArgumentParser:
    """Build the root CLI parser."""
    parser = argparse.ArgumentParser(prog="logtracer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a trace JSON file")
    inspect_parser.add_argument("trace_file", type=Path, help="Path to trace JSON file")
    inspect_parser.add_argument(
        "--verbosity",
        choices=["minimal", "standard", "full"],
        default="standard",
        help="Console render verbosity",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable summary JSON instead of text output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        return _run_inspect(
            args.trace_file,
            cast(VerbosityArg, args.verbosity),
            as_json=args.json,
        )

    parser.error("Unknown command")
    return 2


def _run_inspect(trace_file: Path, verbosity: VerbosityArg, *, as_json: bool) -> int:
    """Inspect a trace file and print summary + tree."""
    trace = load_trace_json(trace_file)
    summary = _build_summary(trace)

    if as_json:
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
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
    """Build a machine-readable summary payload for a trace."""
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


if __name__ == "__main__":
    raise SystemExit(main())
