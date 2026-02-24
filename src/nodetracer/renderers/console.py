"""Rich-based trace console rendering."""

from __future__ import annotations

from collections import defaultdict
from io import StringIO
from typing import Literal

from rich.console import Console
from rich.tree import Tree

from ..models import Node, NodeStatus, TraceGraph

Verbosity = Literal["minimal", "standard", "full"]


def render_trace(trace: TraceGraph, *, verbosity: Verbosity = "standard") -> str:
    tree = Tree(_trace_label(trace))
    children_by_parent: dict[str | None, list[Node]] = defaultdict(list)
    for node in trace.nodes.values():
        children_by_parent[node.parent_id].append(node)

    for siblings in children_by_parent.values():
        siblings.sort(key=lambda node: node.sequence_number)

    for root in children_by_parent[None]:
        _add_node_branch(tree, root, children_by_parent, verbosity)

    console = Console(record=True, width=120, markup=False, file=StringIO())
    console.print(tree)
    return console.export_text()


def _trace_label(trace: TraceGraph) -> str:
    duration = f"{trace.duration_ms:.0f}ms" if trace.duration_ms is not None else "ongoing"
    name = trace.name or trace.trace_id
    return f"Trace: {name} ({duration})"


def _add_node_branch(
    parent_tree: Tree,
    node: Node,
    children_by_parent: dict[str | None, list[Node]],
    verbosity: Verbosity,
) -> None:
    icon = _status_icon(node.status)
    duration = f"{node.duration_ms:.0f}ms" if node.duration_ms is not None else "running"
    branch = parent_tree.add(f"[{node.node_type}] {node.name} ({duration}) {icon}")

    if verbosity == "minimal":
        for child in children_by_parent.get(node.id, []):
            _add_node_branch(branch, child, children_by_parent, verbosity)
        return

    if verbosity == "full":
        if node.input_data:
            branch.add(f"input: {node.input_data}")
        if node.output_data:
            branch.add(f"output: {node.output_data}")
        if node.metadata:
            branch.add(f"metadata: {node.metadata}")
        for annotation in node.annotations:
            branch.add(f'annotation: "{annotation}"')
        if node.error:
            branch.add(f"error: {node.error_type}: {node.error}")

    for child in children_by_parent.get(node.id, []):
        _add_node_branch(branch, child, children_by_parent, verbosity)


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
