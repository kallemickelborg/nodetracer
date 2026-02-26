"""Rich-based trace console rendering."""

from __future__ import annotations

import json
from collections import defaultdict
from io import StringIO
from typing import Literal

from rich.console import Console
from rich.tree import Tree

from ..models import EdgeType, Node, NodeStatus, TraceGraph

Verbosity = Literal["minimal", "standard", "full"]
_MAX_VALUE_LEN = 200


def render_trace(trace: TraceGraph, *, verbosity: Verbosity = "standard") -> str:
    tree = Tree(_trace_label(trace))
    children_by_parent: dict[str | None, list[Node]] = defaultdict(list)
    for node in trace.nodes.values():
        children_by_parent[node.parent_id].append(node)

    for siblings in children_by_parent.values():
        siblings.sort(key=lambda node: node.sequence_number)

    edges_by_source = _build_edge_labels(trace)

    for root in children_by_parent[None]:
        _add_node_branch(tree, root, children_by_parent, edges_by_source, trace, verbosity)

    console = Console(record=True, width=120, markup=False, file=StringIO())
    console.print(tree)
    return console.export_text()


def _build_edge_labels(trace: TraceGraph) -> dict[str, list[str]]:
    """Build map: source_id -> [label, ...] for display."""
    result: dict[str, list[str]] = defaultdict(list)
    for edge in trace.edges:
        if edge.edge_type == EdgeType.CAUSED_BY:
            continue
        if edge.target_id not in trace.nodes:
            continue
        target_name = trace.nodes[edge.target_id].name
        label = _edge_type_to_label(edge.edge_type, target_name)
        result[edge.source_id].append(label)
    return dict(result)


def _edge_type_to_label(edge_type: EdgeType, target_name: str) -> str:
    if edge_type == EdgeType.RETRY_OF:
        return f"[retry of {target_name}]"
    if edge_type == EdgeType.FALLBACK_OF:
        return f"[fallback of {target_name}]"
    if edge_type == EdgeType.BRANCHED_FROM:
        return f"[branched from {target_name}]"
    if edge_type == EdgeType.DATA_FLOW:
        return f"[→ {target_name}]"
    return ""


def _trace_label(trace: TraceGraph) -> str:
    duration = f"{trace.duration_ms:.0f}ms" if trace.duration_ms is not None else "ongoing"
    name = trace.name or trace.trace_id
    return f"Trace: {name} ({duration})"


def _add_node_branch(
    parent_tree: Tree,
    node: Node,
    children_by_parent: dict[str | None, list[Node]],
    edges_by_source: dict[str, list[str]],
    trace: TraceGraph,
    verbosity: Verbosity,
) -> None:
    icon = _status_icon(node.status)
    duration = f"{node.duration_ms:.0f}ms" if node.duration_ms is not None else "running"
    line = f"[{node.node_type}] {node.name} ({duration}) {icon}"
    edge_labels = edges_by_source.get(node.id, [])
    if edge_labels:
        line += " " + " ".join(edge_labels)
    branch = parent_tree.add(line)

    if verbosity == "minimal":
        for child in children_by_parent.get(node.id, []):
            _add_node_branch(branch, child, children_by_parent, edges_by_source, trace, verbosity)
        return

    if verbosity in ("standard", "full"):
        for annotation in node.annotations:
            branch.add(f'annotation: "{annotation}"')
        if node.error:
            err_pre = f"{node.error_type}: " if node.error_type else ""
            branch.add(f"error: {err_pre}{node.error}")
        if node.error_traceback and verbosity == "full":
            branch.add(f"traceback: {node.error_traceback}")

    if verbosity == "full":
        if node.input_data:
            branch.add(f"input: {_format_data(node.input_data)}")
        if node.output_data:
            branch.add(f"output: {_format_data(node.output_data)}")
        if node.metadata:
            branch.add(f"metadata: {_format_data(node.metadata)}")

    for child in children_by_parent.get(node.id, []):
        _add_node_branch(branch, child, children_by_parent, edges_by_source, trace, verbosity)


def _format_data(data: dict[str, object]) -> str:
    """Format dict for display, truncating large values."""
    try:
        s = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        s = str(data)
    if len(s) <= _MAX_VALUE_LEN:
        return s
    return s[:_MAX_VALUE_LEN] + "... [truncated]"


def _status_icon(status: NodeStatus) -> str:
    if status == NodeStatus.COMPLETED:
        return "✓"
    if status == NodeStatus.FAILED:
        return "✗"
    if status == NodeStatus.CANCELLED:
        return "⊘"
    if status == NodeStatus.RUNNING:
        return "…"
    return "·"
